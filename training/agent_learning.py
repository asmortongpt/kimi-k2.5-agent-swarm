#!/usr/bin/env python3
"""
Agent Training & Learning System
Continuous learning and improvement for Kimi agents
"""

import asyncio
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import random


class LearningStrategy(Enum):
    """Learning strategies"""
    SUPERVISED = "supervised"  # Learn from labeled examples
    REINFORCEMENT = "reinforcement"  # Learn from rewards/penalties
    IMITATION = "imitation"  # Learn by observing expert behavior
    SELF_PLAY = "self_play"  # Learn by practicing
    ACTIVE = "active"  # Request labels for uncertain cases


class FeedbackType(Enum):
    """Types of feedback"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    CORRECTION = "correction"


@dataclass
class TrainingExample:
    """Single training example"""
    id: str
    input_data: Dict[str, Any]
    expected_output: Optional[Dict[str, Any]] = None
    actual_output: Optional[Dict[str, Any]] = None
    feedback: Optional[FeedbackType] = None
    reward: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LearningMetrics:
    """Metrics for learning progress"""
    examples_seen: int = 0
    accuracy: float = 0.0
    average_reward: float = 0.0
    improvement_rate: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def update(self, correct: bool, reward: float):
        """Update metrics"""
        self.examples_seen += 1
        old_accuracy = self.accuracy

        # Update accuracy (moving average)
        alpha = 0.1  # Learning rate for moving average
        self.accuracy = (1 - alpha) * self.accuracy + alpha * (1.0 if correct else 0.0)

        # Update average reward
        self.average_reward = (
            (self.average_reward * (self.examples_seen - 1) + reward) /
            self.examples_seen
        )

        # Calculate improvement rate
        self.improvement_rate = self.accuracy - old_accuracy
        self.last_updated = datetime.utcnow()


class ExperienceReplay:
    """
    Experience replay buffer for reinforcement learning

    Stores past experiences and allows sampling for training
    """

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.buffer: List[TrainingExample] = []
        self.priorities: List[float] = []

    def add(self, example: TrainingExample, priority: float = 1.0):
        """Add experience to buffer"""
        if len(self.buffer) >= self.max_size:
            # Remove oldest (or lowest priority)
            min_idx = min(range(len(self.priorities)), key=self.priorities.__getitem__)
            del self.buffer[min_idx]
            del self.priorities[min_idx]

        self.buffer.append(example)
        self.priorities.append(priority)

    def sample(self, batch_size: int = 32) -> List[TrainingExample]:
        """Sample a batch of experiences"""
        if len(self.buffer) == 0:
            return []

        # Prioritized sampling
        total_priority = sum(self.priorities)
        probabilities = [p / total_priority for p in self.priorities]

        indices = random.choices(
            range(len(self.buffer)),
            weights=probabilities,
            k=min(batch_size, len(self.buffer))
        )

        return [self.buffer[i] for i in indices]

    def size(self) -> int:
        """Get buffer size"""
        return len(self.buffer)


class AgentTrainer:
    """
    Agent trainer for continuous learning

    Features:
    - Multiple learning strategies
    - Experience replay
    - Performance tracking
    - Curriculum learning
    - Model updates
    """

    def __init__(
        self,
        agent_id: str,
        strategy: LearningStrategy = LearningStrategy.REINFORCEMENT
    ):
        self.agent_id = agent_id
        self.strategy = strategy
        self.metrics = LearningMetrics()
        self.experience_buffer = ExperienceReplay()
        self.training_history: List[TrainingExample] = []

    async def collect_feedback(
        self,
        input_data: Dict[str, Any],
        output: Dict[str, Any],
        feedback_type: FeedbackType,
        correction: Optional[Dict[str, Any]] = None
    ) -> TrainingExample:
        """Collect feedback on agent performance"""
        # Convert feedback to reward
        reward_map = {
            FeedbackType.POSITIVE: 1.0,
            FeedbackType.NEUTRAL: 0.0,
            FeedbackType.NEGATIVE: -1.0,
            FeedbackType.CORRECTION: 0.5  # Partial credit for corrections
        }
        reward = reward_map[feedback_type]

        example = TrainingExample(
            id=f"example_{len(self.training_history)}",
            input_data=input_data,
            actual_output=output,
            expected_output=correction if correction else output,
            feedback=feedback_type,
            reward=reward
        )

        # Add to experience buffer with priority based on reward magnitude
        priority = abs(reward) + 0.1  # Ensure non-zero priority
        self.experience_buffer.add(example, priority)

        # Update metrics
        correct = feedback_type in [FeedbackType.POSITIVE, FeedbackType.CORRECTION]
        self.metrics.update(correct, reward)

        # Store in history
        self.training_history.append(example)

        return example

    async def train_batch(self, batch_size: int = 32) -> Dict[str, Any]:
        """Train on a batch of experiences"""
        if self.experience_buffer.size() < batch_size:
            return {
                "success": False,
                "message": "Insufficient training examples"
            }

        # Sample batch from experience replay
        batch = self.experience_buffer.sample(batch_size)

        # In production, this would update the model
        # For now, we'll simulate training
        total_loss = 0.0
        for example in batch:
            # Compute "loss" (difference between expected and actual)
            loss = 1.0 - example.reward  # Simplified loss
            total_loss += loss

        average_loss = total_loss / len(batch)

        return {
            "success": True,
            "batch_size": len(batch),
            "average_loss": average_loss,
            "current_accuracy": self.metrics.accuracy,
            "examples_trained": self.metrics.examples_seen
        }

    def get_learning_progress(self) -> Dict[str, Any]:
        """Get learning progress report"""
        return {
            "agent_id": self.agent_id,
            "strategy": self.strategy.value,
            "examples_seen": self.metrics.examples_seen,
            "accuracy": self.metrics.accuracy,
            "average_reward": self.metrics.average_reward,
            "improvement_rate": self.metrics.improvement_rate,
            "buffer_size": self.experience_buffer.size(),
            "last_updated": self.metrics.last_updated.isoformat()
        }

    def should_train(self) -> bool:
        """Determine if it's time to train"""
        # Train every 100 examples or every hour
        return (
            self.metrics.examples_seen % 100 == 0 or
            (datetime.utcnow() - self.metrics.last_updated) > timedelta(hours=1)
        )


class CurriculumLearning:
    """
    Curriculum learning for progressive difficulty

    Starts with easy examples and gradually increases difficulty
    """

    def __init__(self):
        self.difficulty_levels = {
            "easy": [],
            "medium": [],
            "hard": [],
            "expert": []
        }
        self.current_level = "easy"

    def add_example(self, example: TrainingExample, difficulty: str):
        """Add example at specific difficulty"""
        if difficulty in self.difficulty_levels:
            self.difficulty_levels[difficulty].append(example)

    def get_next_batch(self, batch_size: int = 32) -> List[TrainingExample]:
        """Get next batch according to curriculum"""
        # Get examples from current difficulty level
        current_examples = self.difficulty_levels.get(self.current_level, [])

        if len(current_examples) < batch_size:
            # Move to next difficulty level
            self._advance_level()
            current_examples = self.difficulty_levels.get(self.current_level, [])

        return random.sample(
            current_examples,
            min(batch_size, len(current_examples))
        )

    def _advance_level(self):
        """Advance to next difficulty level"""
        levels = ["easy", "medium", "hard", "expert"]
        current_idx = levels.index(self.current_level)
        if current_idx < len(levels) - 1:
            self.current_level = levels[current_idx + 1]


class AgentEvaluator:
    """
    Evaluate agent performance

    Features:
    - Test set evaluation
    - A/B testing
    - Performance monitoring
    - Regression detection
    """

    def __init__(self):
        self.test_sets: Dict[str, List[TrainingExample]] = {}
        self.evaluation_history: List[Dict[str, Any]] = []

    def add_test_set(self, name: str, examples: List[TrainingExample]):
        """Add a test set"""
        self.test_sets[name] = examples

    async def evaluate(
        self,
        agent_id: str,
        test_set_name: str,
        execute_fn: callable
    ) -> Dict[str, Any]:
        """Evaluate agent on test set"""
        if test_set_name not in self.test_sets:
            return {
                "success": False,
                "error": f"Test set '{test_set_name}' not found"
            }

        test_set = self.test_sets[test_set_name]
        results = []

        for example in test_set:
            # Execute agent on test example
            output = await execute_fn(example.input_data)

            # Compare with expected output
            correct = output == example.expected_output
            results.append({
                "example_id": example.id,
                "correct": correct,
                "output": output,
                "expected": example.expected_output
            })

        # Calculate metrics
        accuracy = sum(1 for r in results if r["correct"]) / len(results)

        evaluation = {
            "agent_id": agent_id,
            "test_set": test_set_name,
            "accuracy": accuracy,
            "total_examples": len(results),
            "correct": sum(1 for r in results if r["correct"]),
            "timestamp": datetime.utcnow().isoformat(),
            "results": results
        }

        self.evaluation_history.append(evaluation)
        return evaluation

    def detect_regression(self, agent_id: str, threshold: float = 0.05) -> bool:
        """Detect if agent performance has regressed"""
        agent_evals = [
            e for e in self.evaluation_history
            if e["agent_id"] == agent_id
        ]

        if len(agent_evals) < 2:
            return False

        # Compare last two evaluations
        latest = agent_evals[-1]["accuracy"]
        previous = agent_evals[-2]["accuracy"]

        return latest < previous - threshold


# Example usage
async def demo_training():
    """Demonstrate agent training system"""
    print("🎓 Agent Training & Learning System Demo\n")

    # Create trainer
    trainer = AgentTrainer(
        agent_id="agent_001",
        strategy=LearningStrategy.REINFORCEMENT
    )

    print(f"🤖 Training agent: {trainer.agent_id}")
    print(f"Strategy: {trainer.strategy.value}\n")

    # Simulate agent learning over time
    print("📚 Collecting training examples...\n")

    scenarios = [
        {
            "input": {"task": "code_review", "code": "def foo(): pass"},
            "output": {"issues": 2, "score": 0.7},
            "feedback": FeedbackType.POSITIVE
        },
        {
            "input": {"task": "security_scan", "code": "exec(user_input)"},
            "output": {"vulnerabilities": 1, "severity": "high"},
            "feedback": FeedbackType.POSITIVE
        },
        {
            "input": {"task": "optimization", "code": "slow_code()"},
            "output": {"suggestions": []},
            "feedback": FeedbackType.NEGATIVE,
            "correction": {"suggestions": ["use caching", "parallelize"]}
        },
        {
            "input": {"task": "refactor", "code": "messy_code()"},
            "output": {"improvements": 3},
            "feedback": FeedbackType.CORRECTION,
            "correction": {"improvements": 5}
        }
    ]

    for i, scenario in enumerate(scenarios, 1):
        example = await trainer.collect_feedback(
            input_data=scenario["input"],
            output=scenario["output"],
            feedback_type=scenario["feedback"],
            correction=scenario.get("correction")
        )

        print(f"Example {i}: {scenario['feedback'].value}")
        print(f"  Reward: {example.reward}")
        print(f"  Buffer size: {trainer.experience_buffer.size()}")
        print()

    # Check learning progress
    print("📊 Learning Progress:")
    progress = trainer.get_learning_progress()
    for key, value in progress.items():
        print(f"  {key}: {value}")
    print()

    # Train on batch
    print("🔄 Training on batch...")
    train_result = await trainer.train_batch(batch_size=4)
    print(f"Training result: {json.dumps(train_result, indent=2)}")
    print()

    # Create evaluator
    evaluator = AgentEvaluator()

    # Add test set
    test_examples = [
        TrainingExample(
            id="test_1",
            input_data={"task": "code_review", "code": "good_code()"},
            expected_output={"issues": 0, "score": 1.0}
        ),
        TrainingExample(
            id="test_2",
            input_data={"task": "security_scan", "code": "safe_code()"},
            expected_output={"vulnerabilities": 0}
        )
    ]

    evaluator.add_test_set("standard_tests", test_examples)

    # Mock evaluation function
    async def mock_execute(input_data):
        # Simulate agent execution
        if "code_review" in input_data["task"]:
            return {"issues": 0, "score": 1.0}
        return {"vulnerabilities": 0}

    # Evaluate
    print("✅ Evaluating agent...")
    eval_result = await evaluator.evaluate(
        agent_id=trainer.agent_id,
        test_set_name="standard_tests",
        execute_fn=mock_execute
    )

    print(f"Evaluation accuracy: {eval_result['accuracy']:.2%}")
    print(f"Correct: {eval_result['correct']}/{eval_result['total_examples']}")


if __name__ == "__main__":
    asyncio.run(demo_training())
