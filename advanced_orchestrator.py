#!/usr/bin/env python3
"""
Advanced Kimi K2.5 Agent Orchestrator
Custom agent configuration with skills-based assignment
"""

import asyncio
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json

from kimi_client import KimiClient, ProviderType, AgentSwarmConfig
from agent_skills_library import AgentSkillsLibrary, AgentRole, AgentTemplate


class TaskComplexity(Enum):
    """Task complexity levels"""
    LOW = "low"              # 5-15 agents
    MEDIUM = "medium"        # 15-35 agents
    HIGH = "high"            # 35-65 agents
    EXTREME = "extreme"      # 65-100 agents


@dataclass
class AgentAssignment:
    """Individual agent assignment"""
    agent_template: AgentTemplate
    count: int
    specific_tasks: List[str] = field(default_factory=list)
    priority: int = 1  # 1-5, higher = more critical


@dataclass
class SwarmConfiguration:
    """Complete swarm configuration"""
    task_description: str
    complexity: TaskComplexity
    agent_assignments: List[AgentAssignment]
    total_agents: int
    execution_strategy: str  # "parallel", "pipeline", "hierarchical"
    context: Dict[str, Any] = field(default_factory=dict)


class AdvancedOrchestrator:
    """Advanced agent orchestrator with custom skills"""

    def __init__(
        self,
        provider: ProviderType = ProviderType.OLLAMA,
        max_agents: int = 100
    ):
        self.client = KimiClient(
            provider=provider,
            swarm_config=AgentSwarmConfig(
                max_agents=max_agents,
                parallel_execution=True,
                enable_thinking_mode=True
            )
        )
        self.skills_library = AgentSkillsLibrary()

    def create_swarm_config(
        self,
        task: str,
        complexity: TaskComplexity,
        agent_roles: List[AgentRole],
        execution_strategy: str = "parallel",
        context: Optional[Dict[str, Any]] = None
    ) -> SwarmConfiguration:
        """Create a swarm configuration from agent roles"""

        agent_assignments = []
        total_agents = 0

        # Get complexity-based agent count
        complexity_ranges = {
            TaskComplexity.LOW: (5, 15),
            TaskComplexity.MEDIUM: (15, 35),
            TaskComplexity.HIGH: (35, 65),
            TaskComplexity.EXTREME: (65, 100)
        }

        min_agents, max_agents = complexity_ranges[complexity]
        target_agents = (min_agents + max_agents) // 2

        # Distribute agents across roles
        agents_per_role = target_agents // len(agent_roles)
        remainder = target_agents % len(agent_roles)

        for i, role in enumerate(agent_roles):
            template = self.skills_library.get_agent_by_role(role)
            if template:
                # Give extra agents to first roles (usually more important)
                count = agents_per_role + (1 if i < remainder else 0)
                agent_assignments.append(AgentAssignment(
                    agent_template=template,
                    count=count,
                    priority=5 - (i // 2)  # Decrease priority for later agents
                ))
                total_agents += count

        return SwarmConfiguration(
            task_description=task,
            complexity=complexity,
            agent_assignments=agent_assignments,
            total_agents=total_agents,
            execution_strategy=execution_strategy,
            context=context or {}
        )

    def generate_prompt_from_config(self, config: SwarmConfiguration) -> str:
        """Generate optimized prompt from swarm configuration"""

        prompt = f"""# Task: {config.task_description}

## Agent Swarm Configuration

**Total Agents**: {config.total_agents}
**Complexity**: {config.complexity.value}
**Execution Strategy**: {config.execution_strategy}

## Agent Assignments & Specializations

"""

        for assignment in config.agent_assignments:
            template = assignment.agent_template
            prompt += f"""
### {template.name} (Priority: {assignment.priority}) - {assignment.count} agents

**Role**: {template.role.value}
**Focus**: {template.primary_focus}
**Expertise Level**: {template.expertise_level}

**Key Skills**:
"""
            for skill in template.skills:
                prompt += f"- {skill.name}: {skill.description}\n"
                prompt += f"  Expertise: {', '.join(skill.expertise_areas)}\n"

            if assignment.specific_tasks:
                prompt += f"\n**Specific Tasks**:\n"
                for task in assignment.specific_tasks:
                    prompt += f"- {task}\n"

            prompt += "\n"

        # Add execution strategy instructions
        if config.execution_strategy == "parallel":
            prompt += """
## Execution Strategy: Parallel

All agents should work simultaneously on their assigned tasks. Coordinate to avoid
duplication and ensure comprehensive coverage.
"""
        elif config.execution_strategy == "pipeline":
            prompt += """
## Execution Strategy: Pipeline

Agents execute in stages:
1. First priority agents complete their tasks
2. Results feed into next stage
3. Continue until all stages complete
"""
        elif config.execution_strategy == "hierarchical":
            prompt += """
## Execution Strategy: Hierarchical

Create a hierarchy:
- Master Orchestrator coordinates all work
- Domain leads manage specialist agents
- Specialists execute detailed tasks
- Synthesizer combines all outputs
"""

        # Add context
        if config.context:
            prompt += f"\n## Additional Context\n\n{json.dumps(config.context, indent=2)}\n"

        # Add output format
        prompt += """
## Expected Output

Provide a comprehensive report that:
1. Addresses all aspects of the task
2. Includes contributions from each agent type
3. Synthesizes findings into actionable insights
4. Identifies any gaps or areas needing more research
5. Provides clear recommendations

Format the output with clear sections, bullet points, and specific details.
"""

        return prompt

    async def execute_swarm(
        self,
        config: SwarmConfiguration
    ) -> Dict[str, Any]:
        """Execute the configured agent swarm"""

        prompt = self.generate_prompt_from_config(config)

        print(f"🚀 Executing Agent Swarm")
        print(f"  Total Agents: {config.total_agents}")
        print(f"  Complexity: {config.complexity.value}")
        print(f"  Strategy: {config.execution_strategy}")
        print(f"  Agent Types: {len(config.agent_assignments)}")
        print()

        response = await self.client.agent_swarm_task(
            task=prompt,
            context=config.context,
            max_agents=config.total_agents
        )

        return response

    async def execute_custom_swarm(
        self,
        task: str,
        agent_roles: List[AgentRole],
        complexity: TaskComplexity = TaskComplexity.MEDIUM,
        execution_strategy: str = "parallel",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a custom agent swarm with specified roles"""

        config = self.create_swarm_config(
            task=task,
            complexity=complexity,
            agent_roles=agent_roles,
            execution_strategy=execution_strategy,
            context=context
        )

        return await self.execute_swarm(config)

    async def execute_recommended_swarm(
        self,
        task: str,
        task_type: str,
        complexity: TaskComplexity = TaskComplexity.MEDIUM,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute swarm with automatically recommended agents"""

        # Get recommended agents
        recommended = self.skills_library.recommend_agents_for_task(
            task_type,
            complexity.value
        )

        agent_roles = [agent.role for agent in recommended]

        return await self.execute_custom_swarm(
            task=task,
            agent_roles=agent_roles,
            complexity=complexity,
            context=context
        )

    async def close(self):
        """Close the client"""
        await self.client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Example usage
async def main():
    """Demonstration of advanced orchestrator"""

    print("=" * 80)
    print("🎯 Advanced Agent Orchestrator Demo")
    print("=" * 80)
    print()

    async with AdvancedOrchestrator() as orchestrator:

        # Example 1: Custom agent configuration for security audit
        print("\n📋 Example 1: Security Audit with Custom Agent Configuration")
        print("-" * 80)

        security_roles = [
            AgentRole.SECURITY_AUDITOR,
            AgentRole.PENETRATION_TESTER,
            AgentRole.SECURITY_ENGINEER,
            AgentRole.COMPLIANCE_OFFICER,
            AgentRole.CRYPTOGRAPHER
        ]

        result1 = await orchestrator.execute_custom_swarm(
            task="""Perform comprehensive security audit of a Flask-based web application:
            - Identify all OWASP Top 10 vulnerabilities
            - Review authentication and authorization mechanisms
            - Analyze cryptographic implementations
            - Assess compliance with SOC 2 requirements
            - Provide detailed remediation plan
            """,
            agent_roles=security_roles,
            complexity=TaskComplexity.HIGH,
            execution_strategy="hierarchical",
            context={
                "framework": "Flask",
                "compliance": ["SOC 2", "OWASP"],
                "critical_assets": ["User data", "Payment info", "API keys"]
            }
        )

        print("\n✅ Security Audit Complete")
        print(f"Response length: {len(str(result1))} characters")
        print(f"Preview: {str(result1)[:500]}...")

        # Example 2: Recommended agents for market analysis
        print("\n\n📋 Example 2: Market Analysis with Recommended Agents")
        print("-" * 80)

        result2 = await orchestrator.execute_recommended_swarm(
            task="""Analyze the AI agent framework market:
            - Identify top 10 competitors
            - Evaluate strengths, weaknesses, opportunities, threats
            - Analyze pricing models and total cost of ownership
            - Assess market trends and growth projections
            - Recommend positioning strategy
            """,
            task_type="market_analysis",
            complexity=TaskComplexity.MEDIUM,
            context={
                "target_market": "Enterprise AI",
                "budget": "$1M-$5M",
                "timeline": "12 months"
            }
        )

        print("\n✅ Market Analysis Complete")
        print(f"Response length: {len(str(result2))} characters")

        # Example 3: Complex software development project
        print("\n\n📋 Example 3: Full-Stack Development Project")
        print("-" * 80)

        development_roles = [
            AgentRole.SOFTWARE_ARCHITECT,
            AgentRole.BACKEND_DEVELOPER,
            AgentRole.FRONTEND_DEVELOPER,
            AgentRole.DEVOPS_ENGINEER,
            AgentRole.SECURITY_ENGINEER,
            AgentRole.QA_ENGINEER,
            AgentRole.TECHNICAL_WRITER,
            AgentRole.PERFORMANCE_ENGINEER
        ]

        result3 = await orchestrator.execute_custom_swarm(
            task="""Design and plan a real-time fleet management system:
            - System architecture (microservices, event-driven)
            - Backend APIs (REST + GraphQL)
            - Frontend dashboard (React + TypeScript)
            - Real-time telemetry processing (WebSocket, Kafka)
            - Database design (PostgreSQL + Redis)
            - CI/CD pipeline (GitHub Actions, Docker, Kubernetes)
            - Security architecture (OAuth2, encryption, audit logging)
            - Performance optimization (caching, CDN, load balancing)
            - Testing strategy (unit, integration, E2E, load tests)
            - Documentation (API docs, deployment guide, user manual)
            """,
            agent_roles=development_roles,
            complexity=TaskComplexity.EXTREME,
            execution_strategy="pipeline",
            context={
                "scale": "10,000 vehicles",
                "compliance": ["FedRAMP", "SOC 2"],
                "budget": "$2M",
                "timeline": "9 months",
                "team_size": 12
            }
        )

        print("\n✅ Development Plan Complete")
        print(f"Response length: {len(str(result3))} characters")

    print("\n" + "=" * 80)
    print("✅ All Examples Complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
