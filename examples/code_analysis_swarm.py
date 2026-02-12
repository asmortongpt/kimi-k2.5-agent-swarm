#!/usr/bin/env python3
"""
Example 4: Code Analysis with Agent Swarm
Demonstrates parallel code analysis by specialized agents
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kimi_client import KimiClient, ProviderType, AgentSwarmConfig


async def code_analysis_swarm():
    """Analyze code using specialized agent swarm"""

    print("🔍 Kimi K2.5 - Code Analysis Agent Swarm\n")
    print("=" * 80)

    client = KimiClient(
        provider=ProviderType.OLLAMA,
        swarm_config=AgentSwarmConfig(
            max_agents=50,
            parallel_execution=True,
            enable_thinking_mode=True
        )
    )

    # Sample codebase to analyze
    codebase = """
    # User Authentication Service

    import jwt
    import hashlib
    from flask import Flask, request, jsonify

    app = Flask(__name__)
    SECRET_KEY = "hardcoded-secret-123"

    @app.route('/login', methods=['POST'])
    def login():
        username = request.form.get('username')
        password = request.form.get('password')

        # Direct SQL query - potential SQL injection
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        result = execute_query(query)

        if result:
            # Create JWT token
            token = jwt.encode({'user': username}, SECRET_KEY, algorithm='HS256')
            return jsonify({'token': token})
        else:
            return jsonify({'error': 'Invalid credentials'}), 401

    @app.route('/user/<user_id>')
    def get_user(user_id):
        # No authentication check
        query = f"SELECT * FROM users WHERE id = {user_id}"
        user = execute_query(query)
        return jsonify(user)

    @app.route('/admin')
    def admin_panel():
        # Missing authorization check
        return render_admin_panel()

    def hash_password(password):
        # Weak hashing
        return hashlib.md5(password.encode()).hexdigest()
    """

    try:
        # Task 1: Comprehensive security audit
        print("\n🛡️ Task 1: Security Audit with Specialized Agents")
        print("=" * 80)
        print("Deploying: SQL Injection Hunter, Auth Auditor, Crypto Analyzer, Access Control Checker\n")

        security_audit = await client.agent_swarm_task(
            task=f"""Perform comprehensive security audit using specialized agents:

            AGENTS TO DEPLOY:

            1. SQL Injection Hunter
               - Scan for SQL injection vulnerabilities
               - Identify unsafe query construction
               - Provide parameterized query examples

            2. Authentication Auditor
               - Review auth mechanisms
               - Check token handling
               - Verify session management

            3. Cryptography Analyzer
               - Assess hashing algorithms
               - Check secret management
               - Review encryption practices

            4. Access Control Checker
               - Verify authorization checks
               - Identify missing ACLs
               - Check for privilege escalation

            5. Input Validation Expert
               - Find input validation gaps
               - Identify injection points
               - Suggest validation strategies

            CODE TO ANALYZE:
            {codebase}

            OUTPUT FORMAT:
            - Vulnerability summary (by severity: Critical, High, Medium, Low)
            - Detailed findings for each issue
            - Exploit scenarios
            - Remediation code examples
            - Security best practices checklist
            """,
            context={
                "compliance": ["OWASP Top 10", "CWE Top 25"],
                "language": "Python",
                "framework": "Flask"
            },
            max_agents=20
        )

        print("\n🚨 SECURITY AUDIT RESULTS:")
        print("=" * 80)
        print(security_audit.get('message', {}).get('content', security_audit))

        # Task 2: Performance optimization
        print("\n\n⚡ Task 2: Performance Optimization")
        print("=" * 80)
        print("Deploying: Query Optimizer, Cache Strategist, Algorithm Analyzer\n")

        performance = await client.agent_swarm_task(
            task=f"""Analyze code for performance optimization using specialized agents:

            AGENTS:
            1. Database Query Optimizer - analyze queries, suggest indexes, caching
            2. Algorithm Complexity Analyzer - identify O(n²) patterns, suggest improvements
            3. Caching Strategist - recommend caching layers, strategies
            4. Concurrency Expert - identify async opportunities, parallelization
            5. Resource Monitor - memory leaks, connection pooling

            CODE:
            {codebase}

            Provide:
            - Performance bottlenecks
            - Optimization opportunities
            - Before/after code examples
            - Expected performance gains
            - Implementation priority
            """,
            context={
                "scale": "10,000 req/sec",
                "database": "PostgreSQL"
            },
            max_agents=15
        )

        print("\n📈 PERFORMANCE ANALYSIS:")
        print("=" * 80)
        print(performance.get('message', {}).get('content', performance))

        # Task 3: Code quality & best practices
        print("\n\n✨ Task 3: Code Quality & Best Practices")
        print("=" * 80)
        print("Deploying: Style Guide Enforcer, Documentation Generator, Test Coverage Analyzer\n")

        quality = await client.agent_swarm_task(
            task=f"""Improve code quality using specialized agents:

            AGENTS:
            1. PEP 8 Compliance Checker - style violations, formatting
            2. Documentation Generator - docstrings, type hints, comments
            3. Test Coverage Analyzer - missing tests, edge cases
            4. Error Handling Expert - exception handling, logging
            5. Code Smell Detector - anti-patterns, complexity
            6. Refactoring Specialist - DRY violations, modularity

            CODE:
            {codebase}

            Provide:
            - Quality score (0-100)
            - Specific improvements
            - Refactored code examples
            - Test cases needed
            - Documentation gaps
            """,
            context={
                "standards": ["PEP 8", "Google Python Style Guide"],
                "test_framework": "pytest",
                "coverage_target": 90
            },
            max_agents=18
        )

        print("\n🎯 CODE QUALITY REPORT:")
        print("=" * 80)
        print(quality.get('message', {}).get('content', quality))

        # Task 4: Generate improved version
        print("\n\n🔧 Task 4: Generate Secure, Optimized Version")
        print("=" * 80)

        improved = await client.agent_swarm_task(
            task=f"""Using findings from security audit, performance analysis, and quality review,
            generate a fully improved version of the code that:

            1. Fixes ALL security vulnerabilities
            2. Implements performance optimizations
            3. Follows best practices
            4. Includes comprehensive error handling
            5. Has proper documentation
            6. Includes unit tests

            Original code:
            {codebase}

            Provide complete, production-ready code with inline comments explaining improvements.
            """,
            max_agents=10
        )

        print("\n✅ IMPROVED CODE:")
        print("=" * 80)
        print(improved.get('message', {}).get('content', improved))

    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(code_analysis_swarm())
