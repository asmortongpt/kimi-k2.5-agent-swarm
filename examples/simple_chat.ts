/**
 * Example 1: Simple Chat
 * Basic interaction with Kimi K2.5 without agent swarm
 */

import KimiClient, { ProviderType } from '../kimi_client';
import { createComponentLogger } from '../lib/logger';

const logger = createComponentLogger('SimpleChatExample');

async function simpleChat() {
  logger.info('Starting simple chat example');

  const client = new KimiClient(ProviderType.OLLAMA);

  try {
    // Simple question
    logger.info('Asking question about Kimi K2.5');
    const response1 = await client.chat([
      { role: 'user', content: 'What is Kimi K2.5 and what makes it special?' }
    ]);
    logger.info('Received response', {
      hasContent: !!response1.message?.content,
      questionType: 'introduction',
    });

    // Technical question
    logger.info('Asking technical question about MoE architecture');
    const response2 = await client.chat([
      { role: 'user', content: 'Explain Mixture-of-Experts (MoE) architecture in simple terms' }
    ]);
    logger.info('Received technical response', {
      hasContent: !!response2.message?.content,
      questionType: 'technical',
    });

  } catch (error: any) {
    logger.error('Simple chat example failed', error);
  }
}

simpleChat();
