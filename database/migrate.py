#!/usr/bin/env python3
"""
Database Migration Tool
Applies schema migrations to PostgreSQL database
Security: Uses parameterized queries only
"""

import os
import asyncio
import asyncpg
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv(os.path.expanduser('~/.env'))


class DatabaseMigrator:
    """PostgreSQL database migrator with security best practices"""

    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize migrator

        Args:
            connection_string: PostgreSQL connection string (defaults to env vars)
        """
        if connection_string:
            self.connection_string = connection_string
        else:
            # Build from Azure SQL env vars (works with PostgreSQL too)
            self.connection_string = self._build_connection_string()

        self.pool: Optional[asyncpg.Pool] = None

    def _build_connection_string(self) -> str:
        """Build connection string from environment variables"""
        # Try Azure SQL environment variables first
        server = os.getenv('AZURE_SQL_SERVER', 'localhost')
        database = os.getenv('AZURE_SQL_DATABASE', 'kimi_swarm')
        username = os.getenv('AZURE_SQL_USERNAME', 'postgres')
        password = os.getenv('AZURE_SQL_PASSWORD', '')

        # For local PostgreSQL, use standard PostgreSQL connection
        if server == 'localhost' or not server.endswith('.database.windows.net'):
            return f"postgresql://{username}:{password}@{server}:5432/{database}"

        # For Azure Database for PostgreSQL
        return f"postgresql://{username}@{server}:{password}@{server}:5432/{database}?sslmode=require"

    async def connect(self):
        """Establish database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            print(f"✅ Connected to database")
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            raise

    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            print("✅ Database connection closed")

    async def create_migrations_table(self):
        """Create migrations tracking table"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id SERIAL PRIMARY KEY,
                    migration_name VARCHAR(255) NOT NULL UNIQUE,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    checksum VARCHAR(64),
                    execution_time_ms INTEGER
                )
            """)
            print("✅ Migrations tracking table ready")

    async def get_applied_migrations(self) -> List[str]:
        """Get list of applied migrations"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT migration_name FROM schema_migrations ORDER BY id"
            )
            return [row['migration_name'] for row in rows]

    async def apply_migration(self, name: str, sql: str) -> bool:
        """
        Apply a migration

        Args:
            name: Migration name
            sql: SQL to execute

        Returns:
            True if successful
        """
        start_time = datetime.utcnow()

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                try:
                    # Execute migration SQL
                    await conn.execute(sql)

                    # Record migration
                    execution_time = int(
                        (datetime.utcnow() - start_time).total_seconds() * 1000
                    )

                    await conn.execute(
                        """
                        INSERT INTO schema_migrations (migration_name, execution_time_ms)
                        VALUES ($1, $2)
                        """,
                        name,
                        execution_time
                    )

                    print(f"✅ Applied migration: {name} ({execution_time}ms)")
                    return True

                except Exception as e:
                    print(f"❌ Failed to apply migration {name}: {e}")
                    raise

    async def migrate(self):
        """Run all pending migrations"""
        print("🚀 Starting database migration...\n")

        # Connect to database
        await self.connect()

        # Create migrations table
        await self.create_migrations_table()

        # Get applied migrations
        applied = await self.get_applied_migrations()
        print(f"📊 Found {len(applied)} previously applied migrations")

        # Define migrations
        migrations = [
            {
                "name": "001_initial_schema",
                "path": os.path.join(
                    os.path.dirname(__file__), "schema.sql"
                )
            }
        ]

        # Apply pending migrations
        pending_count = 0
        for migration in migrations:
            if migration["name"] not in applied:
                print(f"\n📝 Applying: {migration['name']}")

                # Read SQL file
                with open(migration["path"], "r") as f:
                    sql = f.read()

                # Apply migration
                await self.apply_migration(migration["name"], sql)
                pending_count += 1
            else:
                print(f"⏭️  Skipping (already applied): {migration['name']}")

        print(f"\n✅ Migration complete! Applied {pending_count} new migration(s)")

        # Close connection
        await self.close()

    async def rollback_last(self):
        """Rollback last migration (use with caution!)"""
        print("⚠️  Rolling back last migration...")

        await self.connect()

        async with self.pool.acquire() as conn:
            # Get last migration
            row = await conn.fetchrow(
                """
                SELECT migration_name
                FROM schema_migrations
                ORDER BY id DESC
                LIMIT 1
                """
            )

            if not row:
                print("❌ No migrations to rollback")
                return

            migration_name = row['migration_name']
            print(f"🔄 Rolling back: {migration_name}")

            # For safety, we don't automatically drop tables
            # User must manually create rollback scripts
            print("⚠️  Automatic rollback not implemented for safety")
            print("    Please create a manual rollback script if needed")

            # Remove from migrations table
            await conn.execute(
                "DELETE FROM schema_migrations WHERE migration_name = $1",
                migration_name
            )
            print(f"✅ Removed {migration_name} from migration tracking")

        await self.close()

    async def status(self):
        """Show migration status"""
        print("📊 Migration Status\n")

        await self.connect()

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    migration_name,
                    applied_at,
                    execution_time_ms
                FROM schema_migrations
                ORDER BY id
                """
            )

            if not rows:
                print("No migrations applied yet")
            else:
                print(f"Applied migrations: {len(rows)}\n")
                for row in rows:
                    print(f"  • {row['migration_name']}")
                    print(f"    Applied: {row['applied_at']}")
                    print(f"    Duration: {row['execution_time_ms']}ms\n")

        await self.close()


async def main():
    """Main entry point"""
    import sys

    migrator = DatabaseMigrator()

    command = sys.argv[1] if len(sys.argv) > 1 else "migrate"

    if command == "migrate":
        await migrator.migrate()
    elif command == "status":
        await migrator.status()
    elif command == "rollback":
        await migrator.rollback_last()
    else:
        print("Usage: python migrate.py [migrate|status|rollback]")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
