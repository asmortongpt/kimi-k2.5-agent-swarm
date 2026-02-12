# Kimi K2.5 Quick Start Guide

Get up and running with Kimi K2.5 in under 5 minutes!

## Prerequisites

- **Ollama installed**: ✅ Already installed at `/opt/homebrew/bin/ollama`
- **Kimi K2.5 model**: ✅ Already downloaded (`kimi-k2.5:cloud`)
- **Python 3.8+** or **Node.js 18+**

## Option 1: Quick Test with Ollama CLI (Fastest!)

```bash
# Start chatting immediately
ollama run kimi-k2.5:cloud

# Try these prompts:
# 1. "Explain agent swarms in AI"
# 2. "Analyze this code for security issues: [paste code]"
# 3. "Break down this complex task into parallel subtasks: [describe task]"
```

## Option 2: Python Client (Recommended)

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env if needed (optional for Ollama)
# OLLAMA_HOST=http://localhost:11434
# OLLAMA_MODEL=kimi-k2.5:cloud
```

### Run Examples

```bash
# Example 1: Simple chat
python kimi_client.py

# Example 2: Code analysis with agent swarm
python examples/code_analysis_swarm.py
```

### Quick Python Script

```python
import asyncio
from kimi_client import KimiClient, ProviderType

async def main():
    async with KimiClient(provider=ProviderType.OLLAMA) as client:
        response = await client.chat([
            {"role": "user", "content": "Explain quantum computing"}
        ])
        print(response)

asyncio.run(main())
```

## Option 3: TypeScript/Node.js Client

### Setup

```bash
# Install dependencies
npm install

# Build TypeScript
npm run build
```

### Run Examples

```bash
# Simple chat
npm run example:simple

# Agent swarm demo
npm run example:swarm

# Research swarm
npm run example:research
```

### Quick TypeScript Script

```typescript
import KimiClient, { ProviderType } from './kimi_client';

async function main() {
  const client = new KimiClient(ProviderType.OLLAMA);
  const response = await client.chat([
    { role: 'user', content: 'Explain quantum computing' }
  ]);
  console.log(response);
}

main();
```

## Agent Swarm Examples

### Example 1: Multi-Domain Research

```python
response = await client.agent_swarm_task(
    "Research quantum computing impact on cryptography. "
    "Deploy specialized agents for: hardware analysis, security threats, "
    "post-quantum solutions, and industry adoption."
)
```

### Example 2: Code Security Audit

```python
response = await client.agent_swarm_task(
    "Analyze this Flask app for security vulnerabilities. "
    "Deploy agents for: SQL injection detection, auth review, "
    "crypto analysis, and access control checks.",
    max_agents=20
)
```

### Example 3: System Architecture Design

```python
response = await client.agent_swarm_task(
    "Design a scalable microservices architecture for a fleet "
    "management system with 10K+ vehicles. Include: system design, "
    "database schema, API specs, security architecture, and cost estimate.",
    context={"scale": "enterprise", "compliance": ["FedRAMP"]},
    max_agents=30
)
```

## Testing Your Setup

### Test Ollama Connection

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Test simple completion
curl http://localhost:11434/api/generate -d '{
  "model": "kimi-k2.5:cloud",
  "prompt": "Hello, what are you?",
  "stream": false
}'
```

### Test Python Client

```bash
# Quick test
python -c "
import asyncio
from kimi_client import KimiClient, ProviderType

async def test():
    client = KimiClient(ProviderType.OLLAMA)
    r = await client.chat([{'role': 'user', 'content': 'Hi!'}])
    print('✅ Connection successful!')
    print(r)
    await client.close()

asyncio.run(test())
"
```

### Test TypeScript Client

```bash
# Quick test
npx ts-node -e "
import KimiClient, { ProviderType } from './kimi_client';

(async () => {
  const client = new KimiClient(ProviderType.OLLAMA);
  const r = await client.chat([{role: 'user', content: 'Hi!'}]);
  console.log('✅ Connection successful!');
  console.log(r);
})();
"
```

## What Makes Kimi K2.5 Special?

1. **Native Agent Swarm**: Automatically spawns up to 100 specialized sub-agents
2. **Massive Scale**: 1.04T total parameters, 32B active per inference
3. **Multimodal**: Text + Vision capabilities
4. **Long Context**: 256K token context window
5. **Open Source**: MIT licensed, run locally or use API

## Next Steps

- Read full documentation: `README.md`
- Explore examples: `examples/`
- Join community: https://www.kimi.com
- API docs: https://platform.moonshot.ai

## Troubleshooting

### Ollama Not Running

```bash
# Start Ollama service
ollama serve

# Or use: brew services start ollama
```

### Model Not Found

```bash
# Re-download model
ollama pull kimi-k2.5:cloud

# List installed models
ollama list
```

### Python Dependencies

```bash
# Ensure you're using Python 3.8+
python --version

# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

### Node/TypeScript Issues

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Rebuild TypeScript
npm run build
```

## Performance Tips

1. **Use Agent Swarm for Complex Tasks**: Tasks with multiple domains benefit most
2. **Adjust max_agents**: More agents = more parallelism but more memory
3. **Enable Thinking Mode**: Better reasoning for complex problems
4. **Use Streaming**: For better user experience with long responses
5. **Context Management**: Keep context focused for better results

## Ready to Go! 🚀

You're all set up with Kimi K2.5! Start with:

```bash
# Try the CLI
ollama run kimi-k2.5:cloud

# Or run the Python examples
python kimi_client.py
```

Happy agent swarming! 🐝
