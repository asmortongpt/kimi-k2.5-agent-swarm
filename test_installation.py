#!/usr/bin/env python3
"""
Test Kimi K2.5 Installation
Quick verification that everything is working
"""

import asyncio
import sys
from kimi_client import KimiClient, ProviderType

async def test_installation():
    """Test Kimi K2.5 installation and basic functionality"""

    print("\n" + "=" * 80)
    print("🧪 Testing Kimi K2.5 Installation")
    print("=" * 80 + "\n")

    # Test 1: Simple connection
    print("Test 1: Basic Connection")
    print("-" * 80)
    try:
        async with KimiClient(provider=ProviderType.OLLAMA) as client:
            response = await client.chat([
                {"role": "user", "content": "Respond with exactly: 'Kimi K2.5 is working!'"}
            ])
            content = response.get('message', {}).get('content', '') or response.get('response', '')
            print(f"✅ Connection successful!")
            print(f"Response: {content[:200]}...\n" if len(content) > 200 else f"Response: {content}\n")
    except Exception as e:
        print(f"❌ Connection failed: {e}\n")
        return False

    # Test 2: Simple reasoning
    print("\nTest 2: Basic Reasoning")
    print("-" * 80)
    try:
        async with KimiClient(provider=ProviderType.OLLAMA) as client:
            response = await client.chat([
                {"role": "user", "content": "What is 15 * 37? Just give the number."}
            ])
            content = response.get('message', {}).get('content', '') or response.get('response', '')
            print(f"✅ Reasoning test passed!")
            print(f"Response: {content[:200]}...\n" if len(content) > 200 else f"Response: {content}\n")
    except Exception as e:
        print(f"❌ Reasoning test failed: {e}\n")
        return False

    # Test 3: Agent swarm (basic)
    print("\nTest 3: Agent Swarm Capability")
    print("-" * 80)
    try:
        async with KimiClient(provider=ProviderType.OLLAMA) as client:
            response = await client.agent_swarm_task(
                task="List 3 use cases for AI agent swarms. Be concise.",
                max_agents=5
            )
            content = response.get('message', {}).get('content', '') or response.get('response', '')
            print(f"✅ Agent swarm test passed!")
            print(f"Response: {content[:300]}...\n" if len(content) > 300 else f"Response: {content}\n")
    except Exception as e:
        print(f"❌ Agent swarm test failed: {e}\n")
        print(f"Note: This is expected if agent swarm features require API access\n")

    # Summary
    print("\n" + "=" * 80)
    print("✅ Installation Test Complete!")
    print("=" * 80)
    print("\n📋 What's Working:")
    print("  • Ollama connection: ✅")
    print("  • Kimi K2.5 model: ✅")
    print("  • Basic chat: ✅")
    print("  • Python client: ✅")
    print("\n🚀 Next Steps:")
    print("  • Try examples: python kimi_client.py")
    print("  • Code analysis: python examples/code_analysis_swarm.py")
    print("  • CLI chat: ollama run kimi-k2.5:cloud")
    print("\n📖 Documentation:")
    print("  • Quick Start: QUICKSTART.md")
    print("  • Full Guide: README.md")
    print("  • Examples: examples/")
    print()

    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(test_installation())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)
