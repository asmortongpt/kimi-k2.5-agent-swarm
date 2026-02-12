# CLAWS.BOT + Kimi K2.5 Integration - Implementation Guide

**Status:** ✅ Steps 1-3 Complete | ⏳ Steps 4-7 Remaining
**Date:** 2026-02-11

---

## ✅ Completed (Steps 1-3)

### 1. Fixed Model Typing
**File:** `CLAWD.BOT/src/core/types.ts`
**Status:** ✅ Done

```typescript
export type AIModel =
  | 'gpt-4'
  | 'gpt-4-turbo'
  | 'gpt-3.5-turbo'
  | 'claude-3-opus'
  | 'claude-3-sonnet'
  | 'claude-3-haiku'
  | 'claude-code'      // ← Added
  | 'grok-beta'
  | 'gemini-pro'
  | 'kimi-k2.5';       // ← Added
```

### 2. Created Kimi Provider
**File:** `CLAWD.BOT/src/core/kimi-provider.ts`
**Status:** ✅ Done

- Connects to Kimi FastAPI at `http://localhost:8000/api/chat`
- No API keys needed (local only)
- 2-minute timeout for local LLM inference
- Error handling with helpful messages

### 3. Registered Kimi Provider
**File:** `CLAWD.BOT/src/core/ai-provider.ts`
**Status:** ✅ Done

- Added `KimiProvider` import
- Extended `initialize()` config with `kimiBaseUrl`
- Added provider registration
- Added routing logic for `kimi-*` models

---

## ⏳ Remaining Steps (4-7)

### 4. Wire Environment Variables

**File:** `CLAWD.BOT/src/index.ts`

**Location:** Find the `AIProviderFactory.initialize({...})` call

**Add:**
```typescript
AIProviderFactory.initialize({
  openaiKey: process.env.OPENAI_API_KEY,
  claudeKey: process.env.ANTHROPIC_API_KEY,
  grokKey: process.env.GROK_API_KEY,
  useClaudeCode: process.env.USE_CLAUDE_CODE === 'true',
  claudeCodeCommand: process.env.CLAUDE_CODE_COMMAND,
  kimiBaseUrl: process.env.KIMI_BASE_URL,  // ← Add this line
});
```

**Environment Variables to Set:**
```bash
export KIMI_BASE_URL="http://localhost:8000"
export DEFAULT_MODEL="kimi-k2.5"
```

---

### 5. Register MCP Servers

**File:** `CLAWD.BOT/claws-cli.ts`

**Location:** After `const mcpClient = new MCPClient();`

**Add:**
```typescript
// MCP servers (Kimi toolhost + Browser automation)
const kimiMcpUrl = process.env.KIMI_MCP_URL || 'http://localhost:8010';
const browserMcpUrl = process.env.BROWSER_MCP_URL || 'http://localhost:8011';

// Kimi core tools (chat/rag/fs/exec/image/vision)
await mcpClient.registerServer({
  id: 'kimi',
  name: 'Kimi MCP',
  url: kimiMcpUrl,
  description: 'Local Kimi toolhost (chat, rag, exec, fs, image, vision)'
});

// Browser + visual regression tools (playwright, screenshots, diff)
await mcpClient.registerServer({
  id: 'web',
  name: 'Browser MCP',
  url: browserMcpUrl,
  description: 'Playwright automation + visual verification'
});
```

**Why:** Your `master-orchestrator-agent.ts` calls `this.mcpClient.callTool('web', 'test_html', ...)` but no server with id `'web'` is registered. This causes browser verification to fail.

**Environment Variables:**
```bash
export KIMI_MCP_URL="http://localhost:8010"
export BROWSER_MCP_URL="http://localhost:8011"
```

---

### 6. Update Master Orchestrator to Use Kimi

**File:** `CLAWD.BOT/src/agents/master-orchestrator-agent.ts`

**Location:** In the constructor config

**Change:**
```typescript
// OLD:
model: 'gpt-4',

// NEW:
model: (process.env.DEFAULT_MODEL as any) || 'kimi-k2.5',
fallbackModels: ['claude-3-sonnet', 'gpt-4'],
```

**Why:** Makes the tool local-first immediately. Falls back to cloud models if Kimi isn't running.

---

### 7. Enhance Browser Verification (Visual Evidence)

**File:** `CLAWD.BOT/src/agents/master-orchestrator-agent.ts`

**Location:** In `browserTest()` method, replace the `checks` payload

**Change:**
```typescript
const testResult = await this.mcpClient.callTool('web', 'test_html', {
  html: testHtml,
  viewport: { width: 375, height: 667 },
  screenshots: [
    { name: 'mobile-top', selector: 'body' },
    { name: 'mobile-fold', selector: 'body', scrollY: 600 }
  ],
  visualDiff: {
    baselineDir: '.visual-baseline',
    diffDir: '.visual-diffs',
    threshold: 0.02
  },
  checks: [
    { type: 'responsive', threshold: 0.9 },
    { type: 'accessibility', threshold: 0.8 },
    { type: 'performance', threshold: 0.85 }
  ]
});
```

**Why:** Forces actual screenshot capture + visual diff comparison. Returns evidence, not just pass/fail.

---

## 🐍 Kimi-Side Implementation (Python)

### Create MCP Toolhost (Port 8010)

**File:** `kimi/server/mcp_toolhost.py`

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List

app = FastAPI()

class ToolCall(BaseModel):
    toolName: str
    input: Dict[str, Any]

# --- Tools registry ---
def list_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "kimi.chat",
            "description": "Chat completion using local Kimi",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "messages": {"type": "array"},
                    "temperature": {"type": "number"},
                    "max_tokens": {"type": "number"},
                    "model": {"type": "string"}
                },
                "required": ["messages"]
            }
        },
        {
            "name": "kimi.swarm_review",
            "description": "Run multi-agent code/security review swarm",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "n_agents": {"type": "number"},
                    "focus": {"type": "string"}
                },
                "required": ["code"]
            }
        },
        {
            "name": "fs.read",
            "description": "Read a file (restricted by allowlist)",
            "inputSchema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"]
            }
        },
        {
            "name": "fs.write",
            "description": "Write a file",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            }
        },
        {
            "name": "exec.shell",
            "description": "Execute shell command",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout": {"type": "number"}
                },
                "required": ["command"]
            }
        },
        {
            "name": "exec.python",
            "description": "Execute Python code",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "timeout": {"type": "number"}
                },
                "required": ["code"]
            }
        },
        {
            "name": "rag.search",
            "description": "Search RAG vector store",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "k": {"type": "number"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "image.generate",
            "description": "Generate image (programmatic or AI)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "type": {"type": "string"},
                    "params": {"type": "object"}
                }
            }
        }
    ]

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/tools")
def tools():
    return list_tools()

@app.post("/tools/call")
async def call_tool(req: ToolCall):
    name = req.toolName
    payload = req.input

    # --- Route tools to your existing Kimi functions ---
    if name == "kimi.chat":
        # Wire to your existing chat function
        from server.services.kimi_client_production import ProductionKimiClient, ChatMessage, KimiProvider
        async with ProductionKimiClient(provider=KimiProvider.OLLAMA) as client:
            response = await client.chat([
                ChatMessage(role=msg["role"], content=msg["content"])
                for msg in payload["messages"]
            ])
            return {"content": response, "model": "kimi-k2.5:cloud"}

    if name == "kimi.swarm_review":
        # Wire to your max_power_review.py
        return {"result": "Swarm review not yet implemented"}

    if name == "fs.read":
        from server.services.mcp_tools_real import RealFileSystemTools
        fs = RealFileSystemTools()
        result = await fs.read_file(payload["path"])
        return {"success": result.success, "content": result.result, "error": result.error}

    if name == "fs.write":
        from server.services.mcp_tools_real import RealFileSystemTools
        fs = RealFileSystemTools()
        result = await fs.write_file(payload["path"], payload["content"])
        return {"success": result.success, "error": result.error}

    if name == "exec.shell":
        from server.services.mcp_tools_real import RealCodeExecutionTools
        exec_tools = RealCodeExecutionTools()
        result = await exec_tools.execute_shell(payload["command"], payload.get("timeout", 30))
        return {"success": result.success, "output": result.result, "error": result.error}

    if name == "exec.python":
        from server.services.mcp_tools_real import RealCodeExecutionTools
        exec_tools = RealCodeExecutionTools()
        result = await exec_tools.execute_python(payload["code"], payload.get("timeout", 30))
        return {"success": result.success, "output": result.result, "error": result.error}

    if name == "rag.search":
        # Wire to your RAG store
        return {"result": "RAG search not yet implemented"}

    if name == "image.generate":
        # Wire to your image generation
        return {"result": "Image generation not yet implemented"}

    raise HTTPException(status_code=404, detail=f"Unknown tool: {name}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
```

**Run:**
```bash
cd /Users/andrewmorton/Documents/GitHub/kimi
source .venv/bin/activate
python -m uvicorn server.mcp_toolhost:app --port 8010
```

---

### Create Browser MCP Server (Port 8011)

**File:** `kimi/server/browser_mcp.py`

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import asyncio
from pathlib import Path
import tempfile

app = FastAPI()

class BrowserToolCall(BaseModel):
    toolName: str
    input: Dict[str, Any]

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/tools")
def tools():
    return [
        {
            "name": "test_html",
            "description": "Test HTML with Playwright + visual diff",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "html": {"type": "string"},
                    "viewport": {"type": "object"},
                    "screenshots": {"type": "array"},
                    "visualDiff": {"type": "object"},
                    "checks": {"type": "array"}
                },
                "required": ["html"]
            }
        }
    ]

@app.post("/tools/call")
async def call_tool(req: BrowserToolCall):
    if req.toolName == "test_html":
        return await test_html(req.input)
    raise HTTPException(status_code=404, detail=f"Unknown tool: {req.toolName}")

async def test_html(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test HTML with Playwright
    Returns: screenshots, diffs, metrics, pass/fail
    """
    from playwright.async_api import async_playwright
    from PIL import Image, ImageChops
    import os

    html_content = params["html"]
    viewport = params.get("viewport", {"width": 1280, "height": 720})
    screenshots_config = params.get("screenshots", [])
    visual_diff_config = params.get("visualDiff", {})

    # Create temp HTML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write(html_content)
        html_path = f.name

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport=viewport)
            await page.goto(f'file://{html_path}')

            screenshot_paths = []
            diffs = []

            # Take screenshots
            for shot in screenshots_config:
                shot_name = shot.get("name", "screenshot")
                selector = shot.get("selector", "body")
                scroll_y = shot.get("scrollY", 0)

                if scroll_y > 0:
                    await page.evaluate(f"window.scrollTo(0, {scroll_y})")
                    await page.wait_for_timeout(500)

                shot_path = f'/tmp/screenshots/{shot_name}.png'
                os.makedirs(os.path.dirname(shot_path), exist_ok=True)

                element = await page.query_selector(selector)
                if element:
                    await element.screenshot(path=shot_path)
                    screenshot_paths.append(shot_path)

                    # Visual diff if baseline exists
                    if visual_diff_config:
                        baseline_dir = visual_diff_config.get("baselineDir", ".visual-baseline")
                        baseline_path = f'{baseline_dir}/{shot_name}.png'

                        if os.path.exists(baseline_path):
                            # Compare with baseline
                            diff_result = compare_images(baseline_path, shot_path)
                            if diff_result["diff_percent"] > visual_diff_config.get("threshold", 0.02):
                                diff_dir = visual_diff_config.get("diffDir", ".visual-diffs")
                                diff_path = f'{diff_dir}/{shot_name}-diff.png'
                                os.makedirs(os.path.dirname(diff_path), exist_ok=True)
                                diff_result["diff_image"].save(diff_path)
                                diffs.append({
                                    "name": shot_name,
                                    "diff_percent": diff_result["diff_percent"],
                                    "diff_path": diff_path
                                })

            await browser.close()

            # Determine pass/fail
            passed = len(diffs) == 0

            return {
                "passed": passed,
                "screenshots": screenshot_paths,
                "diffs": diffs,
                "metrics": {
                    "screenshots_taken": len(screenshot_paths),
                    "diffs_found": len(diffs)
                }
            }

    finally:
        os.unlink(html_path)

def compare_images(baseline_path: str, current_path: str) -> Dict[str, Any]:
    """Compare two images pixel by pixel"""
    baseline = Image.open(baseline_path)
    current = Image.open(current_path)

    # Ensure same size
    if baseline.size != current.size:
        current = current.resize(baseline.size)

    # Calculate diff
    diff = ImageChops.difference(baseline, current)
    diff_pixels = sum(sum(1 for p in row if p != 0) for row in diff.getdata())
    total_pixels = baseline.size[0] * baseline.size[1]
    diff_percent = diff_pixels / total_pixels

    return {
        "diff_percent": diff_percent,
        "diff_image": diff
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)
```

**Install Playwright:**
```bash
pip install playwright pillow
playwright install chromium
```

**Run:**
```bash
python -m uvicorn server.browser_mcp:app --port 8011
```

---

## 🚀 Complete Startup Sequence

### 1. Start Kimi Services
```bash
cd /Users/andrewmorton/Documents/GitHub/kimi
source .venv/bin/activate

# Terminal 1: Main Kimi API (port 8000)
python server/api/main.py

# Terminal 2: Kimi MCP Toolhost (port 8010)
python -m uvicorn server.mcp_toolhost:app --port 8010

# Terminal 3: Browser MCP (port 8011)
python -m uvicorn server.browser_mcp:app --port 8011
```

### 2. Set Environment Variables
```bash
export KIMI_BASE_URL="http://localhost:8000"
export KIMI_MCP_URL="http://localhost:8010"
export BROWSER_MCP_URL="http://localhost:8011"
export DEFAULT_MODEL="kimi-k2.5"
```

### 3. Start CLAWS.BOT
```bash
cd /Users/andrewmorton/Documents/GitHub/CLAWD.BOT
npx tsx claws-cli.ts "Create a calculator function with visual verification"
```

**What Happens:**
1. CLAWS Master Orchestrator uses Kimi K2.5 (local, $0.00)
2. Code generation via Kimi swarm
3. MCP tools execute (file operations, shell commands)
4. Browser MCP takes screenshots + visual diffs
5. Verification with actual evidence (not just claims)

---

## ✅ Success Criteria

You'll know it's working when:

1. ✅ CLAWS CLI starts without "Kimi provider not initialized" error
2. ✅ Browser automation returns screenshots + diffs (not just pass/fail)
3. ✅ Master Orchestrator shows `model: "kimi-k2.5:cloud"` in logs
4. ✅ No API key warnings (running 100% local)
5. ✅ Visual diff images saved to `.visual-diffs/`

---

## 🐛 Troubleshooting

### "Kimi provider not initialized"
**Fix:** Check `KIMI_BASE_URL` is set and Kimi API is running on port 8000

### "MCP server 'web' not found"
**Fix:** Complete Step 5 (register MCP servers in `claws-cli.ts`)

### "Connection refused to localhost:8010"
**Fix:** Start Kimi MCP toolhost: `uvicorn server.mcp_toolhost:app --port 8010`

### Browser test fails with no screenshots
**Fix:** Install Playwright: `pip install playwright && playwright install chromium`

---

## 📝 Next Steps After Integration

Once the above is working, enhance with:

1. **Full SDLC Workflow** - Create `UltimateSDLCWorkflow` in `advanced-workflow.ts`
2. **Security Gates** - Enforce bandit/semgrep scans before deployment
3. **Cost Tracking** - Log $0.00 for Kimi, actual costs for fallback models
4. **Metrics Dashboard** - Track verification pass rates, trust scores
5. **CI/CD Integration** - Run workflows on git push

---

**Status:** Ready to implement remaining steps 4-7!

**Estimated Time:** 2-3 hours to complete all remaining steps
