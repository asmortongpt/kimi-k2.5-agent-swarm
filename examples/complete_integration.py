#!/usr/bin/env python3
"""
Complete Kimi K2.5 System Integration Example
Demonstrates all 5 systems working together:
- RAG (Retrieval Augmented Generation)
- CAG (Context Augmented Generation)
- MCP (Model Context Protocol)
- Skills Framework
- Agent Training & Learning
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.vector_store import RAGVectorStore, Document, VectorStoreType
from cag.context_manager import ContextManager, ContextEntry, ContextType
from mcp_servers.mcp_client import (
    MCPClient, WebSearchMCPServer, FileSystemMCPServer,
    DatabaseMCPServer, CodeExecutionMCPServer
)
from skills.skill_framework import (
    Agent, SkillLibrary, Skill, SkillCategory, SkillLevel,
    create_code_review_skill, create_sql_generation_skill,
    create_security_analysis_skill
)
from training.agent_learning import (
    AgentTrainer, AgentEvaluator, CurriculumLearning,
    FeedbackType, LearningStrategy, TrainingExample
)
from datetime import datetime
import json


class IntegratedAgentSystem:
    """
    Complete integrated system combining all 5 components

    This demonstrates how to build a production AI agent that:
    - Retrieves relevant knowledge (RAG)
    - Maintains conversation context (CAG)
    - Uses external tools (MCP)
    - Has learnable capabilities (Skills)
    - Improves over time (Training)
    """

    def __init__(self, agent_name: str = "Production Agent"):
        self.agent_name = agent_name

        # Component 1: RAG for knowledge retrieval
        self.vector_store = None

        # Component 2: CAG for context management
        self.context_manager = None

        # Component 3: MCP for tool integration
        self.mcp_client = None

        # Component 4: Skills framework
        self.skill_library = None
        self.agent = None

        # Component 5: Training system
        self.trainer = None
        self.evaluator = None

    async def initialize(self):
        """Initialize all system components"""
        print(f"🚀 Initializing {self.agent_name}...\n")

        # 1. Initialize RAG with knowledge base
        print("📚 Setting up RAG (Retrieval Augmented Generation)...")
        self.vector_store = RAGVectorStore(
            store_type=VectorStoreType.IN_MEMORY,
            collection_name="agent_knowledge"
        )

        # Add domain knowledge
        knowledge_documents = [
            Document(
                id="k1",
                content="Kimi K2.5 supports up to 100 parallel agents with 1,500 coordinated tool calls",
                metadata={"category": "capabilities", "importance": "high"}
            ),
            Document(
                id="k2",
                content="Agent swarm reduces execution time by 4.5x compared to single-agent mode",
                metadata={"category": "performance", "importance": "high"}
            ),
            Document(
                id="k3",
                content="Use parameterized queries ($1, $2) to prevent SQL injection attacks",
                metadata={"category": "security", "importance": "critical"}
            ),
            Document(
                id="k4",
                content="Circuit breaker pattern prevents cascading failures in distributed systems",
                metadata={"category": "resilience", "importance": "high"}
            ),
            Document(
                id="k5",
                content="Multi-level caching with L1 and L2 improves response time by 3x",
                metadata={"category": "optimization", "importance": "medium"}
            ),
        ]

        await self.vector_store.add_documents(knowledge_documents)
        print(f"✅ Loaded {len(knowledge_documents)} knowledge documents\n")

        # 2. Initialize CAG context manager
        print("🧠 Setting up CAG (Context Augmented Generation)...")
        self.context_manager = ContextManager(
            vector_store=self.vector_store,
            max_context_tokens=8000
        )
        print("✅ Context manager ready\n")

        # 3. Initialize MCP tools
        print("🔧 Setting up MCP (Model Context Protocol) servers...")
        self.mcp_client = MCPClient()

        # Register tool servers
        self.mcp_client.register_server(FileSystemMCPServer())
        self.mcp_client.register_server(WebSearchMCPServer())
        self.mcp_client.register_server(DatabaseMCPServer("postgresql://localhost/db"))
        self.mcp_client.register_server(CodeExecutionMCPServer())

        # Register mock handlers for demo
        async def mock_search(params):
            return f"Search results for '{params['query']}': [Best practices documentation, Stack Overflow solutions, Security advisories]"

        async def mock_read(params):
            return f"File contents of {params['path']}: [Sample code and configuration]"

        self.mcp_client.register_tool_handler("search_web", mock_search)
        self.mcp_client.register_tool_handler("read_file", mock_read)

        print(f"✅ Registered {len(self.mcp_client.tools)} tools across {len(self.mcp_client.servers)} servers\n")

        # 4. Initialize Skills framework
        print("🎯 Setting up Skills framework...")
        self.skill_library = SkillLibrary()

        # Register base skills
        base_skills = [
            Skill(
                id="basic_programming",
                name="Basic Programming",
                description="Fundamental programming concepts",
                category=SkillCategory.CODING,
                level=SkillLevel.NOVICE
            ),
            Skill(
                id="database_basics",
                name="Database Basics",
                description="SQL and database fundamentals",
                category=SkillCategory.DATA_ANALYSIS,
                level=SkillLevel.NOVICE
            ),
            Skill(
                id="security_basics",
                name="Security Basics",
                description="Security principles and best practices",
                category=SkillCategory.SECURITY,
                level=SkillLevel.NOVICE
            ),
        ]

        # Register advanced skills
        advanced_skills = [
            create_code_review_skill(),
            create_sql_generation_skill(),
            create_security_analysis_skill()
        ]

        for skill in base_skills + advanced_skills:
            self.skill_library.register_skill(skill)

        # Create agent with initial skills
        self.agent = Agent(
            name=self.agent_name,
            skill_library=self.skill_library,
            initial_skills={"basic_programming", "database_basics", "security_basics"}
        )

        # Learn advanced skills
        self.agent.learn_skill("code_review")
        self.agent.learn_skill("sql_generation")
        self.agent.learn_skill("security_analysis")

        print(f"✅ Agent has {len(self.agent.skills)} skills\n")

        # 5. Initialize Training system
        print("🎓 Setting up Training & Learning system...")
        self.trainer = AgentTrainer(
            agent_id=self.agent_name,
            strategy=LearningStrategy.REINFORCEMENT
        )

        self.evaluator = AgentEvaluator()

        # Add test set for evaluation
        test_examples = [
            TrainingExample(
                id="test_1",
                input_data={"task": "code_review", "code": "def secure_query(): pass"},
                expected_output={"issues": 0, "score": 1.0}
            ),
            TrainingExample(
                id="test_2",
                input_data={"task": "security_scan", "code": "safe_code()"},
                expected_output={"vulnerabilities": 0}
            )
        ]

        self.evaluator.add_test_set("standard_tests", test_examples)
        print("✅ Training system ready\n")

        print(f"{'='*60}")
        print(f"✨ {self.agent_name} fully initialized!")
        print(f"{'='*60}\n")

    async def process_task(
        self,
        task_description: str,
        task_data: dict,
        expected_outcome: str = None
    ) -> dict:
        """
        Process a task using all integrated systems

        This demonstrates the complete workflow:
        1. CAG: Augment query with context and knowledge (uses RAG)
        2. Skills: Execute relevant skill
        3. MCP: Use external tools as needed
        4. Training: Collect feedback and improve
        """
        print(f"\n{'='*60}")
        print(f"📋 Task: {task_description}")
        print(f"{'='*60}\n")

        # Step 1: Add user query to context
        self.context_manager.add_user_message(task_description)

        # Step 2: Use CAG to augment query with relevant context
        print("🧠 Augmenting query with CAG + RAG...")
        augmented_prompt, metadata = await self.context_manager.process_query(
            task_description,
            retrieve_knowledge=True
        )

        print(f"Context metadata:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
        print()

        # Step 3: Determine which skill to use
        print("🎯 Selecting skill...")
        recommended_skills = self.agent.get_recommended_skills(task_description)

        if recommended_skills:
            selected_skill = recommended_skills[0]
            print(f"Selected skill: {selected_skill.name}\n")
        else:
            # Default to code review
            selected_skill = self.skill_library.get_skill("code_review")
            print(f"Using default skill: {selected_skill.name}\n")

        # Step 4: Execute skill
        print("⚙️  Executing skill...")
        skill_result = await self.agent.execute_skill(
            selected_skill.id,
            task_data
        )

        if skill_result["success"]:
            print(f"Skill executed successfully in {skill_result['latency']:.3f}s")
            print(f"Result: {json.dumps(skill_result['result'], indent=2)}\n")
        else:
            print(f"Skill execution failed: {skill_result['error']}\n")

        # Step 5: Use MCP tools for additional context
        print("🔧 Using MCP tools for research...")
        search_result = await self.mcp_client.execute_tool(
            "search_web",
            {"query": f"{task_description} best practices", "max_results": 3}
        )

        if search_result["success"]:
            print(f"Search result: {search_result['result']}\n")

        # Step 6: Combine results
        final_output = {
            "task": task_description,
            "skill_analysis": skill_result.get("result", {}),
            "research": search_result.get("result", ""),
            "augmented_context": metadata,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Step 7: Collect feedback for training
        print("🎓 Collecting feedback for training...")

        # Determine feedback type (in production, this comes from user)
        feedback_type = FeedbackType.POSITIVE if skill_result["success"] else FeedbackType.NEGATIVE

        training_example = await self.trainer.collect_feedback(
            input_data=task_data,
            output=final_output,
            feedback_type=feedback_type
        )

        print(f"Feedback: {feedback_type.value}")
        print(f"Reward: {training_example.reward}")
        print(f"Experience buffer size: {self.trainer.experience_buffer.size()}\n")

        # Step 8: Train if threshold reached
        if self.trainer.should_train():
            print("🔄 Training agent on collected experiences...")
            train_result = await self.trainer.train_batch(batch_size=4)
            if train_result["success"]:
                print(f"Training completed:")
                print(f"  Batch size: {train_result['batch_size']}")
                print(f"  Average loss: {train_result['average_loss']:.3f}")
                print(f"  Current accuracy: {train_result['current_accuracy']:.2%}\n")

        # Step 9: Update conversation context
        self.context_manager.add_response(json.dumps(final_output))

        return final_output

    async def show_statistics(self):
        """Display comprehensive system statistics"""
        print(f"\n{'='*60}")
        print("📊 System Statistics")
        print(f"{'='*60}\n")

        # Agent stats
        print("🤖 Agent Statistics:")
        agent_stats = self.agent.get_statistics()
        for key, value in agent_stats.items():
            print(f"  {key}: {value}")
        print()

        # Training progress
        print("🎓 Learning Progress:")
        learning_progress = self.trainer.get_learning_progress()
        for key, value in learning_progress.items():
            print(f"  {key}: {value}")
        print()

        # Context summary
        print("🧠 Context Summary:")
        context_summary = self.context_manager.get_context_summary()
        for key, value in context_summary.items():
            print(f"  {key}: {value}")
        print()

        # MCP tool usage
        print("🔧 Tool Usage:")
        tool_stats = self.mcp_client.get_usage_stats()
        for tool, count in tool_stats.items():
            if count > 0:
                print(f"  {tool}: {count} calls")
        print()


async def demo_complete_system():
    """
    Complete demonstration of all 5 integrated systems

    Scenario: Security-focused code review agent
    """
    print("="*60)
    print("🎯 Kimi K2.5 Complete System Integration Demo")
    print("="*60)
    print()
    print("This demo showcases all 5 systems working together:")
    print("  1. RAG - Retrieval Augmented Generation")
    print("  2. CAG - Context Augmented Generation")
    print("  3. MCP - Model Context Protocol")
    print("  4. Skills - Agent Capabilities Framework")
    print("  5. Training - Continuous Learning System")
    print()

    # Initialize integrated system
    system = IntegratedAgentSystem(agent_name="Security Review Agent")
    await system.initialize()

    # Task 1: Code review with security focus
    await system.process_task(
        task_description="Review this code for security vulnerabilities",
        task_data={
            "code": """
def login(username, password):
    query = f"SELECT * FROM users WHERE name='{username}' AND pass='{password}'"
    return db.execute(query)
            """
        }
    )

    # Task 2: SQL query generation
    await system.process_task(
        task_description="Generate a safe SQL query to find active users",
        task_data={
            "description": "Find all users with active status and last login within 30 days"
        }
    )

    # Task 3: Performance optimization review
    await system.process_task(
        task_description="Review code for performance optimization opportunities",
        task_data={
            "code": """
def process_users():
    users = []
    for id in range(1000):
        user = db.query(f"SELECT * FROM users WHERE id={id}")
        users.append(user)
    return users
            """
        }
    )

    # Show comprehensive statistics
    await system.show_statistics()

    print("\n" + "="*60)
    print("✨ Demo Complete!")
    print("="*60)
    print()
    print("All 5 systems successfully integrated and demonstrated:")
    print("  ✅ RAG retrieved relevant security knowledge")
    print("  ✅ CAG maintained conversation context")
    print("  ✅ MCP tools provided additional research")
    print("  ✅ Skills executed code review and analysis")
    print("  ✅ Training collected feedback and improved")
    print()


if __name__ == "__main__":
    asyncio.run(demo_complete_system())
