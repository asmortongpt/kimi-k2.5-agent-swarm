#!/usr/bin/env python3
"""
Skills Framework for Kimi Agents
Modular, composable skills that agents can learn and use
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json


class SkillCategory(Enum):
    """Skill categories"""
    REASONING = "reasoning"
    CODING = "coding"
    RESEARCH = "research"
    COMMUNICATION = "communication"
    DATA_ANALYSIS = "data_analysis"
    SECURITY = "security"
    CREATIVE = "creative"
    TECHNICAL = "technical"


class SkillLevel(Enum):
    """Skill proficiency levels"""
    NOVICE = 1
    INTERMEDIATE = 2
    ADVANCED = 3
    EXPERT = 4
    MASTER = 5


@dataclass
class SkillMetrics:
    """Metrics for skill performance"""
    success_count: int = 0
    failure_count: int = 0
    average_latency: float = 0.0
    last_used: Optional[datetime] = None
    proficiency_score: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0

    def update(self, success: bool, latency: float):
        """Update metrics"""
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

        total = self.success_count + self.failure_count
        self.average_latency = (
            (self.average_latency * (total - 1) + latency) / total
        )
        self.last_used = datetime.utcnow()
        self._update_proficiency()

    def _update_proficiency(self):
        """Update proficiency score based on performance"""
        self.proficiency_score = (
            self.success_rate * 0.7 +
            min(1.0, self.success_count / 100) * 0.3
        )


@dataclass
class Skill:
    """
    Individual skill that an agent can possess

    A skill is a specific capability like:
    - Code review
    - SQL query generation
    - Security analysis
    - Research summarization
    """
    id: str
    name: str
    description: str
    category: SkillCategory
    level: SkillLevel = SkillLevel.NOVICE
    prerequisites: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    metrics: SkillMetrics = field(default_factory=SkillMetrics)
    metadata: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[Callable] = None

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the skill"""
        start_time = datetime.utcnow()

        try:
            if self.handler:
                result = await self.handler(context, self)
                success = True
            else:
                result = {"message": f"Skill {self.name} executed (no handler)"}
                success = True

            latency = (datetime.utcnow() - start_time).total_seconds()
            self.metrics.update(success, latency)

            return {
                "success": True,
                "result": result,
                "skill": self.name,
                "latency": latency
            }
        except Exception as e:
            latency = (datetime.utcnow() - start_time).total_seconds()
            self.metrics.update(False, latency)

            return {
                "success": False,
                "error": str(e),
                "skill": self.name,
                "latency": latency
            }

    def can_execute(self, agent_skills: Set[str]) -> bool:
        """Check if prerequisites are met"""
        return all(prereq in agent_skills for prereq in self.prerequisites)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "level": self.level.value,
            "prerequisites": self.prerequisites,
            "success_rate": self.metrics.success_rate,
            "proficiency": self.metrics.proficiency_score
        }


class SkillLibrary:
    """
    Central repository of available skills

    Features:
    - Skill discovery
    - Dependency resolution
    - Performance tracking
    - Skill recommendations
    """

    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self.categories: Dict[SkillCategory, List[str]] = {
            cat: [] for cat in SkillCategory
        }

    def register_skill(self, skill: Skill):
        """Register a new skill"""
        self.skills[skill.id] = skill
        self.categories[skill.category].append(skill.id)

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get skill by ID"""
        return self.skills.get(skill_id)

    def get_skills_by_category(self, category: SkillCategory) -> List[Skill]:
        """Get all skills in a category"""
        return [
            self.skills[skill_id]
            for skill_id in self.categories.get(category, [])
        ]

    def recommend_skills(
        self,
        current_skills: Set[str],
        task_description: str
    ) -> List[Skill]:
        """Recommend skills for a task"""
        # Simple keyword-based recommendation
        recommendations = []
        keywords = task_description.lower()

        for skill in self.skills.values():
            # Check if skill name/description matches keywords
            if any(kw in keywords for kw in skill.name.lower().split()):
                recommendations.append(skill)
            elif any(kw in keywords for kw in skill.description.lower().split()):
                recommendations.append(skill)

        return recommendations

    def get_learning_path(
        self,
        current_skills: Set[str],
        target_skill: str
    ) -> List[str]:
        """Get learning path to acquire a skill"""
        if target_skill not in self.skills:
            return []

        target = self.skills[target_skill]
        path = []
        to_learn = set(target.prerequisites) - current_skills

        # Simple dependency resolution
        while to_learn:
            skill_id = to_learn.pop()
            if skill_id in self.skills:
                path.append(skill_id)
                skill = self.skills[skill_id]
                to_learn.update(set(skill.prerequisites) - current_skills - set(path))

        path.append(target_skill)
        return path


class Agent:
    """
    Agent with learnable skills

    Features:
    - Skill acquisition
    - Skill execution
    - Performance tracking
    - Learning history
    """

    def __init__(
        self,
        name: str,
        skill_library: SkillLibrary,
        initial_skills: Optional[Set[str]] = None
    ):
        self.name = name
        self.skill_library = skill_library
        self.skills: Set[str] = initial_skills or set()
        self.execution_history: List[Dict[str, Any]] = []

    def has_skill(self, skill_id: str) -> bool:
        """Check if agent has a skill"""
        return skill_id in self.skills

    def learn_skill(self, skill_id: str) -> bool:
        """Learn a new skill"""
        skill = self.skill_library.get_skill(skill_id)
        if not skill:
            return False

        # Check prerequisites
        if not skill.can_execute(self.skills):
            return False

        self.skills.add(skill_id)
        return True

    async def execute_skill(
        self,
        skill_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a skill"""
        if not self.has_skill(skill_id):
            return {
                "success": False,
                "error": f"Agent {self.name} does not have skill {skill_id}"
            }

        skill = self.skill_library.get_skill(skill_id)
        if not skill:
            return {
                "success": False,
                "error": f"Skill {skill_id} not found in library"
            }

        result = await skill.execute(context)

        # Record execution
        self.execution_history.append({
            "skill": skill_id,
            "timestamp": datetime.utcnow().isoformat(),
            "success": result["success"],
            "latency": result.get("latency", 0)
        })

        return result

    def get_recommended_skills(self, task: str) -> List[Skill]:
        """Get recommended skills for a task"""
        return self.skill_library.recommend_skills(self.skills, task)

    def get_learning_path(self, target_skill: str) -> List[str]:
        """Get path to learn a target skill"""
        return self.skill_library.get_learning_path(self.skills, target_skill)

    def get_statistics(self) -> Dict[str, Any]:
        """Get agent statistics"""
        total_executions = len(self.execution_history)
        successful = sum(1 for h in self.execution_history if h["success"])

        return {
            "name": self.name,
            "total_skills": len(self.skills),
            "total_executions": total_executions,
            "success_rate": successful / total_executions if total_executions > 0 else 0,
            "skills": list(self.skills)
        }


# Pre-built Skills

def create_code_review_skill() -> Skill:
    """Create code review skill"""
    async def handler(context, skill):
        code = context.get("code", "")
        return {
            "issues_found": 3,
            "suggestions": [
                "Add error handling",
                "Improve variable names",
                "Add docstrings"
            ],
            "severity": "medium"
        }

    return Skill(
        id="code_review",
        name="Code Review",
        description="Review code for quality, security, and best practices",
        category=SkillCategory.CODING,
        level=SkillLevel.ADVANCED,
        prerequisites=["basic_programming"],
        handler=handler
    )


def create_sql_generation_skill() -> Skill:
    """Create SQL query generation skill"""
    async def handler(context, skill):
        description = context.get("description", "")
        return {
            "query": "SELECT * FROM users WHERE active = true",
            "confidence": 0.85
        }

    return Skill(
        id="sql_generation",
        name="SQL Query Generation",
        description="Generate SQL queries from natural language",
        category=SkillCategory.DATA_ANALYSIS,
        level=SkillLevel.INTERMEDIATE,
        prerequisites=["database_basics"],
        handler=handler
    )


def create_security_analysis_skill() -> Skill:
    """Create security analysis skill"""
    async def handler(context, skill):
        code = context.get("code", "")
        return {
            "vulnerabilities": [
                {"type": "SQL Injection", "severity": "high", "line": 42},
                {"type": "XSS", "severity": "medium", "line": 78}
            ],
            "risk_score": 7.5
        }

    return Skill(
        id="security_analysis",
        name="Security Analysis",
        description="Analyze code for security vulnerabilities",
        category=SkillCategory.SECURITY,
        level=SkillLevel.EXPERT,
        prerequisites=["code_review", "security_basics"],
        handler=handler
    )


# Example usage
async def demo_skills():
    """Demonstrate skills framework"""
    print("🎓 Skills Framework Demo\n")

    # Create skill library
    library = SkillLibrary()

    # Register skills
    print("📚 Registering skills...")
    skills_to_register = [
        Skill(
            id="basic_programming",
            name="Basic Programming",
            description="Understanding of programming fundamentals",
            category=SkillCategory.CODING,
            level=SkillLevel.NOVICE
        ),
        Skill(
            id="database_basics",
            name="Database Basics",
            description="Understanding of database concepts",
            category=SkillCategory.DATA_ANALYSIS,
            level=SkillLevel.NOVICE
        ),
        Skill(
            id="security_basics",
            name="Security Basics",
            description="Understanding of security principles",
            category=SkillCategory.SECURITY,
            level=SkillLevel.NOVICE
        ),
        create_code_review_skill(),
        create_sql_generation_skill(),
        create_security_analysis_skill()
    ]

    for skill in skills_to_register:
        library.register_skill(skill)

    print(f"✅ Registered {len(library.skills)} skills\n")

    # Create agent
    agent = Agent(
        name="Junior Dev",
        skill_library=library,
        initial_skills={"basic_programming", "database_basics"}
    )

    print(f"🤖 Agent: {agent.name}")
    print(f"Initial skills: {agent.skills}\n")

    # Learn new skill
    print("📖 Learning new skill: code_review")
    if agent.learn_skill("code_review"):
        print("✅ Skill learned successfully\n")
    else:
        print("❌ Failed to learn skill (missing prerequisites)\n")

    # Try to learn advanced skill without prerequisites
    print("📖 Attempting to learn: security_analysis")
    if agent.learn_skill("security_analysis"):
        print("✅ Skill learned successfully\n")
    else:
        print("❌ Failed to learn skill (missing prerequisites)")
        # Get learning path
        path = agent.get_learning_path("security_analysis")
        print(f"💡 Learning path required: {' → '.join(path)}\n")

    # Execute skill
    print("🎯 Executing skill: code_review")
    result = await agent.execute_skill(
        "code_review",
        {"code": "def foo(): pass"}
    )
    print(f"Result: {json.dumps(result, indent=2)}\n")

    # Show statistics
    print("📊 Agent Statistics:")
    stats = agent.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(demo_skills())
