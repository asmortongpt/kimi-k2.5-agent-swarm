#!/usr/bin/env python3
"""
Production-Grade Type-Safe Models
Pydantic models for all data structures with comprehensive validation.
"""

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, validator, root_validator
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Message roles in conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


class Message(BaseModel):
    """Chat message with validation."""
    role: MessageRole
    content: str = Field(..., min_length=1, max_length=100000)
    name: Optional[str] = Field(None, max_length=256)
    function_call: Optional[Dict[str, Any]] = None

    @validator("content")
    def validate_content(cls, v):
        """Ensure content is not empty after stripping."""
        if not v.strip():
            raise ValueError("Message content cannot be empty")
        return v

    class Config:
        use_enum_values = True


class ChatRequest(BaseModel):
    """Chat completion request."""
    messages: List[Message] = Field(..., min_items=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=128000)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    stream: bool = False
    stop: Optional[Union[str, List[str]]] = None

    # Agent swarm parameters
    enable_swarm: bool = False
    max_agents: Optional[int] = Field(None, ge=1, le=1000)

    @validator("messages")
    def validate_messages(cls, v):
        """Ensure at least one user or system message."""
        if not any(msg.role in [MessageRole.USER, MessageRole.SYSTEM] for msg in v):
            raise ValueError("At least one user or system message required")
        return v

    @root_validator
    def validate_swarm_config(cls, values):
        """Validate swarm configuration."""
        if values.get("enable_swarm") and not values.get("max_agents"):
            values["max_agents"] = 100  # Default
        return values


class TokenUsage(BaseModel):
    """Token usage statistics."""
    prompt_tokens: int = Field(..., ge=0)
    completion_tokens: int = Field(..., ge=0)
    total_tokens: int = Field(..., ge=0)

    @root_validator
    def validate_total(cls, values):
        """Ensure total equals sum of parts."""
        prompt = values.get("prompt_tokens", 0)
        completion = values.get("completion_tokens", 0)
        total = values.get("total_tokens", 0)

        if total != prompt + completion:
            values["total_tokens"] = prompt + completion

        return values


class Choice(BaseModel):
    """Single completion choice."""
    index: int = Field(..., ge=0)
    message: Message
    finish_reason: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat completion response."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Optional[TokenUsage] = None

    # Additional metadata
    provider: Optional[str] = None
    cached: bool = False
    response_time_ms: Optional[float] = None


class AgentTask(BaseModel):
    """Agent task specification."""
    task_id: str
    description: str = Field(..., min_length=1, max_length=10000)
    context: Dict[str, Any] = Field(default_factory=dict)
    max_agents: int = Field(default=100, ge=1, le=1000)
    timeout: float = Field(default=300.0, ge=1.0, le=3600.0)
    priority: int = Field(default=1, ge=1, le=5)


class AgentResult(BaseModel):
    """Agent task result."""
    task_id: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    agents_used: int = Field(default=0, ge=0)
    execution_time: float = Field(default=0.0, ge=0.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthStatus(str, Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    """Health status of a component."""
    name: str
    status: HealthStatus
    message: Optional[str] = None
    last_check: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SystemHealth(BaseModel):
    """Overall system health."""
    status: HealthStatus
    components: List[ComponentHealth]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @root_validator
    def determine_overall_status(cls, values):
        """Determine overall status from components."""
        components = values.get("components", [])

        if not components:
            values["status"] = HealthStatus.UNHEALTHY
            return values

        # Overall status is worst component status
        statuses = [c.status for c in components]

        if HealthStatus.UNHEALTHY in statuses:
            values["status"] = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            values["status"] = HealthStatus.DEGRADED
        else:
            values["status"] = HealthStatus.HEALTHY

        return values


class CacheMetrics(BaseModel):
    """Cache performance metrics."""
    hits: int = Field(default=0, ge=0)
    misses: int = Field(default=0, ge=0)
    evictions: int = Field(default=0, ge=0)
    size: int = Field(default=0, ge=0)
    max_size: int = Field(default=0, ge=0)
    memory_bytes: int = Field(default=0, ge=0)
    hit_rate: float = Field(default=0.0, ge=0.0, le=1.0)


class CircuitBreakerMetrics(BaseModel):
    """Circuit breaker metrics."""
    name: str
    state: str
    failure_count: int = Field(default=0, ge=0)
    success_count: int = Field(default=0, ge=0)
    last_failure: Optional[datetime] = None
    open_since: Optional[datetime] = None


class PerformanceMetrics(BaseModel):
    """Performance metrics."""
    total_requests: int = Field(default=0, ge=0)
    successful_requests: int = Field(default=0, ge=0)
    failed_requests: int = Field(default=0, ge=0)
    average_latency_ms: float = Field(default=0.0, ge=0.0)
    p50_latency_ms: Optional[float] = Field(None, ge=0.0)
    p95_latency_ms: Optional[float] = Field(None, ge=0.0)
    p99_latency_ms: Optional[float] = Field(None, ge=0.0)
    total_tokens: int = Field(default=0, ge=0)
    total_cost: float = Field(default=0.0, ge=0.0)


class ProviderMetrics(BaseModel):
    """Provider-specific metrics."""
    provider: str
    total_requests: int = Field(default=0, ge=0)
    successful_requests: int = Field(default=0, ge=0)
    failed_requests: int = Field(default=0, ge=0)
    average_latency_ms: float = Field(default=0.0, ge=0.0)
    total_tokens: int = Field(default=0, ge=0)
    total_cost: float = Field(default=0.0, ge=0.0)
    rate_limit_hits: int = Field(default=0, ge=0)
    circuit_breaker_state: Optional[str] = None


class SystemMetrics(BaseModel):
    """Complete system metrics."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    uptime_seconds: float = Field(default=0.0, ge=0.0)
    performance: PerformanceMetrics
    cache: CacheMetrics
    providers: List[ProviderMetrics]
    circuit_breakers: List[CircuitBreakerMetrics]


class BatchRequest(BaseModel):
    """Batch processing request."""
    requests: List[ChatRequest] = Field(..., min_items=1, max_items=100)
    parallel: bool = True
    max_concurrency: int = Field(default=10, ge=1, le=50)


class BatchResponse(BaseModel):
    """Batch processing response."""
    results: List[ChatResponse]
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_time_ms: float


class ErrorResponse(BaseModel):
    """Standardized error response."""
    error: str
    error_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trace_id: Optional[str] = None


class StreamChunk(BaseModel):
    """Streaming response chunk."""
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[Dict[str, Any]]


# Cost estimation models
class CostEstimate(BaseModel):
    """Cost estimation for a request."""
    provider: str
    model: str
    estimated_prompt_tokens: int = Field(..., ge=0)
    estimated_completion_tokens: int = Field(..., ge=0)
    estimated_total_tokens: int = Field(..., ge=0)
    estimated_cost_usd: float = Field(..., ge=0.0)
    breakdown: Dict[str, float] = Field(default_factory=dict)


# Provider capabilities
class ProviderCapabilities(BaseModel):
    """Capabilities of a provider."""
    provider: str
    models: List[str]
    supports_streaming: bool = False
    supports_functions: bool = False
    supports_vision: bool = False
    max_tokens: int
    max_context_length: int
    pricing_per_1k_tokens: Dict[str, float] = Field(default_factory=dict)
