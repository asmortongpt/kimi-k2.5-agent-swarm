# Kimi K2.5 Setup - Visual Agentic Intelligence with Swarm Agents

## Overview

**Kimi K2.5** is an open-source multimodal AI model with native **Agent Swarm** capabilities:
- 1.04 trillion total parameters (32B active per inference)
- Mixture-of-Experts (MoE) architecture with 384 experts
- 256K token context window
- Self-directed agent swarm with up to 100 parallel sub-agents
- Released January 27, 2026 by Moonshot AI

## Agent Swarm Capabilities

Kimi K2.5 can dynamically create specialized sub-agents that work in parallel:
- Decomposes complex tasks into parallelizable subtasks
- Each agent can independently use tools (search, generate, analyze)
- Orchestrator coordinates distributed execution
- Examples: AI Researcher, Physics Researcher, Fact Checker, Code Analyzer

## Installation Options

### Option 1: API Access (Recommended - Easiest)

Access via Moonshot AI Platform with OpenAI/Anthropic-compatible API:

```bash
# Set your API key
export MOONSHOT_API_KEY="your-api-key-here"
```

API Endpoint: `https://platform.moonshot.ai`

### Option 2: Ollama (Local - Simple)

Best for local testing and development:

```bash
# Install Ollama (if not installed)
curl -fsSL https://ollama.com/install.sh | sh

# Pull Kimi K2.5
ollama pull kimi-k2.5

# Run the model
ollama run kimi-k2.5
```

### Option 3: vLLM (Local - Enterprise Hardware Required)

Requires 8x H100/H200/B200 GPUs for optimal performance:

```bash
# Install vLLM nightly build
pip install -U vllm --pre

# Start the server (requires 8 GPUs)
vllm serve moonshotai/Kimi-K2.5 -tp 8
```

### Option 4: Quantized Version (Lower Resources)

Requires 240GB total (disk + RAM + VRAM):

```bash
# Install dependencies
pip install -U huggingface_hub

# Download quantized model
huggingface-cli download unsloth/Kimi-K2.5-GGUF
```

## API Providers

Kimi K2.5 is also available on:
- **Moonshot AI Platform**: https://platform.moonshot.ai
- **Together AI**: https://www.together.ai/models/kimi-k2-5
- **NVIDIA NIM**: https://build.nvidia.com/moonshotai/kimi-k2.5
- **Hugging Face**: https://huggingface.co/moonshotai/Kimi-K2.5

## Agent Swarm Examples

### Example 1: Multi-Domain Research

```python
# The agent swarm automatically decomposes this into parallel tasks
response = await kimi.chat(
    "Research the impact of quantum computing on cryptography,
     including technical analysis, security implications,
     and industry adoption trends"
)
# Kimi creates: Quantum Researcher, Security Analyst, Industry Analyst
```

### Example 2: Complex Code Analysis

```python
response = await kimi.chat(
    "Analyze this codebase: review architecture,
     identify security vulnerabilities, suggest optimizations,
     and generate documentation"
)
# Kimi creates: Architect, Security Auditor, Performance Engineer, Doc Writer
```

## Environment Setup

See `.env.example` for configuration options.

## Hardware Requirements

- **API Access**: No special hardware needed
- **Ollama**: 16GB+ RAM recommended
- **Full Model**: 8x H100/H200 GPUs (enterprise-grade)
- **Quantized**: 240GB+ available memory (RAM + VRAM)

## Resources

- Official Site: https://www.kimi.com
- GitHub: https://github.com/MoonshotAI/Kimi-K2
- Hugging Face: https://huggingface.co/moonshotai/Kimi-K2.5
- Documentation: https://www.kimi.com/blog/kimi-k2-5.html
- DataCamp Guide: https://www.datacamp.com/tutorial/kimi-k2-agent-swarm-guide

## License

Modified MIT License
