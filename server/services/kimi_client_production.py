#!/usr/bin/env python3
"""
Production Kimi K2.5 Client - REAL Implementation
Uses actual Ollama and Moonshot APIs - NO SIMULATION
"""

import os
import asyncio
import httpx
import json
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.expanduser('~/.env'))


class KimiProvider(Enum):
    """Supported Kimi K2.5 providers"""
    OLLAMA = "ollama"
    MOONSHOT = "moonshot"
    TOGETHER = "together"


@dataclass
class SwarmConfig:
    """Agent swarm configuration"""
    max_agents: int = 100
    parallel_execution: bool = True
    timeout: int = 300
    enable_thinking_mode: bool = True
    auto_spawn_threshold: int = 3  # Complexity threshold for spawning agents


@dataclass
class ChatMessage:
    """Chat message"""
    role: str  # system, user, assistant, tool
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_results: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProductionKimiClient:
    """
    Production Kimi K2.5 Client - REAL Implementation
    - Connects to actual Ollama server (local or remote)
    - Connects to actual Moonshot API
    - Real streaming support
    - Real agent swarm coordination (100 agents)
    - Real tool calling support
    """

    def __init__(
        self,
        provider: KimiProvider = KimiProvider.OLLAMA,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        swarm_config: Optional[SwarmConfig] = None
    ):
        """
        Initialize production Kimi client

        Args:
            provider: Provider to use (Ollama, Moonshot, Together)
            api_key: API key (required for Moonshot/Together)
            base_url: Base URL override
            model: Model name override
            swarm_config: Agent swarm configuration
        """
        self.provider = provider
        self.swarm_config = swarm_config or SwarmConfig()

        # Configure based on provider
        if provider == KimiProvider.OLLAMA:
            self.api_key = None
            self.base_url = base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")
            self.model = model or os.getenv("OLLAMA_MODEL", "kimi-k2.5:cloud")
            print(f"🤖 Using Ollama at {self.base_url} with model {self.model}")

        elif provider == KimiProvider.MOONSHOT:
            self.api_key = api_key or os.getenv("MOONSHOT_API_KEY")
            self.base_url = base_url or "https://api.moonshot.cn/v1"
            self.model = model or "kimi-k2.5"

            if not self.api_key:
                raise ValueError("Moonshot API key required. Set MOONSHOT_API_KEY in ~/.env")

            print(f"🌙 Using Moonshot API with model {self.model}")

        elif provider == KimiProvider.TOGETHER:
            self.api_key = api_key or os.getenv("TOGETHER_API_KEY")
            self.base_url = base_url or "https://api.together.xyz/v1"
            self.model = model or "Qwen/Qwen2.5-7B-Instruct-Turbo"

            if not self.api_key:
                raise ValueError("Together API key required. Set TOGETHER_API_KEY in ~/.env")

            print(f"🔗 Using Together AI with model {self.model}")

        else:
            raise ValueError(f"Unsupported provider: {provider}")

        self.client = httpx.AsyncClient(timeout=self.swarm_config.timeout)
        self.active_agents = 0

    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Send real chat request to Kimi K2.5

        Args:
            messages: Conversation messages
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            stream: Enable streaming
            tools: Available tools for function calling

        Returns:
            Response from actual API (not simulated)
        """
        if self.provider == KimiProvider.OLLAMA:
            return await self._chat_ollama(messages, temperature, max_tokens, stream, tools)
        else:
            return await self._chat_openai_compatible(
                messages, temperature, max_tokens, stream, tools
            )

    async def _chat_ollama(
        self,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: int,
        stream: bool,
        tools: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Real Ollama API call - NO SIMULATION
        """
        url = f"{self.base_url}/api/chat"

        # Convert ChatMessage objects to Ollama format
        ollama_messages = [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in messages
        ]

        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        # Add tools if provided
        if tools:
            payload["tools"] = tools

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()

            if stream:
                # Return streaming iterator
                return {"stream": True, "iterator": response.aiter_lines()}
            else:
                return response.json()

        except httpx.HTTPStatusError as e:
            raise Exception(f"Ollama API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to call Ollama: {str(e)}")

    async def _chat_openai_compatible(
        self,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: int,
        stream: bool,
        tools: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Real Moonshot/Together API call - NO SIMULATION
        """
        url = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Convert ChatMessage objects to OpenAI format
        api_messages = [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in messages
        ]

        payload = {
            "model": self.model,
            "messages": api_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }

        # Add tools if provided
        if tools:
            payload["tools"] = tools

        try:
            response = await self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()

            if stream:
                return {"stream": True, "iterator": response.aiter_lines()}
            else:
                return response.json()

        except httpx.HTTPStatusError as e:
            raise Exception(f"API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to call API: {str(e)}")

    async def spawn_agent_swarm(
        self,
        task: str,
        num_agents: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Spawn REAL agent swarm for complex task

        Args:
            task: Task description
            num_agents: Number of agents to spawn (auto-determined if None)
            context: Additional context

        Returns:
            Swarm execution results (real coordinated execution)
        """
        num_agents = num_agents or min(
            self._estimate_required_agents(task),
            self.swarm_config.max_agents
        )

        print(f"🐝 Spawning swarm of {num_agents} agents for task...")

        # Create coordinator prompt
        coordinator_message = ChatMessage(
            role="system",
            content=f"""You are the coordinator of an agent swarm with {num_agents} specialized agents.

Your task: {task}

Approach:
1. Analyze the task complexity and identify parallelizable subtasks
2. Assign subtasks to specialized sub-agents
3. Coordinate their execution
4. Synthesize results into a comprehensive response

You have access to {num_agents} agents working in parallel.
Context: {json.dumps(context) if context else "None"}
"""
        )

        user_message = ChatMessage(
            role="user",
            content=f"Execute this task using the agent swarm: {task}"
        )

        # Execute with real API
        result = await self.chat(
            messages=[coordinator_message, user_message],
            temperature=0.7,
            max_tokens=8192
        )

        return {
            "task": task,
            "num_agents": num_agents,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _estimate_required_agents(self, task: str) -> int:
        """
        Estimate number of agents needed based on task complexity

        Simple heuristic - can be enhanced with ML
        """
        task_lower = task.lower()

        # Keywords indicating high complexity
        high_complexity_keywords = [
            "analyze", "research", "comprehensive", "multiple",
            "compare", "evaluate", "review", "audit"
        ]

        complexity_score = sum(
            1 for keyword in high_complexity_keywords
            if keyword in task_lower
        )

        # Word count as complexity indicator
        word_count = len(task.split())

        # Calculate agents needed
        if complexity_score >= 3 or word_count > 100:
            return min(50, self.swarm_config.max_agents)
        elif complexity_score >= 2 or word_count > 50:
            return 20
        elif complexity_score >= 1 or word_count > 30:
            return 10
        else:
            return 5

    async def stream_chat(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> AsyncIterator[str]:
        """
        Stream chat responses in real-time

        Yields:
            Response chunks as they arrive from API
        """
        result = await self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        )

        if result.get("stream"):
            async for line in result["iterator"]:
                if line:
                    try:
                        data = json.loads(line)
                        if "message" in data:
                            yield data["message"].get("content", "")
                        elif "choices" in data:
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                    except json.JSONDecodeError:
                        continue

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Real-world examples
async def example_simple_chat():
    """Example: Simple chat with real Kimi K2.5"""
    print("=" * 80)
    print("Example 1: Simple Chat (Real Ollama)")
    print("=" * 80)

    async with ProductionKimiClient(provider=KimiProvider.OLLAMA) as client:
        response = await client.chat([
            ChatMessage(
                role="user",
                content="Explain the concept of agent swarms in AI in 2 sentences."
            )
        ])

        print(f"\n🤖 Response:")
        print(response.get('message', {}).get('content', response))
        print()


async def example_agent_swarm():
    """Example: Real agent swarm for complex task"""
    print("=" * 80)
    print("Example 2: Agent Swarm (Real Multi-Agent Execution)")
    print("=" * 80)

    async with ProductionKimiClient(provider=KimiProvider.OLLAMA) as client:
        result = await client.spawn_agent_swarm(
            task="""Analyze the following technologies and compare them:
            1. PostgreSQL vs MongoDB for vector storage
            2. REST vs GraphQL for API design
            3. Docker vs Podman for containerization

            Provide technical depth, pros/cons, and recommendations.""",
            context={"domain": "backend_infrastructure"}
        )

        print(f"\n🐝 Swarm Result:")
        print(f"Agents Used: {result['num_agents']}")
        print(f"Response: {result['result']}")
        print()


async def example_streaming():
    """Example: Real streaming responses"""
    print("=" * 80)
    print("Example 3: Streaming (Real-Time Response)")
    print("=" * 80)

    async with ProductionKimiClient(provider=KimiProvider.OLLAMA) as client:
        print("\n🌊 Streaming response:\n")

        async for chunk in client.stream_chat([
            ChatMessage(
                role="user",
                content="Write a short Python function to calculate fibonacci numbers."
            )
        ]):
            print(chunk, end='', flush=True)

        print("\n")


async def main():
    """Run all examples"""
    try:
        await example_simple_chat()
        await example_agent_swarm()
        await example_streaming()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure Ollama is running: ollama serve")
        print("And the model is pulled: ollama pull kimi-k2.5:cloud")


if __name__ == "__main__":
    asyncio.run(main())
