#!/usr/bin/env python3
"""
Production-Grade Exception Hierarchy for Kimi K2.5
Comprehensive exception handling with detailed context and error recovery guidance.
"""

from typing import Optional, Dict, Any
from enum import Enum


class ErrorCategory(Enum):
    """Error categories for monitoring and alerting."""
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    VALIDATION = "validation"
    PROVIDER = "provider"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    CONFIGURATION = "configuration"
    INTERNAL = "internal"


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class KimiError(Exception):
    """
    Base exception for all Kimi errors.

    Attributes:
        message: Human-readable error message
        category: Error category for classification
        severity: Error severity level
        context: Additional context about the error
        recovery_hint: Suggestion for error recovery
        original_error: Original exception if wrapped
    """

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.INTERNAL,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        recovery_hint: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.recovery_hint = recovery_hint
        self.original_error = original_error

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "context": self.context,
            "recovery_hint": self.recovery_hint,
            "original_error": str(self.original_error) if self.original_error else None
        }


# Network-related errors
class NetworkError(KimiError):
    """Base class for network-related errors."""

    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("category", ErrorCategory.NETWORK)
        kwargs.setdefault("severity", ErrorSeverity.HIGH)
        super().__init__(message, **kwargs)


class ConnectionError(NetworkError):
    """Failed to establish connection to provider."""

    def __init__(self, provider: str, original_error: Optional[Exception] = None):
        super().__init__(
            f"Failed to connect to provider: {provider}",
            recovery_hint="Check network connectivity and provider availability. Consider using fallback provider.",
            context={"provider": provider},
            original_error=original_error
        )


class TimeoutError(NetworkError):
    """Request timed out."""

    def __init__(
        self,
        timeout_seconds: float,
        operation: str,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            f"Operation '{operation}' timed out after {timeout_seconds}s",
            category=ErrorCategory.TIMEOUT,
            recovery_hint="Increase timeout value or optimize request complexity. Consider breaking into smaller requests.",
            context={"timeout_seconds": timeout_seconds, "operation": operation},
            original_error=original_error
        )


# Authentication errors
class AuthenticationError(KimiError):
    """Authentication-related errors."""

    def __init__(self, message: str, provider: str, **kwargs):
        kwargs.setdefault("category", ErrorCategory.AUTHENTICATION)
        kwargs.setdefault("severity", ErrorSeverity.CRITICAL)
        kwargs.setdefault("recovery_hint", "Verify API key and provider credentials")
        kwargs["context"] = kwargs.get("context", {})
        kwargs["context"]["provider"] = provider
        super().__init__(message, **kwargs)


class InvalidAPIKeyError(AuthenticationError):
    """API key is invalid or expired."""

    def __init__(self, provider: str):
        super().__init__(
            f"Invalid or expired API key for provider: {provider}",
            provider=provider,
            recovery_hint="Check API key validity and regenerate if necessary"
        )


class InsufficientPermissionsError(AuthenticationError):
    """API key lacks required permissions."""

    def __init__(self, provider: str, required_permission: str):
        super().__init__(
            f"API key lacks permission '{required_permission}' for provider: {provider}",
            provider=provider,
            context={"required_permission": required_permission},
            recovery_hint="Update API key permissions or use a key with appropriate access"
        )


# Rate limiting errors
class RateLimitError(KimiError):
    """Rate limit exceeded."""

    def __init__(
        self,
        provider: str,
        retry_after: Optional[int] = None,
        limit_type: str = "requests"
    ):
        retry_hint = f"Retry after {retry_after} seconds" if retry_after else "Implement exponential backoff"
        super().__init__(
            f"Rate limit exceeded for provider: {provider}",
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.MEDIUM,
            context={
                "provider": provider,
                "retry_after": retry_after,
                "limit_type": limit_type
            },
            recovery_hint=retry_hint
        )


# Validation errors
class ValidationError(KimiError):
    """Input validation failed."""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        kwargs.setdefault("category", ErrorCategory.VALIDATION)
        kwargs.setdefault("severity", ErrorSeverity.LOW)
        kwargs["context"] = kwargs.get("context", {})
        if field:
            kwargs["context"]["field"] = field
        super().__init__(message, **kwargs)


class InvalidModelError(ValidationError):
    """Invalid model specified."""

    def __init__(self, model: str, provider: str, available_models: Optional[list] = None):
        message = f"Invalid model '{model}' for provider '{provider}'"
        if available_models:
            message += f". Available models: {', '.join(available_models)}"

        super().__init__(
            message,
            field="model",
            context={
                "model": model,
                "provider": provider,
                "available_models": available_models
            },
            recovery_hint="Use a supported model for this provider"
        )


class InvalidParameterError(ValidationError):
    """Invalid parameter value."""

    def __init__(self, parameter: str, value: Any, expected: str):
        super().__init__(
            f"Invalid value for parameter '{parameter}': {value}. Expected: {expected}",
            field=parameter,
            context={"parameter": parameter, "value": value, "expected": expected},
            recovery_hint=f"Ensure {parameter} matches expected format: {expected}"
        )


# Provider errors
class ProviderError(KimiError):
    """Provider-specific errors."""

    def __init__(self, provider: str, message: str, **kwargs):
        kwargs.setdefault("category", ErrorCategory.PROVIDER)
        kwargs["context"] = kwargs.get("context", {})
        kwargs["context"]["provider"] = provider
        super().__init__(message, **kwargs)


class ProviderUnavailableError(ProviderError):
    """Provider is temporarily unavailable."""

    def __init__(self, provider: str, status_code: Optional[int] = None):
        super().__init__(
            provider,
            f"Provider '{provider}' is temporarily unavailable",
            severity=ErrorSeverity.HIGH,
            context={"status_code": status_code} if status_code else {},
            recovery_hint="Wait and retry, or switch to fallback provider"
        )


class ProviderResponseError(ProviderError):
    """Provider returned unexpected response."""

    def __init__(self, provider: str, status_code: int, response_body: Optional[str] = None):
        super().__init__(
            provider,
            f"Provider '{provider}' returned error status {status_code}",
            context={"status_code": status_code, "response_body": response_body},
            recovery_hint="Check provider status page and validate request parameters"
        )


# Resource errors
class ResourceError(KimiError):
    """Resource-related errors."""

    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("category", ErrorCategory.RESOURCE)
        kwargs.setdefault("severity", ErrorSeverity.MEDIUM)
        super().__init__(message, **kwargs)


class ResourceExhaustedError(ResourceError):
    """System resource exhausted."""

    def __init__(self, resource_type: str, current_usage: Any, limit: Any):
        super().__init__(
            f"Resource '{resource_type}' exhausted: {current_usage}/{limit}",
            context={
                "resource_type": resource_type,
                "current_usage": current_usage,
                "limit": limit
            },
            recovery_hint=f"Reduce {resource_type} usage or increase limits"
        )


class QuotaExceededError(ResourceError):
    """API quota exceeded."""

    def __init__(self, quota_type: str, provider: str, reset_time: Optional[str] = None):
        message = f"Quota exceeded for '{quota_type}' on provider '{provider}'"
        if reset_time:
            message += f". Resets at: {reset_time}"

        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            context={
                "quota_type": quota_type,
                "provider": provider,
                "reset_time": reset_time
            },
            recovery_hint="Wait for quota reset or upgrade plan"
        )


# Configuration errors
class ConfigurationError(KimiError):
    """Configuration-related errors."""

    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("category", ErrorCategory.CONFIGURATION)
        kwargs.setdefault("severity", ErrorSeverity.CRITICAL)
        super().__init__(message, **kwargs)


class MissingConfigurationError(ConfigurationError):
    """Required configuration is missing."""

    def __init__(self, config_key: str):
        super().__init__(
            f"Missing required configuration: {config_key}",
            context={"config_key": config_key},
            recovery_hint=f"Set {config_key} in environment variables or configuration file"
        )


class InvalidConfigurationError(ConfigurationError):
    """Configuration value is invalid."""

    def __init__(self, config_key: str, value: Any, reason: str):
        super().__init__(
            f"Invalid configuration for '{config_key}': {reason}",
            context={"config_key": config_key, "value": value, "reason": reason},
            recovery_hint=f"Update {config_key} to a valid value"
        )


# Circuit breaker errors
class CircuitBreakerError(KimiError):
    """Circuit breaker is open."""

    def __init__(self, service: str, failure_count: int, threshold: int):
        super().__init__(
            f"Circuit breaker open for '{service}' after {failure_count} failures (threshold: {threshold})",
            category=ErrorCategory.PROVIDER,
            severity=ErrorSeverity.HIGH,
            context={
                "service": service,
                "failure_count": failure_count,
                "threshold": threshold
            },
            recovery_hint="Wait for circuit breaker to reset or switch to fallback provider"
        )


# Retry exhausted error
class RetryExhaustedError(KimiError):
    """All retry attempts exhausted."""

    def __init__(self, operation: str, attempts: int, last_error: Exception):
        super().__init__(
            f"Retry exhausted for '{operation}' after {attempts} attempts",
            category=ErrorCategory.INTERNAL,
            severity=ErrorSeverity.HIGH,
            context={"operation": operation, "attempts": attempts},
            recovery_hint="Check underlying error and consider manual intervention",
            original_error=last_error
        )


# Cache errors
class CacheError(KimiError):
    """Cache-related errors."""

    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("category", ErrorCategory.INTERNAL)
        kwargs.setdefault("severity", ErrorSeverity.LOW)
        super().__init__(message, **kwargs)


class CacheMissError(CacheError):
    """Cache entry not found."""

    def __init__(self, key: str):
        super().__init__(
            f"Cache miss for key: {key}",
            context={"key": key},
            recovery_hint="Fetch from source and populate cache"
        )


class CacheInvalidationError(CacheError):
    """Failed to invalidate cache."""

    def __init__(self, key: str, reason: str):
        super().__init__(
            f"Failed to invalidate cache for key '{key}': {reason}",
            context={"key": key, "reason": reason},
            recovery_hint="Manual cache clear may be required"
        )
