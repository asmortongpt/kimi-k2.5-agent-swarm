#!/usr/bin/env python3
"""
Kimi K2.5 API Client with Agent Swarm Support
Supports: Moonshot AI API, Ollama, Together AI
"""

import os
import json
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import httpx
from dotenv import load_dotenv

load_dotenv()


class ProviderType(Enum):
    MOONSHOT = "moonshot"
    OLLAMA = "ollama"
    TOGETHER = "together"


@dataclass
class AgentSwarmConfig:
    max_agents: int = 100
    parallel_execution: bool = True
    timeout: int = 300
    enable_thinking_mode: bool = True


class KimiClient:
    """Kimi K2.5 Client with Agent Swarm capabilities"""

    def __init__(
        self,
        provider: ProviderType = ProviderType.OLLAMA,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "kimi-k2.5",
        swarm_config: Optional[AgentSwarmConfig] = None
    ):
        self.provider = provider
        self.model = model
        self.swarm_config = swarm_config or AgentSwarmConfig()

        # Configure based on provider
        if provider == ProviderType.MOONSHOT:
            self.api_key = api_key or os.getenv("MOONSHOT_API_KEY")
            self.base_url = base_url or os.getenv("MOONSHOT_API_BASE", "https://api.moonshot.cn/v1")
        elif provider == ProviderType.OLLAMA:
            self.api_key = None
            self.base_url = base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")
            self.model = os.getenv("OLLAMA_MODEL", "kimi-k2.5:cloud")
        elif provider == ProviderType.TOGETHER:
            self.api_key = api_key or os.getenv("TOGETHER_API_KEY")
            self.base_url = "https://api.together.xyz/v1"

        self.client = httpx.AsyncClient(timeout=self.swarm_config.timeout)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        enable_swarm: bool = True
    ) -> Dict[str, Any]:
        """
        Send chat request to Kimi K2.5

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            stream: Enable streaming response
            enable_swarm: Enable agent swarm for complex tasks
        """
        if self.provider == ProviderType.OLLAMA:
            return await self._chat_ollama(messages, temperature, max_tokens, stream)
        else:
            return await self._chat_openai_compatible(
                messages, temperature, max_tokens, stream, enable_swarm
            )

    async def _chat_ollama(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        stream: bool
    ) -> Dict[str, Any]:
        """Chat using Ollama API"""
        url = f"{self.base_url}/api/chat"

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    async def _chat_openai_compatible(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        stream: bool,
        enable_swarm: bool
    ) -> Dict[str, Any]:
        """Chat using OpenAI-compatible API (Moonshot, Together)"""
        url = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }

        # Add agent swarm configuration if enabled
        if enable_swarm:
            payload["agent_swarm"] = {
                "enabled": True,
                "max_agents": self.swarm_config.max_agents,
                "parallel_execution": self.swarm_config.parallel_execution
            }

        response = await self.client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()

    async def agent_swarm_task(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        max_agents: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a complex task using agent swarm

        Args:
            task: Complex task description
            context: Additional context for the task
            max_agents: Maximum number of agents to spawn

        Returns:
            Dict with task results and agent execution details
        """
        system_message = {
            "role": "system",
            "content": f"""You are Kimi K2.5 with agent swarm capabilities.

For this task, you should:
1. Analyze the complexity and break it into parallelizable subtasks
2. Spawn specialized agents for each subtask
3. Coordinate their execution
4. Synthesize results into a comprehensive response

Max agents: {max_agents or self.swarm_config.max_agents}
Parallel execution: {self.swarm_config.parallel_execution}
"""
        }

        user_message = {
            "role": "user",
            "content": task
        }

        if context:
            user_message["content"] += f"\n\nContext: {json.dumps(context, indent=2)}"

        messages = [system_message, user_message]

        return await self.chat(
            messages=messages,
            enable_swarm=True,
            max_tokens=8192
        )

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Example usage
async def main():
    """Example usage of Kimi K2.5 client"""

    # Example 1: Simple chat with Ollama
    print("=" * 80)
    print("Example 1: Simple Chat (Ollama)")
    print("=" * 80)

    async with KimiClient(provider=ProviderType.OLLAMA) as client:
        response = await client.chat([
            {"role": "user", "content": "Explain quantum computing in simple terms"}
        ])
        print(f"Response: {response.get('message', {}).get('content', response)}\n")

    # Example 2: Agent Swarm for complex research
    print("=" * 80)
    print("Example 2: Agent Swarm - Multi-Domain Research")
    print("=" * 80)

    async with KimiClient(provider=ProviderType.OLLAMA) as client:
        response = await client.agent_swarm_task(
            task="""Research the following topics and provide a comprehensive analysis:
            1. Current state of quantum computing hardware
            2. Threats to existing cryptographic systems
            3. Post-quantum cryptography solutions
            4. Timeline for industry adoption

            For each topic, provide technical details, challenges, and future outlook.""",
            context={
                "depth": "technical",
                "target_audience": "security professionals"
            }
        )
        print(f"Swarm Response: {response}\n")

    # Example 3: Code analysis with agent swarm
    print("=" * 80)
    print("Example 3: Agent Swarm - Code Analysis")
    print("=" * 80)

    async with KimiClient(provider=ProviderType.OLLAMA) as client:
        code_sample = """
        def process_user_data(user_input):
            query = f"SELECT * FROM users WHERE username = '{user_input}'"
            return execute_query(query)
        """

        response = await client.agent_swarm_task(
            task=f"""Analyze this code for:
            1. Security vulnerabilities
            2. Performance issues
            3. Best practice violations
            4. Suggested improvements

            Code:
            {code_sample}
            """,
            max_agents=10
        )
        print(f"Analysis: {response}\n")


if __name__ == "__main__":
    asyncio.run(main())
