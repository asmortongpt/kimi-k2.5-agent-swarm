#!/usr/bin/env python3
"""
Production-Grade Configuration Management
Type-safe configuration with validation, secrets management, and hot-reload support.
"""

import os
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator, SecretStr
from pydantic_settings import BaseSettings
from enum import Enum


class Environment(str, Enum):
    """Application environment."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class ProviderType(str, Enum):
    """Supported AI providers."""
    MOONSHOT = "moonshot"
    OLLAMA = "ollama"
    TOGETHER = "together"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LogFormat(str, Enum):
    """Log output format."""
    JSON = "json"
    TEXT = "text"


class ProviderConfig(BaseModel):
    """Configuration for a specific provider."""
    name: ProviderType
    api_key: Optional[SecretStr] = None
    base_url: Optional[str] = None
    model: str
    max_tokens: int = Field(default=4096, ge=1, le=128000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    timeout: float = Field(default=30.0, ge=1.0, le=600.0)
    enabled: bool = True

    class Config:
        use_enum_values = True


class RetryConfig(BaseModel):
    """Retry behavior configuration."""
    max_attempts: int = Field(default=3, ge=1, le=10)
    initial_delay: float = Field(default=1.0, ge=0.1, le=60.0)
    max_delay: float = Field(default=60.0, ge=1.0, le=600.0)
    exponential_base: float = Field(default=2.0, ge=1.0, le=10.0)
    jitter: bool = True


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""
    enabled: bool = True
    failure_threshold: int = Field(default=5, ge=1, le=100)
    success_threshold: int = Field(default=2, ge=1, le=10)
    timeout: float = Field(default=60.0, ge=1.0, le=600.0)


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""
    enabled: bool = True
    max_requests: int = Field(default=100, ge=1)
    time_window: float = Field(default=60.0, ge=1.0)
    burst_size: Optional[int] = Field(default=None, ge=1)


class CacheConfig(BaseModel):
    """Cache configuration."""
    enabled: bool = True
    max_size: int = Field(default=1000, ge=1)
    default_ttl: Optional[float] = Field(default=300.0, ge=1.0)
    max_memory_bytes: Optional[int] = Field(default=None, ge=1)


class ObservabilityConfig(BaseModel):
    """Observability configuration."""
    logging_enabled: bool = True
    log_level: str = Field(default="INFO")
    log_format: LogFormat = LogFormat.JSON
    metrics_enabled: bool = True
    tracing_enabled: bool = False
    performance_monitoring: bool = True


class AgentSwarmConfig(BaseModel):
    """Agent swarm configuration."""
    max_agents: int = Field(default=100, ge=1, le=1000)
    parallel_execution: bool = True
    timeout: float = Field(default=300.0, ge=1.0, le=3600.0)
    enable_thinking_mode: bool = True


class SecurityConfig(BaseModel):
    """Security configuration."""
    api_key_rotation_days: int = Field(default=90, ge=1)
    tls_verify: bool = True
    allowed_hosts: List[str] = Field(default_factory=list)
    max_request_size_bytes: int = Field(default=10485760, ge=1)  # 10MB
    rate_limit_by_ip: bool = True


class KimiConfig(BaseSettings):
    """
    Main application configuration.

    Loads from environment variables and .env file.
    Provides validation and type safety.
    """

    # Environment
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False

    # Default provider
    default_provider: ProviderType = ProviderType.OLLAMA

    # Provider configurations
    moonshot: ProviderConfig = Field(
        default_factory=lambda: ProviderConfig(
            name=ProviderType.MOONSHOT,
            model="moonshot-v1-8k",
            base_url="https://api.moonshot.cn/v1"
        )
    )

    ollama: ProviderConfig = Field(
        default_factory=lambda: ProviderConfig(
            name=ProviderType.OLLAMA,
            model="kimi-k2.5:cloud",
            base_url="http://localhost:11434"
        )
    )

    together: ProviderConfig = Field(
        default_factory=lambda: ProviderConfig(
            name=ProviderType.TOGETHER,
            model="meta-llama/Llama-2-70b-chat-hf",
            base_url="https://api.together.xyz/v1"
        )
    )

    # Resilience
    retry: RetryConfig = Field(default_factory=RetryConfig)
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)

    # Caching
    cache: CacheConfig = Field(default_factory=CacheConfig)

    # Observability
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)

    # Agent swarm
    agent_swarm: AgentSwarmConfig = Field(default_factory=AgentSwarmConfig)

    # Security
    security: SecurityConfig = Field(default_factory=SecurityConfig)

    # Connection pooling
    connection_pool_size: int = Field(default=100, ge=1, le=1000)
    connection_pool_max_keepalive: float = Field(default=30.0, ge=1.0)

    class Config:
        env_prefix = "KIMI_"
        env_nested_delimiter = "__"
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"

    @validator("environment", pre=True)
    def validate_environment(cls, v):
        """Ensure environment is valid."""
        if isinstance(v, str):
            return Environment(v.lower())
        return v

    @validator("default_provider", pre=True)
    def validate_provider(cls, v):
        """Ensure provider is valid."""
        if isinstance(v, str):
            return ProviderType(v.lower())
        return v

    def get_provider_config(self, provider: ProviderType) -> ProviderConfig:
        """
        Get configuration for specific provider.

        Args:
            provider: Provider type

        Returns:
            Provider configuration

        Raises:
            ValueError: If provider not configured
        """
        config_map = {
            ProviderType.MOONSHOT: self.moonshot,
            ProviderType.OLLAMA: self.ollama,
            ProviderType.TOGETHER: self.together,
        }

        if provider not in config_map:
            raise ValueError(f"Provider {provider} not configured")

        config = config_map[provider]

        # Load API key from environment if not set
        if config.api_key is None and provider != ProviderType.OLLAMA:
            env_key = f"{provider.value.upper()}_API_KEY"
            api_key = os.getenv(env_key)
            if api_key:
                config.api_key = SecretStr(api_key)

        # Load base URL from environment if not set
        if config.base_url is None:
            env_key = f"{provider.value.upper()}_API_BASE"
            base_url = os.getenv(env_key)
            if base_url:
                config.base_url = base_url

        return config

    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Args:
            include_secrets: Whether to include secret values

        Returns:
            Configuration as dictionary
        """
        data = self.dict()

        if not include_secrets:
            # Redact secrets
            for provider_key in ["moonshot", "ollama", "together"]:
                if provider_key in data and "api_key" in data[provider_key]:
                    if data[provider_key]["api_key"]:
                        data[provider_key]["api_key"] = "***REDACTED***"

        return data

    def validate_config(self) -> List[str]:
        """
        Validate configuration and return list of issues.

        Returns:
            List of validation error messages (empty if valid)
        """
        issues = []

        # Check default provider is enabled
        default_config = self.get_provider_config(self.default_provider)
        if not default_config.enabled:
            issues.append(f"Default provider {self.default_provider} is disabled")

        # Check API keys for enabled providers
        for provider in [ProviderType.MOONSHOT, ProviderType.TOGETHER]:
            config = self.get_provider_config(provider)
            if config.enabled and not config.api_key:
                issues.append(f"Provider {provider} is enabled but API key is missing")

        # Validate retry config
        if self.retry.max_delay < self.retry.initial_delay:
            issues.append("Retry max_delay must be >= initial_delay")

        # Validate circuit breaker
        if self.circuit_breaker.enabled and self.circuit_breaker.success_threshold > self.circuit_breaker.failure_threshold:
            issues.append("Circuit breaker success_threshold should be <= failure_threshold")

        # Validate cache
        if self.cache.enabled and self.cache.max_memory_bytes:
            if self.cache.max_memory_bytes < 1024 * 1024:  # 1MB minimum
                issues.append("Cache max_memory_bytes should be at least 1MB")

        return issues


class ConfigManager:
    """
    Configuration manager with hot-reload support.

    Manages configuration lifecycle and updates.
    """

    def __init__(self, config: Optional[KimiConfig] = None):
        self._config = config or KimiConfig()
        self._validate()

    def _validate(self):
        """Validate configuration and raise if invalid."""
        issues = self._config.validate_config()
        if issues:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {issue}" for issue in issues)
            raise ValueError(error_msg)

    @property
    def config(self) -> KimiConfig:
        """Get current configuration."""
        return self._config

    def reload(self):
        """Reload configuration from environment."""
        self._config = KimiConfig()
        self._validate()

    def update(self, **kwargs):
        """
        Update configuration values.

        Args:
            **kwargs: Configuration values to update
        """
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)

        self._validate()

    def get_provider_config(self, provider: Optional[ProviderType] = None) -> ProviderConfig:
        """
        Get provider configuration.

        Args:
            provider: Provider type (uses default if None)

        Returns:
            Provider configuration
        """
        provider_type = provider or self._config.default_provider
        return self._config.get_provider_config(provider_type)


# Global configuration instance
config_manager = ConfigManager()


def get_config() -> KimiConfig:
    """Get global configuration."""
    return config_manager.config


def reload_config():
    """Reload global configuration."""
    config_manager.reload()
