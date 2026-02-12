/**
 * Secure Structured Logging Utility
 *
 * This module provides secure logging capabilities that:
 * - Use structured logging (pino) instead of console.log
 * - Sanitize sensitive information from logs
 * - Provide proper log levels and contexts
 * - Never expose internal URLs, API keys, or implementation details
 */

import pino from 'pino';

// Define sensitive field patterns to redact
const SENSITIVE_PATTERNS = [
  'api_key',
  'apiKey',
  'password',
  'secret',
  'token',
  'authorization',
  'credential',
  'auth',
];

// Custom serializers to sanitize sensitive data
const serializers = {
  req: (req: any) => ({
    method: req.method,
    url: req.url,
    // Redact authorization headers
    headers: sanitizeHeaders(req.headers),
  }),
  res: (res: any) => ({
    statusCode: res.statusCode,
  }),
  err: pino.stdSerializers.err,
};

/**
 * Sanitize headers to remove sensitive information
 */
function sanitizeHeaders(headers: Record<string, any>): Record<string, string> {
  if (!headers) return {};

  const sanitized: Record<string, string> = {};
  for (const [key, value] of Object.entries(headers)) {
    const lowerKey = key.toLowerCase();
    if (lowerKey === 'authorization' || lowerKey.includes('key') || lowerKey.includes('token')) {
      sanitized[key] = '[REDACTED]';
    } else {
      sanitized[key] = String(value);
    }
  }
  return sanitized;
}

/**
 * Sanitize object to remove sensitive fields
 */
function sanitizeObject(obj: any): any {
  if (!obj || typeof obj !== 'object') return obj;

  const sanitized: any = Array.isArray(obj) ? [] : {};

  for (const [key, value] of Object.entries(obj)) {
    const lowerKey = key.toLowerCase();
    const isSensitive = SENSITIVE_PATTERNS.some(pattern =>
      lowerKey.includes(pattern.toLowerCase())
    );

    if (isSensitive) {
      sanitized[key] = '[REDACTED]';
    } else if (typeof value === 'object' && value !== null) {
      sanitized[key] = sanitizeObject(value);
    } else {
      sanitized[key] = value;
    }
  }

  return sanitized;
}

/**
 * Create a logger instance with security best practices
 */
function createLogger(component: string) {
  const isDevelopment = process.env.NODE_ENV !== 'production';

  return pino({
    name: 'kimi-agent',
    level: process.env.LOG_LEVEL || (isDevelopment ? 'debug' : 'info'),
    base: {
      component,
      env: process.env.NODE_ENV || 'development',
    },
    serializers,
    // Pretty print in development for readability
    transport: isDevelopment ? {
      target: 'pino-pretty',
      options: {
        colorize: true,
        translateTime: 'HH:MM:ss',
        ignore: 'pid,hostname',
      }
    } : undefined,
    // Redact sensitive fields automatically
    redact: {
      paths: [
        'apiKey',
        'api_key',
        'password',
        'secret',
        'token',
        'authorization',
        '*.apiKey',
        '*.api_key',
        '*.password',
        '*.secret',
        '*.token',
        '*.authorization',
      ],
      censor: '[REDACTED]',
    },
  });
}

/**
 * Error codes for structured error reporting
 */
export enum ErrorCode {
  CONFIG_MISSING = 'CONFIG_MISSING',
  CONFIG_INVALID = 'CONFIG_INVALID',
  API_REQUEST_FAILED = 'API_REQUEST_FAILED',
  API_RESPONSE_INVALID = 'API_RESPONSE_INVALID',
  TIMEOUT = 'TIMEOUT',
  NETWORK_ERROR = 'NETWORK_ERROR',
  AUTHENTICATION_FAILED = 'AUTHENTICATION_FAILED',
  RATE_LIMIT_EXCEEDED = 'RATE_LIMIT_EXCEEDED',
  UNKNOWN_ERROR = 'UNKNOWN_ERROR',
}

/**
 * Secure logger class with context awareness
 */
export class Logger {
  private logger: pino.Logger;

  constructor(component: string) {
    this.logger = createLogger(component);
  }

  /**
   * Log debug information (development only)
   */
  debug(message: string, context?: Record<string, any>): void {
    this.logger.debug(sanitizeObject(context), message);
  }

  /**
   * Log informational messages
   */
  info(message: string, context?: Record<string, any>): void {
    this.logger.info(sanitizeObject(context), message);
  }

  /**
   * Log warning messages
   */
  warn(message: string, context?: Record<string, any>): void {
    this.logger.warn(sanitizeObject(context), message);
  }

  /**
   * Log error messages with error code
   */
  error(message: string, error?: Error | unknown, context?: Record<string, any>): void {
    const errorContext = {
      ...sanitizeObject(context),
      err: error instanceof Error ? error : new Error(String(error)),
    };
    this.logger.error(errorContext, message);
  }

  /**
   * Log configuration errors without exposing internals
   */
  configError(errorCode: ErrorCode, message?: string): void {
    this.logger.error({
      errorCode,
      type: 'configuration',
    }, message || 'Configuration error occurred. Please check deployment documentation.');
  }

  /**
   * Log API errors without exposing URLs or keys
   */
  apiError(errorCode: ErrorCode, context?: Record<string, any>): void {
    this.logger.error({
      errorCode,
      type: 'api',
      ...sanitizeObject(context),
    }, 'API request failed. Check configuration and network connectivity.');
  }

  /**
   * Create a child logger with additional context
   */
  child(bindings: Record<string, any>): Logger {
    const childLogger = new Logger('');
    childLogger.logger = this.logger.child(sanitizeObject(bindings));
    return childLogger;
  }
}

/**
 * Create a logger for a specific component
 */
export function createComponentLogger(component: string): Logger {
  return new Logger(component);
}

export default Logger;
