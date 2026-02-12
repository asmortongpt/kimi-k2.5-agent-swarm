#!/usr/bin/env python3
"""
Example: Custom Security Audit Swarm
Demonstrates custom agent configuration for comprehensive security auditing
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from advanced_orchestrator import AdvancedOrchestrator, TaskComplexity
from agent_skills_library import AgentRole


async def run_security_audit():
    """Run comprehensive security audit with custom agent configuration"""

    print("🛡️ Custom Security Audit Swarm")
    print("=" * 80)
    print()

    # Sample vulnerable application code
    vulnerable_code = """
# Flask Web Application - Vulnerable Example

from flask import Flask, request, jsonify, render_template_string
import sqlite3
import hashlib
import jwt

app = Flask(__name__)
SECRET_KEY = "hardcoded-secret-123"  # Vulnerability: Hardcoded secret

# Vulnerability: SQL Injection
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    # Direct string concatenation in SQL
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    conn = sqlite3.connect('users.db')
    result = conn.execute(query).fetchone()

    if result:
        # Vulnerability: Weak JWT secret
        token = jwt.encode({'user': username}, SECRET_KEY, algorithm='HS256')
        return jsonify({'token': token})
    return jsonify({'error': 'Invalid credentials'}), 401

# Vulnerability: Missing authentication
@app.route('/admin/users')
def admin_users():
    conn = sqlite3.connect('users.db')
    users = conn.execute('SELECT * FROM users').fetchall()
    return jsonify(users)

# Vulnerability: Server-Side Template Injection (SSTI)
@app.route('/greet')
def greet():
    name = request.args.get('name', 'Guest')
    template = f"<h1>Hello {{{{ name }}}}</h1>"
    return render_template_string(template)

# Vulnerability: Weak password hashing
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()

# Vulnerability: Missing CORS, CSP, security headers
# Vulnerability: Debug mode in production
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # Exposed to all interfaces
    """

    async with AdvancedOrchestrator(max_agents=100) as orchestrator:

        # Define custom security audit team
        security_team = [
            AgentRole.SECURITY_AUDITOR,      # Lead security reviewer
            AgentRole.PENETRATION_TESTER,    # Exploit identification
            AgentRole.SECURITY_ENGINEER,      # Architecture review
            AgentRole.CRYPTOGRAPHER,          # Crypto analysis
            AgentRole.COMPLIANCE_OFFICER,     # Standards compliance
            AgentRole.ACCESS_CONTROL_SPECIALIST,  # AuthN/AuthZ review
            AgentRole.PRIVACY_ANALYST,        # Data protection
        ]

        print(f"🔧 Assembling Security Team:")
        for role in security_team:
            print(f"  • {role.value.replace('_', ' ').title()}")
        print()

        # Execute comprehensive security audit
        result = await orchestrator.execute_custom_swarm(
            task=f"""Perform COMPREHENSIVE security audit of this Flask application.

APPLICATION CODE:
{vulnerable_code}

AUDIT REQUIREMENTS:

1. VULNERABILITY IDENTIFICATION
   - Identify ALL vulnerabilities (OWASP Top 10, CWE Top 25)
   - Classify by severity (Critical, High, Medium, Low)
   - Provide exploit scenarios for each vulnerability

2. SECURITY ARCHITECTURE REVIEW
   - Analyze authentication and authorization mechanisms
   - Review session management
   - Assess input validation and sanitization
   - Evaluate cryptographic implementations

3. COMPLIANCE ASSESSMENT
   - Check against OWASP Application Security Verification Standard (ASVS)
   - Evaluate SOC 2 Type II requirements
   - Assess GDPR/privacy compliance
   - Review security logging and monitoring

4. PENETRATION TESTING
   - Demonstrate exploitability of vulnerabilities
   - Provide proof-of-concept exploits
   - Assess impact of successful attacks

5. CRYPTOGRAPHIC ANALYSIS
   - Review hashing algorithms
   - Assess secret management
   - Evaluate encryption at rest and in transit

6. ACCESS CONTROL REVIEW
   - Identify missing authorization checks
   - Review privilege escalation vectors
   - Assess session security

7. DATA PRIVACY ANALYSIS
   - Identify PII handling issues
   - Review data retention policies
   - Assess encryption of sensitive data

DELIVERABLES:
1. Executive summary (for non-technical stakeholders)
2. Detailed vulnerability report with CVE references
3. Exploit demonstrations (POC code)
4. Remediation guide with secure code examples
5. Compliance gap analysis
6. Security architecture recommendations
7. Implementation roadmap (prioritized by risk)

Use all {len(security_team)} specialized agent roles to provide comprehensive coverage.
            """,
            agent_roles=security_team,
            complexity=TaskComplexity.HIGH,
            execution_strategy="hierarchical",
            context={
                "framework": "Flask/Python",
                "compliance_requirements": ["OWASP ASVS", "SOC 2 Type II", "GDPR"],
                "severity_threshold": "Medium",
                "include_exploit_pocs": True,
                "target_audience": ["CISO", "Development Team", "Compliance Team"]
            }
        )

        print("\n" + "=" * 80)
        print("🔍 SECURITY AUDIT RESULTS")
        print("=" * 80)
        print()

        response_text = result.get('message', {}).get('content') or result.get('response', '')
        print(response_text[:5000] if len(response_text) > 5000 else response_text)

        if len(response_text) > 5000:
            print(f"\n... (truncated, total length: {len(response_text)} characters)")

        print("\n" + "=" * 80)
        print("✅ Security Audit Complete")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_security_audit())
