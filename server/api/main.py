#!/usr/bin/env python3
"""
Kimi K2.5 Agent Swarm - Production FastAPI Server
NO MOCKS - All endpoints use real implementations
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
import asyncio

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from auth import require_auth
from services.kimi_client_production import ProductionKimiClient, KimiProvider, ChatMessage, SwarmConfig
from services.rag_vector_store import ProductionRAGStore, Document, EmbeddingProvider
from services.mcp_tools_real import (
    RealFileSystemTools, RealDatabaseTools, RealWebSearchTools
)
from services.image_generation_real import RealImageGenerator, ImageGenerationBackend

logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Allowed CORS origins (configure via env var, comma-separated)
ALLOWED_ORIGINS = os.getenv(
    "KIMI_CORS_ORIGINS",
    "http://localhost:8000,http://localhost:3000"
).split(",")

# Create FastAPI app
app = FastAPI(
    title="Kimi K2.5 Agent Swarm API",
    description="Production-grade multi-agent AI system with real LLM, RAG, and MCP integrations",
    version="1.0.0",
    docs_url="/api/docs" if os.getenv("KIMI_ENABLE_DOCS", "false").lower() == "true" else None,
    redoc_url=None,
)

# Rate limiter middleware
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")


# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SlowAPIMiddleware)

# CORS middleware - restricted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# Global instances (initialized on startup)
kimi_client: Optional[ProductionKimiClient] = None
rag_store: Optional[ProductionRAGStore] = None
db_tools: Optional[RealDatabaseTools] = None
web_tools: Optional[RealWebSearchTools] = None
image_generator: Optional[RealImageGenerator] = None

# Mount static files (for web UI)
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# Pydantic models for API
class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=4096, ge=1, le=32000)
    stream: bool = False


class SwarmRequest(BaseModel):
    task: str = Field(..., max_length=10000)
    num_agents: Optional[int] = Field(default=None, ge=1, le=100)
    context: Optional[Dict[str, Any]] = None


class KnowledgeDocument(BaseModel):
    id: str = Field(..., max_length=500)
    content: str = Field(..., max_length=100000)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    query: str = Field(..., max_length=1000)
    k: int = Field(default=5, ge=1, le=50)
    filter_metadata: Optional[Dict[str, Any]] = None


class ToolExecutionRequest(BaseModel):
    tool_type: str = Field(..., pattern=r"^(filesystem|database|web_search|image_generation)$")
    tool_name: str = Field(..., max_length=100)
    parameters: Dict[str, Any]


class ImageGenerationRequest(BaseModel):
    prompt: Optional[str] = Field(default=None, max_length=2000)
    image_type: Literal["gradient", "pattern", "shapes", "text"] = "gradient"
    chart_type: Optional[Literal["line", "bar", "scatter", "pie"]] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    data: Optional[Dict[str, Any]] = None


def _safe_error_response(e: Exception, status_code: int = 500) -> HTTPException:
    """Return a sanitized error without leaking internals."""
    logger.exception("Request error")
    return HTTPException(status_code=status_code, detail="Internal server error")


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global kimi_client, rag_store, db_tools, web_tools, image_generator

    logger.info("Starting Kimi K2.5 Agent Swarm API...")

    # Initialize Kimi client
    kimi_client = ProductionKimiClient(
        provider=KimiProvider.OLLAMA,
        swarm_config=SwarmConfig(max_agents=100)
    )
    logger.info("Kimi client initialized")

    # Initialize RAG store (make optional for now)
    try:
        rag_store = ProductionRAGStore(
            collection_name="kimi_knowledge",
            embedding_provider=EmbeddingProvider.OLLAMA
        )
        await rag_store.connect()
        logger.info("RAG store initialized")
    except Exception as e:
        logger.warning("RAG store initialization skipped: %s", type(e).__name__)

    # Initialize tools
    try:
        db_tools = RealDatabaseTools()
        await db_tools.connect()
        logger.info("Database tools initialized")
    except Exception as e:
        logger.warning("Database tools initialization skipped: %s", type(e).__name__)

    web_tools = RealWebSearchTools()
    image_generator = RealImageGenerator()
    logger.info("MCP tools initialized")
    logger.info("Server ready on http://localhost:8000")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down...")

    if kimi_client:
        await kimi_client.close()
    if rag_store:
        await rag_store.close()
    if db_tools:
        await db_tools.close()
    if web_tools:
        await web_tools.close()

    logger.info("Shutdown complete")


# Health check endpoint (no auth required)
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "kimi_client": kimi_client is not None,
            "rag_store": rag_store is not None,
            "db_tools": db_tools is not None,
            "web_tools": web_tools is not None
        }
    }


# Chat endpoints
@app.post("/api/chat")
@limiter.limit("30/minute")
async def chat(request: Request, body: ChatRequest, _user=Depends(require_auth)):
    """Chat with Kimi K2.5 (REAL API call)"""
    try:
        messages = [
            ChatMessage(role=msg["role"], content=msg["content"])
            for msg in body.messages
        ]

        response = await kimi_client.chat(
            messages=messages,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            stream=False
        )

        return {
            "success": True,
            "response": response,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise _safe_error_response(e)


@app.post("/api/chat/stream")
@limiter.limit("30/minute")
async def chat_stream(request: Request, body: ChatRequest, _user=Depends(require_auth)):
    """Stream chat responses in real-time"""
    try:
        messages = [
            ChatMessage(role=msg["role"], content=msg["content"])
            for msg in body.messages
        ]

        async def generate():
            async for chunk in kimi_client.stream_chat(
                messages=messages,
                temperature=body.temperature,
                max_tokens=body.max_tokens
            ):
                yield f"data: {chunk}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    except Exception as e:
        raise _safe_error_response(e)


# Agent Swarm endpoints
@app.post("/api/swarm")
@limiter.limit("10/minute")
async def create_swarm(request: Request, body: SwarmRequest, _user=Depends(require_auth)):
    """Create and execute agent swarm (REAL multi-agent coordination)"""
    try:
        result = await kimi_client.spawn_agent_swarm(
            task=body.task,
            num_agents=body.num_agents,
            context=body.context
        )

        return {
            "success": True,
            "swarm_result": result,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise _safe_error_response(e)


# Knowledge base endpoints
@app.post("/api/knowledge")
@limiter.limit("20/minute")
async def add_knowledge(request: Request, documents: List[KnowledgeDocument], _user=Depends(require_auth)):
    """Add documents to knowledge base (REAL embeddings, REAL vector store)"""
    try:
        docs = [
            Document(
                id=doc.id,
                content=doc.content,
                metadata=doc.metadata
            )
            for doc in documents
        ]

        await rag_store.add_documents(docs, generate_embeddings=True)

        return {
            "success": True,
            "documents_added": len(docs),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise _safe_error_response(e)


@app.post("/api/knowledge/search")
@limiter.limit("60/minute")
async def search_knowledge(request: Request, body: SearchRequest, _user=Depends(require_auth)):
    """Search knowledge base (REAL vector similarity search)"""
    try:
        results = await rag_store.search(
            query=body.query,
            k=body.k,
            filter_metadata=body.filter_metadata
        )

        return {
            "success": True,
            "results": [
                {
                    "document": result.document.to_dict(),
                    "score": result.score,
                    "rank": result.rank
                }
                for result in results
            ],
            "count": len(results),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise _safe_error_response(e)


@app.get("/api/knowledge/stats")
@limiter.limit("60/minute")
async def knowledge_stats(request: Request, _user=Depends(require_auth)):
    """Get knowledge base statistics"""
    try:
        stats = await rag_store.get_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        raise _safe_error_response(e)


# Tool execution endpoints - code_execution REMOVED for security
@app.post("/api/tools/execute")
@limiter.limit("30/minute")
async def execute_tool(request: Request, body: ToolExecutionRequest, _user=Depends(require_auth)):
    """
    Execute MCP tool (file/db/web/image operations).
    NOTE: code_execution tools have been removed for security.
    """
    try:
        result = None

        if body.tool_type == "image_generation":
            if body.tool_name == "generate_programmatic":
                result = await image_generator.generate_programmatic(
                    body.parameters.get("image_type", "gradient"),
                    body.parameters.get("params", {})
                )
            elif body.tool_name == "generate_chart":
                result = await image_generator.generate_chart(
                    body.parameters.get("chart_type", "bar"),
                    body.parameters.get("data", {})
                )
            elif body.tool_name == "generate_from_text":
                result = await image_generator.generate_from_text(
                    body.parameters.get("prompt", ""),
                    width=body.parameters.get("width", 512),
                    height=body.parameters.get("height", 512)
                )

            if result:
                return {
                    "success": result.success,
                    "result": {
                        "image_path": result.image_path,
                        "image_base64": result.image_base64,
                        "generation_time_ms": result.generation_time_ms,
                        "metadata": result.metadata
                    },
                    "error": result.error,
                    "timestamp": datetime.utcnow().isoformat()
                }

        elif body.tool_type == "filesystem":
            fs = RealFileSystemTools()

            if body.tool_name == "read_file":
                result = await fs.read_file(body.parameters["path"])
            elif body.tool_name == "write_file":
                result = await fs.write_file(
                    body.parameters["path"],
                    body.parameters["content"]
                )
            elif body.tool_name == "list_directory":
                result = await fs.list_directory(body.parameters["path"])

        elif body.tool_type == "database":
            if body.tool_name == "get_schema":
                result = await db_tools.get_schema(
                    body.parameters.get("table_name")
                )
            # query_database removed - use get_schema only

        elif body.tool_type == "web_search":
            if body.tool_name == "search_web":
                result = await web_tools.search_web(
                    body.parameters["query"],
                    body.parameters.get("max_results", 5)
                )
            elif body.tool_name == "fetch_webpage":
                result = await web_tools.fetch_webpage(body.parameters["url"])

        if result is None:
            raise HTTPException(status_code=400, detail="Unknown or disallowed tool")

        return {
            "success": result.success,
            "result": result.result,
            "error": result.error,
            "execution_time_ms": result.execution_time_ms,
            "metadata": result.metadata,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise _safe_error_response(e)


# RAG-enhanced chat
@app.post("/api/rag-chat")
@limiter.limit("20/minute")
async def rag_enhanced_chat(request: Request, body: ChatRequest, _user=Depends(require_auth)):
    """Chat with RAG-enhanced context (REAL embeddings + REAL LLM)"""
    try:
        user_message = next(
            (msg["content"] for msg in body.messages if msg["role"] == "user"),
            None
        )

        if not user_message:
            raise HTTPException(status_code=400, detail="No user message found")

        search_results = await rag_store.search(user_message, k=3)

        context = "\n\n".join([
            f"[Source: {r.document.metadata.get('source', 'unknown')}]\n{r.document.content}"
            for r in search_results
        ])

        enhanced_messages = [
            ChatMessage(
                role="system",
                content=f"You are a helpful assistant with access to the following knowledge:\n\n{context}"
            )
        ] + [
            ChatMessage(role=msg["role"], content=msg["content"])
            for msg in body.messages
        ]

        response = await kimi_client.chat(
            messages=enhanced_messages,
            temperature=body.temperature,
            max_tokens=body.max_tokens
        )

        return {
            "success": True,
            "response": response,
            "retrieved_documents": len(search_results),
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise _safe_error_response(e)


# Image generation
@app.post("/api/image/generate")
@limiter.limit("10/minute")
async def generate_image(request: Request, body: ImageGenerationRequest, _user=Depends(require_auth)):
    """Generate images programmatically (REAL generation, no mocks)"""
    try:
        if body.prompt:
            result = await image_generator.generate_from_text(
                prompt=body.prompt,
                width=body.params.get("width", 512),
                height=body.params.get("height", 512),
                num_inference_steps=body.params.get("steps", 20)
            )
        elif body.chart_type:
            result = await image_generator.generate_chart(
                chart_type=body.chart_type,
                data=body.data or {}
            )
        else:
            result = await image_generator.generate_programmatic(
                image_type=body.image_type,
                params=body.params
            )

        if result.success:
            return {
                "success": True,
                "image_path": result.image_path,
                "image_base64": result.image_base64,
                "generation_time_ms": result.generation_time_ms,
                "metadata": result.metadata
            }
        else:
            raise HTTPException(status_code=500, detail="Image generation failed")

    except HTTPException:
        raise
    except Exception as e:
        raise _safe_error_response(e)


# Web UI endpoint (no auth - serves static HTML)
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the web chat UI"""
    html_path = Path(__file__).parent.parent / "static" / "index.html"
    if html_path.exists():
        with open(html_path, 'r') as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Kimi K2.5 API is running!</h1><p>Web UI not found. Check /api/health endpoint.</p>")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
