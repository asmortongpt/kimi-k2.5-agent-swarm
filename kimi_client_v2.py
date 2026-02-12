#!/usr/bin/env python3
"""
Kimi K2.5 API Client - Production-Grade Version
Enterprise-ready client with comprehensive error handling, resilience patterns,
observability, caching, and performance optimization.

Key improvements over v1:
- Comprehensive exception handling with detailed error context
- Retry with exponential backoff and jitter
- Circuit breaker for failed providers
- Rate limiting with token bucket algorithm
- Multi-level caching with TTL
- Connection pooling for better performance
- Structured logging and metrics collection
- Type-safe models with Pydantic validation
- Health checks and monitoring
- Async batching for efficiency
- Cost tracking and estimation
"""

import asyncio
import time
from typing import Optional, List, Dict, Any, AsyncIterator
from datetime import datetime
import httpx

from core.exceptions import *
from core.resilience import (
    with_retry, with_circuit_breaker, with_rate_limit, with_timeout,
    RetryConfig, CircuitBreakerConfig, RateLimitConfig, resilient
)
from core.observability import (
    StructuredLogger, MetricsCollector, PerformanceMonitor, PerformanceStats
)
from core.caching import LRUCache, cached, cache_key
from core.config import (
    KimiConfig, ConfigManager, ProviderType, get_config
)
from core.models import (
    ChatRequest, ChatResponse, Message, MessageRole, TokenUsage,
    Choice, AgentTask, AgentResult, SystemHealth, ComponentHealth, HealthStatus,
    SystemMetrics, PerformanceMetrics, CacheMetrics, ProviderMetrics,
    BatchRequest, BatchResponse
)


class KimiClientV2:
    """
    Production-grade Kimi K2.5 client with comprehensive error handling,
    resilience patterns, and observability.

    Features:
    - Automatic retry with exponential backoff
    - Circuit breaker for failing providers
    - Rate limiting to prevent quota exhaustion
    - Multi-level caching for performance
    - Connection pooling for efficiency
    - Structured logging and metrics
    - Cost tracking and optimization
    - Health monitoring
    - Async batch processing
    """

    def __init__(
        self,
        provider: Optional[ProviderType] = None,
        config: Optional[KimiConfig] = None,
        enable_cache: bool = True,
        enable_metrics: bool = True
    ):
        """
        Initialize production-grade Kimi client.

        Args:
            provider: AI provider to use (defaults to config default)
            config: Configuration instance (loads from env if None)
            enable_cache: Enable response caching
            enable_metrics: Enable metrics collection
        """
        self.config = config or get_config()
        self.provider = provider or self.config.default_provider
        self.provider_config = self.config.get_provider_config(self.provider)

        # Observability
        self.logger = StructuredLogger(f"kimi.{self.provider.value}")
        self.metrics = MetricsCollector() if enable_metrics else None
        self.performance_monitor = PerformanceMonitor() if enable_metrics else None

        # Caching
        self.cache = None
        if enable_cache and self.config.cache.enabled:
            self.cache = LRUCache(
                max_size=self.config.cache.max_size,
                default_ttl=self.config.cache.default_ttl,
                max_memory_bytes=self.config.cache.max_memory_bytes
            )

        # HTTP client with connection pooling
        limits = httpx.Limits(
            max_connections=self.config.connection_pool_size,
            max_keepalive_connections=self.config.connection_pool_size // 2,
            keepalive_expiry=self.config.connection_pool_max_keepalive
        )

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.provider_config.timeout),
            limits=limits,
            http2=True  # Enable HTTP/2 for better performance
        )

        # Track initialization
        self.logger.info(
            "Kimi client initialized",
            provider=self.provider.value,
            model=self.provider_config.model,
            cache_enabled=enable_cache,
            metrics_enabled=enable_metrics
        )

    @resilient(
        retry_config=RetryConfig(
            max_attempts=3,
            initial_delay=1.0,
            max_delay=60.0
        ),
        circuit_breaker_name="kimi_chat",
        timeout_seconds=30.0
    )
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        enable_swarm: bool = False,
        use_cache: bool = True
    ) -> ChatResponse:
        """
        Send chat request with production-grade error handling.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            stream: Enable streaming response
            enable_swarm: Enable agent swarm for complex tasks
            use_cache: Use cached response if available

        Returns:
            Validated ChatResponse

        Raises:
            ValidationError: If input validation fails
            NetworkError: If network request fails
            RateLimitError: If rate limit exceeded
            TimeoutError: If request times out
        """
        start_time = time.time()

        try:
            # Validate and convert to Pydantic models
            chat_request = self._build_chat_request(
                messages, temperature, max_tokens, stream, enable_swarm
            )

            # Check cache if enabled
            if use_cache and self.cache and not stream:
                cache_key_str = self._get_cache_key(chat_request)
                try:
                    cached_response = await self.cache.get(cache_key_str)
                    self.logger.info("Cache hit", key=cache_key_str[:16])
                    if self.metrics:
                        self.metrics.counter("cache.hit", 1.0, provider=self.provider.value)

                    # Return cached response with metadata
                    cached_response.cached = True
                    return cached_response
                except CacheMissError:
                    self.logger.debug("Cache miss", key=cache_key_str[:16])
                    if self.metrics:
                        self.metrics.counter("cache.miss", 1.0, provider=self.provider.value)

            # Execute request based on provider
            if self.provider == ProviderType.OLLAMA:
                response = await self._chat_ollama(chat_request)
            else:
                response = await self._chat_openai_compatible(chat_request)

            # Record performance
            duration = time.time() - start_time
            self._record_performance(chat_request, response, duration, success=True)

            # Cache response if enabled
            if use_cache and self.cache and not stream:
                cache_key_str = self._get_cache_key(chat_request)
                await self.cache.set(
                    cache_key_str,
                    response,
                    ttl=self.config.cache.default_ttl
                )

            return response

        except Exception as e:
            duration = time.time() - start_time
            self._record_performance(None, None, duration, success=False, error=str(e))

            # Re-raise with context
            self.logger.error(
                f"Chat request failed: {str(e)}",
                exc_info=e,
                provider=self.provider.value,
                duration=duration
            )
            raise

    async def _chat_ollama(self, request: ChatRequest) -> ChatResponse:
        """Execute chat request with Ollama."""
        url = f"{self.provider_config.base_url}/api/chat"

        # Convert messages to Ollama format
        ollama_messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in request.messages
        ]

        payload = {
            "model": self.provider_config.model,
            "messages": ollama_messages,
            "stream": request.stream,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens
            }
        }

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            # Convert to standardized format
            return self._parse_ollama_response(data)

        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e)
        except httpx.RequestError as e:
            raise ConnectionError(provider=self.provider.value, original_error=e)

    async def _chat_openai_compatible(self, request: ChatRequest) -> ChatResponse:
        """Execute chat request with OpenAI-compatible API."""
        url = f"{self.provider_config.base_url}/chat/completions"

        headers = {
            "Content-Type": "application/json"
        }

        # Add authentication if API key present
        if self.provider_config.api_key:
            headers["Authorization"] = f"Bearer {self.provider_config.api_key.get_secret_value()}"

        # Build payload
        payload = {
            "model": self.provider_config.model,
            "messages": [{"role": msg.role.value, "content": msg.content} for msg in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": request.stream
        }

        # Add agent swarm configuration if enabled
        if request.enable_swarm:
            payload["agent_swarm"] = {
                "enabled": True,
                "max_agents": request.max_agents or self.config.agent_swarm.max_agents,
                "parallel_execution": self.config.agent_swarm.parallel_execution
            }

        try:
            response = await self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            return self._parse_openai_response(data)

        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e)
        except httpx.RequestError as e:
            raise ConnectionError(provider=self.provider.value, original_error=e)

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream chat responses for real-time output.

        Args:
            messages: List of message dicts
            **kwargs: Additional chat parameters

        Yields:
            Response chunks as they arrive
        """
        kwargs["stream"] = True
        kwargs["use_cache"] = False  # Don't cache streaming responses

        request = self._build_chat_request(messages, **kwargs)

        if self.provider == ProviderType.OLLAMA:
            url = f"{self.provider_config.base_url}/api/chat"
        else:
            url = f"{self.provider_config.base_url}/chat/completions"

        # Prepare request
        payload = self._build_stream_payload(request)
        headers = self._build_headers()

        try:
            async with self.client.stream("POST", url, headers=headers, json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.strip():
                        # Parse and yield chunk
                        chunk = self._parse_stream_chunk(line)
                        if chunk:
                            yield chunk

        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e)
        except httpx.RequestError as e:
            raise ConnectionError(provider=self.provider.value, original_error=e)

    async def batch_chat(
        self,
        batch_request: BatchRequest
    ) -> BatchResponse:
        """
        Process multiple chat requests in batch.

        Args:
            batch_request: Batch request with multiple chat requests

        Returns:
            Batch response with all results
        """
        start_time = time.time()

        if batch_request.parallel:
            # Execute in parallel with concurrency limit
            semaphore = asyncio.Semaphore(batch_request.max_concurrency)

            async def execute_with_semaphore(req):
                async with semaphore:
                    try:
                        return await self.chat(
                            messages=[{"role": m.role.value, "content": m.content} for m in req.messages],
                            temperature=req.temperature,
                            max_tokens=req.max_tokens,
                            enable_swarm=req.enable_swarm
                        )
                    except Exception as e:
                        self.logger.error(f"Batch request failed: {str(e)}", exc_info=e)
                        return None

            results = await asyncio.gather(
                *[execute_with_semaphore(req) for req in batch_request.requests],
                return_exceptions=False
            )
        else:
            # Execute sequentially
            results = []
            for req in batch_request.requests:
                try:
                    result = await self.chat(
                        messages=[{"role": m.role.value, "content": m.content} for m in req.messages],
                        temperature=req.temperature,
                        max_tokens=req.max_tokens,
                        enable_swarm=req.enable_swarm
                    )
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Batch request failed: {str(e)}", exc_info=e)
                    results.append(None)

        # Filter out failures
        successful_results = [r for r in results if r is not None]
        failed_count = len(results) - len(successful_results)

        duration = (time.time() - start_time) * 1000  # Convert to ms

        return BatchResponse(
            results=successful_results,
            total_requests=len(batch_request.requests),
            successful_requests=len(successful_results),
            failed_requests=failed_count,
            total_time_ms=duration
        )

    async def agent_swarm_task(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        max_agents: Optional[int] = None
    ) -> AgentResult:
        """
        Execute complex task using agent swarm with comprehensive error handling.

        Args:
            task: Task description
            context: Additional context
            max_agents: Maximum agents to spawn

        Returns:
            Agent task result with metrics
        """
        task_id = f"task_{int(time.time() * 1000)}"
        start_time = time.time()

        try:
            system_message = {
                "role": "system",
                "content": f"""You are Kimi K2.5 with agent swarm capabilities.

For this task, you should:
1. Analyze complexity and break into parallelizable subtasks
2. Spawn specialized agents for each subtask
3. Coordinate their execution
4. Synthesize results into comprehensive response

Max agents: {max_agents or self.config.agent_swarm.max_agents}
Parallel execution: {self.config.agent_swarm.parallel_execution}
"""
            }

            user_message = {
                "role": "user",
                "content": task
            }

            if context:
                import json
                user_message["content"] += f"\n\nContext: {json.dumps(context, indent=2)}"

            response = await self.chat(
                messages=[system_message, user_message],
                enable_swarm=True,
                max_tokens=8192
            )

            execution_time = time.time() - start_time

            return AgentResult(
                task_id=task_id,
                success=True,
                result=response,
                agents_used=max_agents or self.config.agent_swarm.max_agents,
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time

            self.logger.error(
                f"Agent swarm task failed: {str(e)}",
                exc_info=e,
                task_id=task_id
            )

            return AgentResult(
                task_id=task_id,
                success=False,
                error=str(e),
                execution_time=execution_time
            )

    async def health_check(self) -> SystemHealth:
        """
        Comprehensive health check of all components.

        Returns:
            System health status
        """
        components = []

        # Check provider connectivity
        try:
            test_response = await asyncio.wait_for(
                self.chat(
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=10,
                    use_cache=False
                ),
                timeout=10.0
            )
            components.append(ComponentHealth(
                name=f"provider_{self.provider.value}",
                status=HealthStatus.HEALTHY,
                message="Provider responding normally"
            ))
        except Exception as e:
            components.append(ComponentHealth(
                name=f"provider_{self.provider.value}",
                status=HealthStatus.UNHEALTHY,
                message=str(e)
            ))

        # Check cache health
        if self.cache:
            cache_stats = self.cache.get_stats()
            cache_status = HealthStatus.HEALTHY if cache_stats["hit_rate"] > 0.1 or cache_stats["hits"] == 0 else HealthStatus.DEGRADED

            components.append(ComponentHealth(
                name="cache",
                status=cache_status,
                message=f"Hit rate: {cache_stats['hit_rate']:.2%}",
                metadata=cache_stats
            ))

        return SystemHealth(
            status=HealthStatus.HEALTHY,  # Will be determined by root_validator
            components=components
        )

    def get_metrics(self) -> SystemMetrics:
        """
        Get comprehensive system metrics.

        Returns:
            System metrics including performance, cache, and provider stats
        """
        if not self.performance_monitor:
            raise ValueError("Metrics not enabled")

        perf_summary = self.performance_monitor.get_summary()
        cache_stats = self.cache.get_stats() if self.cache else {}

        return SystemMetrics(
            uptime_seconds=time.time() - self._start_time if hasattr(self, "_start_time") else 0.0,
            performance=PerformanceMetrics(
                total_requests=perf_summary.get("total_operations", 0),
                successful_requests=perf_summary.get("successful", 0),
                failed_requests=perf_summary.get("failed", 0),
                average_latency_ms=perf_summary.get("latency", {}).get("average_seconds", 0.0) * 1000,
                total_tokens=perf_summary.get("tokens", {}).get("total", 0),
                total_cost=perf_summary.get("cost", {}).get("total", 0.0)
            ),
            cache=CacheMetrics(**cache_stats) if cache_stats else CacheMetrics(),
            providers=[
                ProviderMetrics(
                    provider=self.provider.value,
                    total_requests=perf_summary.get("total_operations", 0),
                    successful_requests=perf_summary.get("successful", 0),
                    failed_requests=perf_summary.get("failed", 0),
                    average_latency_ms=perf_summary.get("latency", {}).get("average_seconds", 0.0) * 1000,
                    total_tokens=perf_summary.get("tokens", {}).get("total", 0),
                    total_cost=perf_summary.get("cost", {}).get("total", 0.0)
                )
            ],
            circuit_breakers=[]
        )

    # Helper methods
    def _build_chat_request(self, messages, temperature=None, max_tokens=None, stream=False, enable_swarm=False) -> ChatRequest:
        """Build and validate chat request."""
        pydantic_messages = [
            Message(
                role=MessageRole(msg["role"]),
                content=msg["content"]
            )
            for msg in messages
        ]

        return ChatRequest(
            messages=pydantic_messages,
            temperature=temperature or self.provider_config.temperature,
            max_tokens=max_tokens or self.provider_config.max_tokens,
            stream=stream,
            enable_swarm=enable_swarm
        )

    def _get_cache_key(self, request: ChatRequest) -> str:
        """Generate cache key from request."""
        return cache_key(
            self.provider.value,
            self.provider_config.model,
            [{"role": m.role.value, "content": m.content} for m in request.messages],
            request.temperature,
            request.max_tokens
        )

    def _parse_ollama_response(self, data: Dict[str, Any]) -> ChatResponse:
        """Parse Ollama response to standardized format."""
        message_data = data.get("message", {})

        return ChatResponse(
            id=f"ollama_{int(time.time() * 1000)}",
            created=int(time.time()),
            model=self.provider_config.model,
            choices=[
                Choice(
                    index=0,
                    message=Message(
                        role=MessageRole(message_data.get("role", "assistant")),
                        content=message_data.get("content", "")
                    ),
                    finish_reason="stop"
                )
            ],
            provider=self.provider.value
        )

    def _parse_openai_response(self, data: Dict[str, Any]) -> ChatResponse:
        """Parse OpenAI-compatible response."""
        choices_data = data.get("choices", [])
        usage_data = data.get("usage")

        choices = [
            Choice(
                index=choice.get("index", 0),
                message=Message(
                    role=MessageRole(choice["message"]["role"]),
                    content=choice["message"]["content"]
                ),
                finish_reason=choice.get("finish_reason")
            )
            for choice in choices_data
        ]

        usage = None
        if usage_data:
            usage = TokenUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0)
            )

        return ChatResponse(
            id=data.get("id", f"resp_{int(time.time() * 1000)}"),
            created=data.get("created", int(time.time())),
            model=data.get("model", self.provider_config.model),
            choices=choices,
            usage=usage,
            provider=self.provider.value
        )

    def _handle_http_error(self, error: httpx.HTTPStatusError) -> KimiError:
        """Convert HTTP errors to appropriate Kimi exceptions."""
        status_code = error.response.status_code

        if status_code == 401:
            return InvalidAPIKeyError(provider=self.provider.value)
        elif status_code == 429:
            retry_after = error.response.headers.get("retry-after")
            return RateLimitError(
                provider=self.provider.value,
                retry_after=int(retry_after) if retry_after else None
            )
        elif status_code >= 500:
            return ProviderUnavailableError(
                provider=self.provider.value,
                status_code=status_code
            )
        else:
            return ProviderResponseError(
                provider=self.provider.value,
                status_code=status_code,
                response_body=error.response.text[:500]
            )

    def _record_performance(self, request, response, duration, success=True, error=None):
        """Record performance metrics."""
        if not self.performance_monitor:
            return

        stats = PerformanceStats(
            operation="chat",
            duration_seconds=duration,
            timestamp=datetime.utcnow(),
            success=success,
            error=error,
            metadata={"provider": self.provider.value},
            prompt_tokens=response.usage.prompt_tokens if response and response.usage else None,
            completion_tokens=response.usage.completion_tokens if response and response.usage else None,
            total_tokens=response.usage.total_tokens if response and response.usage else None,
            provider=self.provider.value
        )

        self.performance_monitor.record(stats)

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers."""
        headers = {"Content-Type": "application/json"}
        if self.provider_config.api_key:
            headers["Authorization"] = f"Bearer {self.provider_config.api_key.get_secret_value()}"
        return headers

    def _build_stream_payload(self, request: ChatRequest) -> Dict[str, Any]:
        """Build payload for streaming request."""
        return {
            "model": self.provider_config.model,
            "messages": [{"role": m.role.value, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True
        }

    def _parse_stream_chunk(self, line: str) -> Optional[str]:
        """Parse streaming chunk."""
        if line.startswith("data: "):
            line = line[6:]
        if line == "[DONE]":
            return None

        try:
            import json
            data = json.loads(line)
            choices = data.get("choices", [])
            if choices and "delta" in choices[0]:
                delta = choices[0]["delta"]
                return delta.get("content", "")
        except Exception:
            return None

        return None

    async def close(self):
        """Close client and cleanup resources."""
        await self.client.aclose()
        self.logger.info("Client closed")

    async def __aenter__(self):
        """Async context manager entry."""
        self._start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
