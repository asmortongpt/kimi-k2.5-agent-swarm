#!/usr/bin/env python3
"""
Kimi K2.5 Agent Skills Library
Comprehensive library of specialized agent templates and skills
"""

from enum import Enum
from typing import List, Dict, Optional
from dataclasses import dataclass


class AgentRole(Enum):
    """Predefined agent roles"""
    # Research & Analysis
    RESEARCH_SPECIALIST = "research_specialist"
    DATA_ANALYST = "data_analyst"
    MARKET_ANALYST = "market_analyst"
    ACADEMIC_RESEARCHER = "academic_researcher"
    FACT_CHECKER = "fact_checker"
    TREND_ANALYST = "trend_analyst"

    # Development & Engineering
    SOFTWARE_ARCHITECT = "software_architect"
    BACKEND_DEVELOPER = "backend_developer"
    FRONTEND_DEVELOPER = "frontend_developer"
    DEVOPS_ENGINEER = "devops_engineer"
    SECURITY_ENGINEER = "security_engineer"
    QA_ENGINEER = "qa_engineer"
    PERFORMANCE_ENGINEER = "performance_engineer"

    # Security & Compliance
    SECURITY_AUDITOR = "security_auditor"
    PENETRATION_TESTER = "penetration_tester"
    COMPLIANCE_OFFICER = "compliance_officer"
    CRYPTOGRAPHER = "cryptographer"
    ACCESS_CONTROL_SPECIALIST = "access_control_specialist"
    PRIVACY_ANALYST = "privacy_analyst"

    # Content & Communication
    TECHNICAL_WRITER = "technical_writer"
    CONTENT_WRITER = "content_writer"
    EDITOR = "editor"
    SEO_SPECIALIST = "seo_specialist"
    COPYWRITER = "copywriter"

    # Business & Strategy
    BUSINESS_ANALYST = "business_analyst"
    PRODUCT_MANAGER = "product_manager"
    FINANCIAL_ANALYST = "financial_analyst"
    RISK_MANAGER = "risk_manager"
    PROJECT_MANAGER = "project_manager"

    # Creative & Design
    UI_UX_DESIGNER = "ui_ux_designer"
    VISUAL_DESIGNER = "visual_designer"
    VIDEO_PRODUCER = "video_producer"
    THREE_D_ARTIST = "3d_artist"

    # Data & AI
    DATA_ENGINEER = "data_engineer"
    ML_ENGINEER = "ml_engineer"
    AI_RESEARCHER = "ai_researcher"
    DATA_SCIENTIST = "data_scientist"


@dataclass
class AgentSkill:
    """Individual agent skill definition"""
    name: str
    description: str
    expertise_areas: List[str]
    tools: List[str]
    output_types: List[str]


@dataclass
class AgentTemplate:
    """Complete agent template with skills and configuration"""
    role: AgentRole
    name: str
    description: str
    skills: List[AgentSkill]
    primary_focus: str
    expertise_level: str  # junior, mid, senior, expert
    optimal_team_size: int
    works_best_with: List[AgentRole]


class AgentSkillsLibrary:
    """Library of predefined agent templates"""

    @staticmethod
    def get_research_agents() -> Dict[AgentRole, AgentTemplate]:
        """Get all research-focused agent templates"""
        return {
            AgentRole.RESEARCH_SPECIALIST: AgentTemplate(
                role=AgentRole.RESEARCH_SPECIALIST,
                name="Research Specialist",
                description="Deep-dive research on specific topics with academic rigor",
                skills=[
                    AgentSkill(
                        name="Literature Review",
                        description="Comprehensive review of academic and industry literature",
                        expertise_areas=["Academic papers", "Industry reports", "Technical docs"],
                        tools=["Web search", "Academic databases", "Citation tracking"],
                        output_types=["Research summaries", "Bibliographies", "State-of-the-art analysis"]
                    ),
                    AgentSkill(
                        name="Data Collection",
                        description="Systematic collection of relevant data and sources",
                        expertise_areas=["Primary sources", "Data extraction", "Survey design"],
                        tools=["APIs", "Web scraping", "Database queries"],
                        output_types=["Datasets", "Source lists", "Data reports"]
                    ),
                    AgentSkill(
                        name="Synthesis",
                        description="Combining multiple sources into coherent insights",
                        expertise_areas=["Pattern recognition", "Trend analysis", "Critical thinking"],
                        tools=["Analysis frameworks", "Visualization"],
                        output_types=["Executive summaries", "Insight reports"]
                    )
                ],
                primary_focus="In-depth research and analysis",
                expertise_level="expert",
                optimal_team_size=5,
                works_best_with=[AgentRole.DATA_ANALYST, AgentRole.TECHNICAL_WRITER]
            ),

            AgentRole.MARKET_ANALYST: AgentTemplate(
                role=AgentRole.MARKET_ANALYST,
                name="Market Analyst",
                description="Competitive intelligence and market research",
                skills=[
                    AgentSkill(
                        name="Competitive Analysis",
                        description="In-depth analysis of competitors and market positioning",
                        expertise_areas=["Competitor profiling", "SWOT analysis", "Market share"],
                        tools=["Market data", "Financial reports", "Customer reviews"],
                        output_types=["Competitive matrices", "Market reports"]
                    ),
                    AgentSkill(
                        name="Trend Forecasting",
                        description="Predicting market trends and opportunities",
                        expertise_areas=["Trend analysis", "Forecasting", "Scenario planning"],
                        tools=["Statistical models", "Industry data"],
                        output_types=["Trend reports", "Forecasts", "Opportunity analysis"]
                    )
                ],
                primary_focus="Market intelligence and competitive analysis",
                expertise_level="senior",
                optimal_team_size=3,
                works_best_with=[AgentRole.BUSINESS_ANALYST, AgentRole.FINANCIAL_ANALYST]
            )
        }

    @staticmethod
    def get_development_agents() -> Dict[AgentRole, AgentTemplate]:
        """Get all development-focused agent templates"""
        return {
            AgentRole.SOFTWARE_ARCHITECT: AgentTemplate(
                role=AgentRole.SOFTWARE_ARCHITECT,
                name="Software Architect",
                description="System design and architectural decision-making",
                skills=[
                    AgentSkill(
                        name="Architecture Design",
                        description="Designing scalable, maintainable system architectures",
                        expertise_areas=["Microservices", "Monoliths", "Serverless", "Event-driven"],
                        tools=["UML", "Architecture diagrams", "Design patterns"],
                        output_types=["Architecture diagrams", "Design docs", "Tech specs"]
                    ),
                    AgentSkill(
                        name="Technology Selection",
                        description="Choosing optimal technologies for requirements",
                        expertise_areas=["Technology evaluation", "Trade-off analysis"],
                        tools=["Proof of concepts", "Benchmarking"],
                        output_types=["Technology recommendations", "Comparison matrices"]
                    ),
                    AgentSkill(
                        name="Scalability Planning",
                        description="Ensuring systems can scale effectively",
                        expertise_areas=["Load balancing", "Caching", "Database sharding"],
                        tools=["Performance modeling", "Capacity planning"],
                        output_types=["Scalability plans", "Performance specs"]
                    )
                ],
                primary_focus="High-level system architecture and technical strategy",
                expertise_level="expert",
                optimal_team_size=2,
                works_best_with=[AgentRole.BACKEND_DEVELOPER, AgentRole.DEVOPS_ENGINEER]
            ),

            AgentRole.SECURITY_ENGINEER: AgentTemplate(
                role=AgentRole.SECURITY_ENGINEER,
                name="Security Engineer",
                description="Application and infrastructure security",
                skills=[
                    AgentSkill(
                        name="Threat Modeling",
                        description="Identifying and mitigating security threats",
                        expertise_areas=["STRIDE", "Attack trees", "Risk assessment"],
                        tools=["Threat modeling tools", "CVSS scoring"],
                        output_types=["Threat models", "Risk registers"]
                    ),
                    AgentSkill(
                        name="Security Architecture",
                        description="Designing secure systems and defenses",
                        expertise_areas=["Defense in depth", "Zero trust", "Encryption"],
                        tools=["Security frameworks", "Compliance standards"],
                        output_types=["Security architectures", "Security requirements"]
                    ),
                    AgentSkill(
                        name="Incident Response",
                        description="Responding to security incidents",
                        expertise_areas=["Forensics", "Containment", "Recovery"],
                        tools=["SIEM", "Log analysis", "Forensic tools"],
                        output_types=["Incident reports", "Remediation plans"]
                    )
                ],
                primary_focus="Security architecture and threat mitigation",
                expertise_level="expert",
                optimal_team_size=3,
                works_best_with=[AgentRole.SECURITY_AUDITOR, AgentRole.PENETRATION_TESTER]
            )
        }

    @staticmethod
    def get_security_agents() -> Dict[AgentRole, AgentTemplate]:
        """Get all security-focused agent templates"""
        return {
            AgentRole.SECURITY_AUDITOR: AgentTemplate(
                role=AgentRole.SECURITY_AUDITOR,
                name="Security Auditor",
                description="Code review and vulnerability assessment",
                skills=[
                    AgentSkill(
                        name="Code Security Review",
                        description="Analyzing code for security vulnerabilities",
                        expertise_areas=["OWASP Top 10", "CWE Top 25", "Secure coding"],
                        tools=["SAST", "DAST", "Code scanners"],
                        output_types=["Vulnerability reports", "Remediation guides"]
                    ),
                    AgentSkill(
                        name="Compliance Audit",
                        description="Ensuring compliance with security standards",
                        expertise_areas=["PCI-DSS", "HIPAA", "SOC 2", "ISO 27001"],
                        tools=["Compliance frameworks", "Audit tools"],
                        output_types=["Compliance reports", "Gap analysis"]
                    )
                ],
                primary_focus="Security auditing and compliance",
                expertise_level="senior",
                optimal_team_size=4,
                works_best_with=[AgentRole.SECURITY_ENGINEER, AgentRole.COMPLIANCE_OFFICER]
            ),

            AgentRole.PENETRATION_TESTER: AgentTemplate(
                role=AgentRole.PENETRATION_TESTER,
                name="Penetration Tester",
                description="Offensive security and exploit detection",
                skills=[
                    AgentSkill(
                        name="Vulnerability Exploitation",
                        description="Identifying and exploiting security vulnerabilities",
                        expertise_areas=["SQL injection", "XSS", "CSRF", "Authentication bypass"],
                        tools=["Burp Suite", "Metasploit", "Custom exploits"],
                        output_types=["Penetration test reports", "Exploit POCs"]
                    ),
                    AgentSkill(
                        name="Red Team Operations",
                        description="Simulating advanced persistent threats",
                        expertise_areas=["Social engineering", "Lateral movement", "Privilege escalation"],
                        tools=["C2 frameworks", "Reconnaissance tools"],
                        output_types=["Attack narratives", "Security recommendations"]
                    )
                ],
                primary_focus="Offensive security and vulnerability exploitation",
                expertise_level="expert",
                optimal_team_size=2,
                works_best_with=[AgentRole.SECURITY_AUDITOR, AgentRole.SECURITY_ENGINEER]
            )
        }

    @staticmethod
    def get_content_agents() -> Dict[AgentRole, AgentTemplate]:
        """Get all content-focused agent templates"""
        return {
            AgentRole.TECHNICAL_WRITER: AgentTemplate(
                role=AgentRole.TECHNICAL_WRITER,
                name="Technical Writer",
                description="Technical documentation and developer guides",
                skills=[
                    AgentSkill(
                        name="API Documentation",
                        description="Writing comprehensive API documentation",
                        expertise_areas=["REST", "GraphQL", "OpenAPI", "SDK docs"],
                        tools=["Swagger", "Postman", "Documentation generators"],
                        output_types=["API references", "Integration guides"]
                    ),
                    AgentSkill(
                        name="User Documentation",
                        description="Creating user-friendly documentation",
                        expertise_areas=["User guides", "Tutorials", "Troubleshooting"],
                        tools=["Markdown", "Documentation platforms"],
                        output_types=["User manuals", "Quick start guides", "FAQs"]
                    )
                ],
                primary_focus="Clear, comprehensive technical documentation",
                expertise_level="senior",
                optimal_team_size=3,
                works_best_with=[AgentRole.SOFTWARE_ARCHITECT, AgentRole.BACKEND_DEVELOPER]
            )
        }

    @staticmethod
    def get_all_agents() -> Dict[AgentRole, AgentTemplate]:
        """Get all available agent templates"""
        all_agents = {}
        all_agents.update(AgentSkillsLibrary.get_research_agents())
        all_agents.update(AgentSkillsLibrary.get_development_agents())
        all_agents.update(AgentSkillsLibrary.get_security_agents())
        all_agents.update(AgentSkillsLibrary.get_content_agents())
        return all_agents

    @staticmethod
    def get_agent_by_role(role: AgentRole) -> Optional[AgentTemplate]:
        """Get specific agent template by role"""
        all_agents = AgentSkillsLibrary.get_all_agents()
        return all_agents.get(role)

    @staticmethod
    def recommend_agents_for_task(task_type: str, complexity: str = "medium") -> List[AgentTemplate]:
        """Recommend agents based on task type and complexity"""

        recommendations = {
            "security_audit": [
                AgentRole.SECURITY_AUDITOR,
                AgentRole.PENETRATION_TESTER,
                AgentRole.SECURITY_ENGINEER,
                AgentRole.COMPLIANCE_OFFICER
            ],
            "research": [
                AgentRole.RESEARCH_SPECIALIST,
                AgentRole.DATA_ANALYST,
                AgentRole.FACT_CHECKER,
                AgentRole.TECHNICAL_WRITER
            ],
            "software_development": [
                AgentRole.SOFTWARE_ARCHITECT,
                AgentRole.BACKEND_DEVELOPER,
                AgentRole.FRONTEND_DEVELOPER,
                AgentRole.QA_ENGINEER,
                AgentRole.DEVOPS_ENGINEER
            ],
            "market_analysis": [
                AgentRole.MARKET_ANALYST,
                AgentRole.BUSINESS_ANALYST,
                AgentRole.FINANCIAL_ANALYST,
                AgentRole.DATA_ANALYST
            ]
        }

        # Get recommended roles
        roles = recommendations.get(task_type, [])

        # Adjust count based on complexity
        complexity_multipliers = {
            "low": 0.5,
            "medium": 1.0,
            "high": 1.5,
            "extreme": 2.0
        }

        multiplier = complexity_multipliers.get(complexity, 1.0)
        target_count = int(len(roles) * multiplier)

        # Get agent templates
        all_agents = AgentSkillsLibrary.get_all_agents()
        recommended = [all_agents[role] for role in roles if role in all_agents]

        return recommended[:target_count] if target_count < len(recommended) else recommended


# Example usage
if __name__ == "__main__":
    library = AgentSkillsLibrary()

    print("🎯 Agent Skills Library\n")
    print("=" * 80)

    # Get all agents
    all_agents = library.get_all_agents()
    print(f"\n📋 Total Available Agent Templates: {len(all_agents)}\n")

    # Show research agents
    print("🔬 Research Agents:")
    print("-" * 80)
    for role, template in library.get_research_agents().items():
        print(f"\n{template.name}")
        print(f"  Role: {role.value}")
        print(f"  Focus: {template.primary_focus}")
        print(f"  Expertise: {template.expertise_level}")
        print(f"  Optimal Team Size: {template.optimal_team_size}")
        print(f"  Skills: {len(template.skills)}")

    # Show security agents
    print("\n\n🛡️ Security Agents:")
    print("-" * 80)
    for role, template in library.get_security_agents().items():
        print(f"\n{template.name}")
        print(f"  Focus: {template.primary_focus}")
        print(f"  Skills: {', '.join([s.name for s in template.skills])}")

    # Get recommendations
    print("\n\n💡 Agent Recommendations:")
    print("-" * 80)

    print("\nFor: Security Audit (High Complexity)")
    recommended = library.recommend_agents_for_task("security_audit", "high")
    for agent in recommended:
        print(f"  • {agent.name} ({agent.expertise_level})")

    print("\nFor: Market Analysis (Medium Complexity)")
    recommended = library.recommend_agents_for_task("market_analysis", "medium")
    for agent in recommended:
        print(f"  • {agent.name} ({agent.expertise_level})")

    print("\n" + "=" * 80)
