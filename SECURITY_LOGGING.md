# Security Logging Implementation

## Overview

This document describes the secure structured logging implementation that addresses **Critical Security Issue #2: Hardcoded API Keys in Environment Checks**.

## Security Issues Addressed

### Before: Insecure Logging Practices

The codebase previously used `console.log()` and `console.error()` which posed several security risks:

1. **Information Disclosure**: Error messages exposed internal dashboard URLs and API key structures
2. **No Redaction**: Sensitive data (API keys, tokens, passwords) could leak into logs
3. **Unstructured Logs**: Difficult to audit, filter, or monitor for security events
4. **Implementation Exposure**: Error messages revealed internal implementation details

### After: Secure Structured Logging

All logging now uses the **pino** structured logging library with:

1. **Automatic Redaction**: API keys, tokens, and passwords are automatically redacted
2. **Generic Error Messages**: No exposure of internal URLs or implementation details
3. **Structured Context**: All logs include context without exposing sensitive data
4. **Error Codes**: Use semantic error codes instead of revealing details
5. **Field Sanitization**: Automatic sanitization of sensitive object properties

## Implementation

### Logger Module: `lib/logger.ts`

The logger module provides:

- **Automatic Redaction**: Fields matching sensitive patterns are redacted
- **Context Sanitization**: Objects are sanitized before logging
- **Error Codes**: Semantic error codes for categorization
- **Environment Awareness**: Development vs production logging modes
- **Security First**: No sensitive data can leak through logs

### Sensitive Field Patterns

The following patterns are automatically redacted:
- `api_key` / `apiKey`
- `password`
- `secret`
- `token`
- `authorization`
- `credential`
- `auth`

### Error Codes

```typescript
enum ErrorCode {
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
```

## Usage Examples

### Before (Insecure)

```typescript
// ❌ INSECURE - Exposes internal URLs and implementation
console.error('Missing API key. Get one from https://dashboard.meshy.ai/api-keys');

// ❌ INSECURE - Could leak sensitive data
console.log('User data:', userData);

// ❌ INSECURE - Exposes error details
console.error('Error:', error.message, error.response.data);
```

### After (Secure)

```typescript
// ✅ SECURE - Generic message, structured logging
logger.error('API request failed', error, {
  component: 'APIClient',
  operation: 'fetchData',
});

// ✅ SECURE - Automatic redaction of sensitive fields
logger.info('User authenticated', {
  userId: user.id,
  apiKey: 'sk-123...', // Automatically redacted to [REDACTED]
});

// ✅ SECURE - Error codes without revealing implementation
logger.configError(ErrorCode.CONFIG_MISSING,
  'Required API key not configured. Please check deployment documentation.'
);
```

### Creating a Logger

```typescript
import { createComponentLogger, ErrorCode } from './lib/logger';

const logger = createComponentLogger('MyComponent');

// Log levels
logger.debug('Debug information', { details: 'value' });
logger.info('Informational message', { status: 'success' });
logger.warn('Warning message', { issue: 'deprecation' });
logger.error('Error occurred', error, { context: 'data' });

// Configuration errors (generic messages)
logger.configError(ErrorCode.CONFIG_MISSING);

// API errors (no URL/key exposure)
logger.apiError(ErrorCode.API_REQUEST_FAILED, {
  operation: 'fetchUsers',
  retryable: true,
});
```

## Files Modified

1. **lib/logger.ts** (NEW)
   - Secure structured logging module
   - Automatic redaction and sanitization
   - Error code definitions

2. **kimi_client.ts**
   - Replaced `console.log()` with `logger.info()`
   - Replaced `console.error()` with `logger.error()`
   - Added structured context to all logs

3. **examples/simple_chat.ts**
   - Updated to use secure logger
   - Removed emoji-based console logging
   - Added structured context

4. **examples/agent_swarm_demo.ts**
   - Updated to use secure logger
   - Removed console-based progress indicators
   - Added structured task tracking

5. **examples/research_swarm.ts**
   - Updated to use secure logger
   - Removed console-based output
   - Added structured research tracking

## Environment Variables

The logger respects the following environment variables:

- `LOG_LEVEL`: Set log level (debug, info, warn, error) - default: `info` in production, `debug` in development
- `NODE_ENV`: Set to `production` for production logging mode

## Development vs Production

### Development Mode
- Pretty-printed, colorized logs
- Debug level enabled
- Human-readable timestamps
- Detailed context

### Production Mode
- JSON-formatted logs
- Info level and above
- Machine-parseable
- Optimized for log aggregation

## Security Benefits

1. **No Information Leakage**: Internal URLs, API structures, and implementation details are never logged
2. **Automatic Redaction**: Sensitive fields are automatically redacted
3. **Audit Trail**: Structured logs provide comprehensive audit capabilities
4. **Error Tracking**: Error codes enable tracking without exposing details
5. **Compliance Ready**: Log format suitable for security compliance requirements

## Testing

To verify the logging implementation:

```bash
# Build the project
npm run build

# Run examples (logs will be pretty-printed in development)
npm run example:simple
npm run example:swarm
npm run example:research

# Check for any remaining console.log usage
grep -r "console\." --include="*.ts" --exclude-dir=node_modules .
```

## Recommendations

1. **Never use console.log()**: Always use the logger
2. **Use Error Codes**: Categorize errors with semantic codes
3. **Sanitize Context**: The logger does this automatically, but be aware
4. **Generic Messages**: Never expose internal implementation in error messages
5. **Monitor Logs**: Use log aggregation tools to monitor for security events

## Related Security Standards

This implementation aligns with:
- **OWASP Logging Guidelines**: Proper log level usage, no sensitive data in logs
- **NIST 800-53 AU-2**: Audit event content requirements
- **PCI-DSS 10.3**: Proper audit trail requirements
- **SOC 2**: Logging and monitoring controls

## Questions or Issues

For questions about the logging implementation, refer to:
- `lib/logger.ts` - Source code with inline documentation
- This document - Usage guidelines and examples
- pino documentation: https://github.com/pinojs/pino
