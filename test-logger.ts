/**
 * Test script to demonstrate secure logging
 *
 * This script demonstrates:
 * 1. Automatic redaction of sensitive fields
 * 2. Structured logging with context
 * 3. Different log levels
 * 4. Error code usage
 */

import { createComponentLogger, ErrorCode } from './lib/logger';

const logger = createComponentLogger('LoggerTest');

async function demonstrateSecureLogging() {
  console.log('='.repeat(80));
  console.log('SECURE LOGGING DEMONSTRATION');
  console.log('='.repeat(80));
  console.log('\nNote: The following logs demonstrate automatic redaction and secure practices\n');

  // 1. Info logging with safe context
  logger.info('Application started', {
    version: '1.0.0',
    environment: 'test',
  });

  // 2. Demonstrate automatic redaction of sensitive fields
  logger.info('User authentication attempt', {
    userId: 'user-12345',
    apiKey: 'sk-1234567890abcdef', // Will be automatically redacted
    password: 'super-secret', // Will be automatically redacted
    token: 'bearer-token-xyz', // Will be automatically redacted
    email: 'user@example.com', // Safe to log
  });

  // 3. Debug logging (only visible in development)
  logger.debug('Processing request details', {
    requestId: 'req-abc123',
    method: 'POST',
    path: '/api/users',
  });

  // 4. Warning logging
  logger.warn('Rate limit approaching threshold', {
    current: 90,
    limit: 100,
    action: 'throttle_requests',
  });

  // 5. Configuration error with error code
  logger.configError(
    ErrorCode.CONFIG_MISSING,
    'Required API key not configured. Please check deployment documentation.'
  );

  // 6. API error with context
  logger.apiError(ErrorCode.API_REQUEST_FAILED, {
    operation: 'fetchUsers',
    retryable: true,
    attemptNumber: 1,
  });

  // 7. Error logging with exception
  try {
    throw new Error('Simulated database connection error');
  } catch (error) {
    logger.error('Database operation failed', error, {
      operation: 'connect',
      database: 'users_db',
      retryScheduled: true,
    });
  }

  // 8. Demonstrate nested object sanitization
  logger.info('Complex object with nested secrets', {
    user: {
      id: 'user-123',
      profile: {
        name: 'John Doe',
        apiKey: 'nested-secret-key', // Will be redacted
        preferences: {
          theme: 'dark',
          token: 'user-token-xyz', // Will be redacted
        },
      },
    },
  });

  console.log('\n' + '='.repeat(80));
  console.log('DEMONSTRATION COMPLETE');
  console.log('='.repeat(80));
  console.log('\nAll sensitive fields (apiKey, password, token) have been automatically redacted.');
  console.log('Check the logs above to verify [REDACTED] appears instead of actual values.\n');
}

// Run the demonstration
demonstrateSecureLogging().catch((error) => {
  logger.error('Demonstration failed', error);
  process.exit(1);
});
