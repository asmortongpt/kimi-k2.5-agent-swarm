#!/usr/bin/env python3
"""
Production-Grade Observability System
Structured logging, metrics collection, and distributed tracing support.
"""

import logging
import time
import json
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from functools import wraps
from contextvars import ContextVar
from enum import Enum
import sys

# Context variables for distributed tracing
trace_id_var: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
span_id_var: ContextVar[Optional[str]] = ContextVar('span_id', default=None)


class LogLevel(Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class StructuredLogEntry:
    """Structured log entry for JSON logging."""
    timestamp: str
    level: str
    message: str
    logger_name: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    exception: Optional[Dict[str, Any]] = None

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(asdict(self), default=str)


class StructuredLogger:
    """
    Structured logger with context management.

    Provides JSON-formatted logging with automatic trace ID propagation.
    """

    def __init__(self, name: str, level: LogLevel = LogLevel.INFO):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.value))

        # Configure JSON formatter if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(handler)

    def _create_entry(
        self,
        level: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Exception] = None
    ) -> StructuredLogEntry:
        """Create structured log entry."""
        exception_data = None
        if exc_info:
            exception_data = {
                "type": type(exc_info).__name__,
                "message": str(exc_info),
                "traceback": self._format_exception(exc_info)
            }

        return StructuredLogEntry(
            timestamp=datetime.utcnow().isoformat() + 'Z',
            level=level,
            message=message,
            logger_name=self.name,
            trace_id=trace_id_var.get(),
            span_id=span_id_var.get(),
            context=context or {},
            exception=exception_data
        )

    def _format_exception(self, exc: Exception) -> str:
        """Format exception for logging."""
        import traceback
        return ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    def debug(self, message: str, **context):
        """Log debug message."""
        entry = self._create_entry("DEBUG", message, context)
        self.logger.debug(entry.to_json())

    def info(self, message: str, **context):
        """Log info message."""
        entry = self._create_entry("INFO", message, context)
        self.logger.info(entry.to_json())

    def warning(self, message: str, **context):
        """Log warning message."""
        entry = self._create_entry("WARNING", message, context)
        self.logger.warning(entry.to_json())

    def error(self, message: str, exc_info: Optional[Exception] = None, **context):
        """Log error message."""
        entry = self._create_entry("ERROR", message, context, exc_info)
        self.logger.error(entry.to_json())

    def critical(self, message: str, exc_info: Optional[Exception] = None, **context):
        """Log critical message."""
        entry = self._create_entry("CRITICAL", message, context, exc_info)
        self.logger.critical(entry.to_json())


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON if not already formatted."""
        # If message is already JSON, return as-is
        if record.getMessage().startswith('{'):
            return record.getMessage()

        # Otherwise create structured log entry
        entry = StructuredLogEntry(
            timestamp=datetime.utcfromtimestamp(record.created).isoformat() + 'Z',
            level=record.levelname,
            message=record.getMessage(),
            logger_name=record.name,
            trace_id=trace_id_var.get(),
            span_id=span_id_var.get()
        )
        return entry.to_json()


@dataclass
class Metric:
    """Base metric class."""
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags
        }


class MetricsCollector:
    """
    Metrics collector for performance monitoring.

    Collects counters, gauges, histograms, and timers.
    """

    def __init__(self):
        self.metrics: list[Metric] = []
        self.logger = StructuredLogger("metrics")

    def counter(self, name: str, value: float = 1.0, **tags):
        """Increment a counter metric."""
        metric = Metric(name=f"{name}.count", value=value, tags=tags)
        self.metrics.append(metric)
        self.logger.debug(f"Counter: {name}", metric=metric.to_dict())

    def gauge(self, name: str, value: float, **tags):
        """Record a gauge metric (point-in-time value)."""
        metric = Metric(name=f"{name}.gauge", value=value, tags=tags)
        self.metrics.append(metric)
        self.logger.debug(f"Gauge: {name}", metric=metric.to_dict())

    def histogram(self, name: str, value: float, **tags):
        """Record a histogram metric (distribution)."""
        metric = Metric(name=f"{name}.histogram", value=value, tags=tags)
        self.metrics.append(metric)
        self.logger.debug(f"Histogram: {name}", metric=metric.to_dict())

    def timer(self, name: str, duration_seconds: float, **tags):
        """Record a timing metric."""
        metric = Metric(name=f"{name}.duration", value=duration_seconds, tags=tags)
        self.metrics.append(metric)
        self.logger.debug(f"Timer: {name}", metric=metric.to_dict())

    def get_metrics(self) -> list[Dict[str, Any]]:
        """Get all collected metrics."""
        return [m.to_dict() for m in self.metrics]

    def clear(self):
        """Clear collected metrics."""
        self.metrics.clear()


@dataclass
class PerformanceStats:
    """Performance statistics for an operation."""
    operation: str
    duration_seconds: float
    timestamp: datetime
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Token usage (for LLM calls)
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None

    # Cost tracking
    estimated_cost: Optional[float] = None
    provider: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "operation": self.operation,
            "duration_seconds": self.duration_seconds,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata,
            "tokens": {
                "prompt": self.prompt_tokens,
                "completion": self.completion_tokens,
                "total": self.total_tokens
            } if self.total_tokens else None,
            "cost": {
                "estimated_cost": self.estimated_cost,
                "provider": self.provider
            } if self.estimated_cost else None
        }


class PerformanceMonitor:
    """
    Performance monitoring with detailed statistics.

    Tracks latency, token usage, costs, and success rates.
    """

    def __init__(self):
        self.stats: list[PerformanceStats] = []
        self.logger = StructuredLogger("performance")
        self.metrics = MetricsCollector()

    def record(self, stats: PerformanceStats):
        """Record performance statistics."""
        self.stats.append(stats)

        # Log performance
        self.logger.info(
            f"Operation completed: {stats.operation}",
            duration=stats.duration_seconds,
            success=stats.success,
            tokens=stats.total_tokens,
            cost=stats.estimated_cost
        )

        # Record metrics
        self.metrics.timer(
            f"operation.{stats.operation}",
            stats.duration_seconds,
            success=str(stats.success),
            provider=stats.provider or "unknown"
        )

        if stats.total_tokens:
            self.metrics.counter(
                "tokens.usage",
                stats.total_tokens,
                operation=stats.operation,
                provider=stats.provider or "unknown"
            )

        if stats.estimated_cost:
            self.metrics.counter(
                "cost.total",
                stats.estimated_cost,
                operation=stats.operation,
                provider=stats.provider or "unknown"
            )

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        if not self.stats:
            return {"total_operations": 0}

        total = len(self.stats)
        successful = sum(1 for s in self.stats if s.success)
        failed = total - successful

        durations = [s.duration_seconds for s in self.stats]
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)

        total_tokens = sum(s.total_tokens or 0 for s in self.stats)
        total_cost = sum(s.estimated_cost or 0.0 for s in self.stats)

        return {
            "total_operations": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0.0,
            "latency": {
                "average_seconds": avg_duration,
                "max_seconds": max_duration,
                "min_seconds": min_duration
            },
            "tokens": {
                "total": total_tokens,
                "average_per_operation": total_tokens / total if total > 0 else 0
            },
            "cost": {
                "total": total_cost,
                "average_per_operation": total_cost / total if total > 0 else 0.0
            }
        }

    def clear(self):
        """Clear statistics."""
        self.stats.clear()
        self.metrics.clear()


def measure_performance(
    operation: str,
    logger: Optional[StructuredLogger] = None,
    metrics: Optional[MetricsCollector] = None
):
    """
    Decorator to measure function performance.

    Args:
        operation: Operation name
        logger: Optional logger for output
        metrics: Optional metrics collector

    Example:
        @measure_performance("api_call")
        async def make_api_call():
            pass
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            error = None
            success = True

            try:
                result = await func(*args, **kwargs)
                return result

            except Exception as e:
                success = False
                error = str(e)
                raise

            finally:
                duration = time.time() - start_time

                if logger:
                    logger.info(
                        f"Operation completed: {operation}",
                        duration=duration,
                        success=success,
                        error=error
                    )

                if metrics:
                    metrics.timer(operation, duration, success=str(success))
                    if not success:
                        metrics.counter(f"{operation}.error", 1.0)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            error = None
            success = True

            try:
                result = func(*args, **kwargs)
                return result

            except Exception as e:
                success = False
                error = str(e)
                raise

            finally:
                duration = time.time() - start_time

                if logger:
                    logger.info(
                        f"Operation completed: {operation}",
                        duration=duration,
                        success=success,
                        error=error
                    )

                if metrics:
                    metrics.timer(operation, duration, success=str(success))
                    if not success:
                        metrics.counter(f"{operation}.error", 1.0)

        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Global instances for convenience
default_logger = StructuredLogger("kimi")
default_metrics = MetricsCollector()
default_performance_monitor = PerformanceMonitor()
