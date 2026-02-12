#!/usr/bin/env python3
"""
Mock Provider for Testing
Simulates AI provider responses without making real API calls.
"""

import asyncio
import random
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from core.models import ChatResponse, Message, MessageRole, Choice, TokenUsage
from core.exceptions import RateLimitError, ProviderUnavailableError, TimeoutError


class MockProvider:
    """
    Mock AI provider for testing.

    Simulates various scenarios:
    - Successful responses
    - Rate limiting
    - Timeouts
    - Provider errors
    - Variable latency
    """

    def __init__(
        self,
        failure_rate: float = 0.0,
        rate_limit_probability: float = 0.0,
        timeout_probability: float = 0.0,
        min_latency_ms: float = 10.0,
        max_latency_ms: float = 100.0,
        simulate_token_usage: bool = True
    ):
        """
        Initialize mock provider.

        Args:
            failure_rate: Probability of provider errors (0.0-1.0)
            rate_limit_probability: Probability of rate limit errors
            timeout_probability: Probability of timeouts
            min_latency_ms: Minimum response latency
            max_latency_ms: Maximum response latency
            simulate_token_usage: Include token usage in responses
        """
        self.failure_rate = failure_rate
        self.rate_limit_probability = rate_limit_probability
        self.timeout_probability = timeout_probability
        self.min_latency_ms = min_latency_ms
        self.max_latency_ms = max_latency_ms
        self.simulate_token_usage = simulate_token_usage

        # Statistics
        self.request_count = 0
        self.success_count = 0
        self.failure_count = 0

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> ChatResponse:
        """
        Simulate chat completion request.

        Args:
            messages: Chat messages
            **kwargs: Additional parameters

        Returns:
            Mock ChatResponse

        Raises:
            RateLimitError: If rate limiting simulated
            ProviderUnavailableError: If provider error simulated
            TimeoutError: If timeout simulated
        """
        self.request_count += 1

        # Simulate latency
        latency = random.uniform(self.min_latency_ms, self.max_latency_ms)
        await asyncio.sleep(latency / 1000.0)

        # Simulate timeout
        if random.random() < self.timeout_probability:
            raise TimeoutError(
                timeout_seconds=30.0,
                operation="mock_chat"
            )

        # Simulate rate limiting
        if random.random() < self.rate_limit_probability:
            raise RateLimitError(
                provider="mock",
                retry_after=60,
                limit_type="requests"
            )

        # Simulate provider errors
        if random.random() < self.failure_rate:
            self.failure_count += 1
            raise ProviderUnavailableError(
                provider="mock",
                status_code=503
            )

        # Generate successful response
        self.success_count += 1

        # Create mock response content
        last_message = messages[-1]["content"]
        response_content = self._generate_response(last_message)

        # Estimate tokens
        prompt_tokens = sum(len(m["content"].split()) for m in messages) * 1.3
        completion_tokens = len(response_content.split()) * 1.3
        total_tokens = int(prompt_tokens + completion_tokens)

        response = ChatResponse(
            id=f"mock_{int(time.time() * 1000)}_{self.request_count}",
            created=int(time.time()),
            model="mock-gpt-4",
            choices=[
                Choice(
                    index=0,
                    message=Message(
                        role=MessageRole.ASSISTANT,
                        content=response_content
                    ),
                    finish_reason="stop"
                )
            ],
            usage=TokenUsage(
                prompt_tokens=int(prompt_tokens),
                completion_tokens=int(completion_tokens),
                total_tokens=total_tokens
            ) if self.simulate_token_usage else None,
            provider="mock"
        )

        return response

    def _generate_response(self, prompt: str) -> str:
        """Generate mock response based on prompt."""
        # Simple response generation
        templates = [
            f"I understand you're asking about: {prompt[:100]}. Here's a comprehensive response...",
            f"Regarding your question about {prompt[:50]}, let me provide detailed information...",
            f"That's an interesting question. To address {prompt[:50]}, I would say...",
            f"Based on your query about {prompt[:50]}, here are my thoughts..."
        ]

        base_response = random.choice(templates)

        # Add some filler content
        filler = (
            "\n\nThis is a detailed explanation with multiple points:\n"
            "1. First important point about the topic\n"
            "2. Second consideration to keep in mind\n"
            "3. Third aspect worth exploring\n"
            "4. Fourth element to understand\n"
            "5. Final thoughts and conclusions\n\n"
            "In summary, this covers the key aspects comprehensively."
        )

        return base_response + filler

    async def batch_chat(self, requests: List[Dict[str, Any]]) -> List[ChatResponse]:
        """Process multiple requests."""
        results = []
        for req in requests:
            try:
                response = await self.chat(req["messages"])
                results.append(response)
            except Exception as e:
                # In real implementation, might want to handle errors differently
                raise

        return results

    def reset_stats(self):
        """Reset statistics."""
        self.request_count = 0
        self.success_count = 0
        self.failure_count = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get provider statistics."""
        return {
            "request_count": self.request_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_count / self.request_count if self.request_count > 0 else 0.0
        }


class ReliableMockProvider(MockProvider):
    """Mock provider that always succeeds (for testing happy paths)."""

    def __init__(self, **kwargs):
        super().__init__(
            failure_rate=0.0,
            rate_limit_probability=0.0,
            timeout_probability=0.0,
            **kwargs
        )


class UnreliableMockProvider(MockProvider):
    """Mock provider with high failure rate (for testing error handling)."""

    def __init__(self, **kwargs):
        super().__init__(
            failure_rate=0.3,
            rate_limit_probability=0.2,
            timeout_probability=0.1,
            **kwargs
        )


class SlowMockProvider(MockProvider):
    """Mock provider with high latency (for testing timeouts)."""

    def __init__(self, **kwargs):
        super().__init__(
            min_latency_ms=500.0,
            max_latency_ms=2000.0,
            **kwargs
        )
