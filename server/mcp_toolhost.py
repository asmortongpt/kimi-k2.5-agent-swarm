from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Any, Dict, List

from auth import require_auth

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
            "description": "Read a file (restricted to allowed directories)",
            "inputSchema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"]
            }
        },
        {
            "name": "fs.write",
            "description": "Write a file (restricted to allowed directories)",
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
async def call_tool(req: ToolCall, _user=Depends(require_auth)):
    name = req.toolName
    payload = req.input

    if name == "kimi.chat":
        from server.services.kimi_client_production import ProductionKimiClient, ChatMessage, KimiProvider
        async with ProductionKimiClient(provider=KimiProvider.OLLAMA) as client:
            response = await client.chat([
                ChatMessage(role=msg["role"], content=msg["content"])
                for msg in payload["messages"]
            ])
            return {"content": response, "model": "kimi-k2.5:cloud"}

    if name == "kimi.swarm_review":
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

    # exec.shell and exec.python REMOVED from API for security
    # Code execution should only be done from trusted internal contexts

    if name == "rag.search":
        return {"result": "RAG search not yet implemented"}

    if name == "image.generate":
        return {"result": "Image generation not yet implemented"}

    raise HTTPException(status_code=404, detail=f"Unknown tool: {name}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
