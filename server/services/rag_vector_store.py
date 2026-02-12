#!/usr/bin/env python3
"""
Production RAG Vector Store - NO MOCKS
Uses real embeddings and real vector databases
"""

import os
import asyncio
import asyncpg
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
from dotenv import load_dotenv

# Import real embedding service
from embeddings import RealEmbeddingService, EmbeddingProvider

load_dotenv(os.path.expanduser('~/.env'))


@dataclass
class Document:
    """Document for RAG retrieval"""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class SearchResult:
    """Search result from vector store"""
    document: Document
    score: float
    rank: int


class ProductionRAGStore:
    """
    Production RAG Vector Store - Real Implementation
    - Uses real PostgreSQL with pgvector extension
    - Uses real Ollama embeddings by default (FREE, no API costs!)
    - Optional: OpenAI/Cohere for higher quality (paid)
    - Production-grade performance and security
    """

    def __init__(
        self,
        collection_name: str = "kimi_knowledge",
        embedding_provider: EmbeddingProvider = EmbeddingProvider.OLLAMA,  # FREE default
        connection_string: Optional[str] = None
    ):
        """
        Initialize production RAG store

        Args:
            collection_name: Name for the knowledge collection
            embedding_provider: Real embedding provider (default: OLLAMA - free, local)
            connection_string: PostgreSQL connection string (from env if None)
        """
        self.collection_name = collection_name

        # Initialize REAL embedding service
        self.embedding_service = RealEmbeddingService(provider=embedding_provider)

        # Build PostgreSQL connection string
        if connection_string:
            self.connection_string = connection_string
        else:
            self.connection_string = self._build_connection_string()

        self.pool: Optional[asyncpg.Pool] = None

    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string from environment"""
        server = os.getenv('AZURE_SQL_SERVER', 'localhost')
        database = os.getenv('AZURE_SQL_DATABASE', 'kimi_swarm')
        username = os.getenv('AZURE_SQL_USERNAME', 'postgres')
        password = os.getenv('AZURE_SQL_PASSWORD', '')

        if server == 'localhost' or not server.endswith('.database.windows.net'):
            return f"postgresql://{username}:{password}@{server}:5432/{database}"

        return f"postgresql://{username}@{server}:{password}@{server}:5432/{database}?sslmode=require"

    async def connect(self):
        """Connect to PostgreSQL database"""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            print(f"✅ Connected to PostgreSQL vector store")
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            raise

    async def close(self):
        """Close database connection"""
        if self.pool:
            await self.pool.close()
            await self.embedding_service.close()

    async def add_documents(
        self,
        documents: List[Document],
        generate_embeddings: bool = True
    ):
        """
        Add documents to vector store with REAL embeddings

        Args:
            documents: Documents to add
            generate_embeddings: Generate real embeddings (not fake hashes)
        """
        if not self.pool:
            await self.connect()

        if generate_embeddings:
            # Generate REAL embeddings using actual API
            texts_to_embed = [
                doc.content for doc in documents if not doc.embedding
            ]

            if texts_to_embed:
                print(f"🔄 Generating REAL embeddings for {len(texts_to_embed)} documents...")
                embeddings = await self.embedding_service.embed_batch(texts_to_embed)

                embed_idx = 0
                for doc in documents:
                    if not doc.embedding:
                        doc.embedding = embeddings[embed_idx]
                        embed_idx += 1

                print(f"✅ Generated {len(embeddings)} real embeddings")

        # Insert into PostgreSQL with pgvector
        async with self.pool.acquire() as conn:
            for doc in documents:
                # Use parameterized query ($1, $2, $3) for security
                await conn.execute(
                    """
                    INSERT INTO knowledge_base (
                        document_id, content, embedding, metadata,
                        category, source, embedding_model, indexed_at
                    ) VALUES (
                        $1, $2, $3::vector, $4, $5, $6, $7, $8
                    )
                    ON CONFLICT (document_id) DO UPDATE
                    SET content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        metadata = EXCLUDED.metadata,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    doc.id,
                    doc.content,
                    doc.embedding,
                    json.dumps(doc.metadata),
                    doc.metadata.get('category'),
                    doc.metadata.get('source'),
                    self.embedding_service.model,
                    datetime.utcnow()
                )

        print(f"✅ Added {len(documents)} documents to vector store")

    async def search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.0
    ) -> List[SearchResult]:
        """
        Search for relevant documents using REAL vector similarity

        Args:
            query: Search query
            k: Number of results
            filter_metadata: Metadata filters
            score_threshold: Minimum similarity score

        Returns:
            Search results with real similarity scores
        """
        if not self.pool:
            await self.connect()

        # Generate REAL embedding for query
        print(f"🔍 Generating real embedding for query...")
        query_embedding = await self.embedding_service.embed_text(query)

        # Build WHERE clause for metadata filtering
        where_clause = "1=1"
        params = [query_embedding, k]

        if filter_metadata:
            if 'category' in filter_metadata:
                where_clause += " AND category = $3"
                params.append(filter_metadata['category'])
            if 'source' in filter_metadata:
                param_idx = len(params) + 1
                where_clause += f" AND source = ${param_idx}"
                params.append(filter_metadata['source'])

        # Perform vector similarity search using pgvector
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT
                    document_id,
                    content,
                    metadata,
                    1 - (embedding <=> $1::vector) as similarity
                FROM knowledge_base
                WHERE {where_clause}
                ORDER BY embedding <=> $1::vector
                LIMIT $2
                """,
                *params
            )

        # Convert to SearchResult objects
        results = []
        for i, row in enumerate(rows):
            if row['similarity'] >= score_threshold:
                doc = Document(
                    id=row['document_id'],
                    content=row['content'],
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
                results.append(SearchResult(
                    document=doc,
                    score=float(row['similarity']),
                    rank=i + 1
                ))

        print(f"✅ Found {len(results)} results")
        return results

    async def delete(self, doc_id: str):
        """Delete document by ID using parameterized query"""
        if not self.pool:
            await self.connect()

        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM knowledge_base WHERE document_id = $1",
                doc_id
            )

    async def clear(self):
        """Clear all documents from collection"""
        if not self.pool:
            await self.connect()

        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM knowledge_base")

    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        if not self.pool:
            await self.connect()

        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as total_documents,
                    COUNT(DISTINCT category) as categories,
                    COUNT(DISTINCT source) as sources,
                    MIN(created_at) as oldest_document,
                    MAX(created_at) as newest_document
                FROM knowledge_base
                """
            )

        return {
            "total_documents": stats['total_documents'],
            "categories": stats['categories'],
            "sources": stats['sources'],
            "oldest_document": stats['oldest_document'].isoformat() if stats['oldest_document'] else None,
            "newest_document": stats['newest_document'].isoformat() if stats['newest_document'] else None
        }

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Example usage with REAL data and REAL embeddings
async def demo_production_rag():
    """
    Demonstrate production RAG with REAL embeddings
    NO MOCK DATA - uses actual OpenAI API
    """
    print("🚀 Production RAG Vector Store Demo\n")

    try:
        async with ProductionRAGStore(
            collection_name="agent_knowledge",
            embedding_provider=EmbeddingProvider.OPENAI
        ) as store:

            # Add knowledge documents with REAL embeddings
            documents = [
                Document(
                    id="doc1",
                    content="Kimi K2.5 can spawn up to 100 specialized sub-agents working in parallel using advanced swarm intelligence",
                    metadata={"category": "capabilities", "source": "documentation"}
                ),
                Document(
                    id="doc2",
                    content="The agent swarm uses Parallel-Agent Reinforcement Learning (PARL) for self-directed task distribution",
                    metadata={"category": "technology", "source": "research"}
                ),
                Document(
                    id="doc3",
                    content="Circuit breaker pattern prevents cascading failures in distributed systems by monitoring failure rates",
                    metadata={"category": "resilience", "source": "patterns"}
                ),
                Document(
                    id="doc4",
                    content="Multi-level caching with L1 memory and L2 Redis improves response time by 3x in production workloads",
                    metadata={"category": "performance", "source": "benchmarks"}
                )
            ]

            print("📚 Adding documents with REAL embeddings...")
            await store.add_documents(documents, generate_embeddings=True)

            # Search with REAL vector similarity
            queries = [
                "How many agents can work in parallel?",
                "What improves system performance?",
                "How to handle system failures?"
            ]

            for query in queries:
                print(f"\n❓ Query: {query}")
                results = await store.search(query, k=2)

                for result in results:
                    print(f"  📄 [Score: {result.score:.3f}] {result.document.content}")

            # Show statistics
            print("\n📊 Vector Store Statistics:")
            stats = await store.get_stats()
            for key, value in stats.items():
                print(f"  {key}: {value}")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(demo_production_rag())
