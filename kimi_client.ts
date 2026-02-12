/**
 * Kimi K2.5 TypeScript Client with Agent Swarm Support
 * Supports: Moonshot AI API, Ollama, Together AI
 */

import axios, { AxiosInstance } from 'axios';
import * as dotenv from 'dotenv';
import { createComponentLogger, ErrorCode } from './lib/logger';

dotenv.config();

const logger = createComponentLogger('KimiClient');

export enum ProviderType {
  MOONSHOT = 'moonshot',
  OLLAMA = 'ollama',
  TOGETHER = 'together'
}

export interface AgentSwarmConfig {
  maxAgents: number;
  parallelExecution: boolean;
  timeout: number;
  enableThinkingMode: boolean;
}

export interface Message {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface ChatOptions {
  temperature?: number;
  maxTokens?: number;
  stream?: boolean;
  enableSwarm?: boolean;
}

export interface AgentSwarmTaskOptions {
  context?: Record<string, any>;
  maxAgents?: number;
}

export class KimiClient {
  private provider: ProviderType;
  private apiKey: string | null;
  private baseUrl: string;
  private model: string;
  private swarmConfig: AgentSwarmConfig;
  private client: AxiosInstance;

  constructor(
    provider: ProviderType = ProviderType.OLLAMA,
    apiKey?: string,
    baseUrl?: string,
    model: string = 'kimi-k2.5',
    swarmConfig?: Partial<AgentSwarmConfig>
  ) {
    this.provider = provider;
    this.model = model;
    this.swarmConfig = {
      maxAgents: 100,
      parallelExecution: true,
      timeout: 300000,
      enableThinkingMode: true,
      ...swarmConfig
    };

    // Configure based on provider
    switch (provider) {
      case ProviderType.MOONSHOT:
        this.apiKey = apiKey || process.env.MOONSHOT_API_KEY || null;
        this.baseUrl = baseUrl || process.env.MOONSHOT_API_BASE || 'https://api.moonshot.cn/v1';
        break;
      case ProviderType.OLLAMA:
        this.apiKey = null;
        this.baseUrl = baseUrl || process.env.OLLAMA_HOST || 'http://localhost:11434';
        this.model = process.env.OLLAMA_MODEL || 'kimi-k2.5:cloud';
        break;
      case ProviderType.TOGETHER:
        this.apiKey = apiKey || process.env.TOGETHER_API_KEY || null;
        this.baseUrl = 'https://api.together.xyz/v1';
        break;
    }

    this.client = axios.create({
      timeout: this.swarmConfig.timeout
    });
  }

  async chat(
    messages: Message[],
    options: ChatOptions = {}
  ): Promise<any> {
    const {
      temperature = 0.7,
      maxTokens = 4096,
      stream = false,
      enableSwarm = true
    } = options;

    if (this.provider === ProviderType.OLLAMA) {
      return this.chatOllama(messages, temperature, maxTokens, stream);
    } else {
      return this.chatOpenAICompatible(
        messages,
        temperature,
        maxTokens,
        stream,
        enableSwarm
      );
    }
  }

  private async chatOllama(
    messages: Message[],
    temperature: number,
    maxTokens: number,
    stream: boolean
  ): Promise<any> {
    const url = `${this.baseUrl}/api/chat`;

    const payload = {
      model: this.model,
      messages,
      stream,
      options: {
        temperature,
        num_predict: maxTokens
      }
    };

    const response = await this.client.post(url, payload);
    return response.data;
  }

  private async chatOpenAICompatible(
    messages: Message[],
    temperature: number,
    maxTokens: number,
    stream: boolean,
    enableSwarm: boolean
  ): Promise<any> {
    const url = `${this.baseUrl}/chat/completions`;

    const headers: Record<string, string> = {
      'Authorization': `Bearer ${this.apiKey}`,
      'Content-Type': 'application/json'
    };

    const payload: any = {
      model: this.model,
      messages,
      temperature,
      max_tokens: maxTokens,
      stream
    };

    // Add agent swarm configuration if enabled
    if (enableSwarm) {
      payload.agent_swarm = {
        enabled: true,
        max_agents: this.swarmConfig.maxAgents,
        parallel_execution: this.swarmConfig.parallelExecution
      };
    }

    const response = await this.client.post(url, payload, { headers });
    return response.data;
  }

  async agentSwarmTask(
    task: string,
    options: AgentSwarmTaskOptions = {}
  ): Promise<any> {
    const { context, maxAgents } = options;

    const systemMessage: Message = {
      role: 'system',
      content: `You are Kimi K2.5 with agent swarm capabilities.

For this task, you should:
1. Analyze the complexity and break it into parallelizable subtasks
2. Spawn specialized agents for each subtask
3. Coordinate their execution
4. Synthesize results into a comprehensive response

Max agents: ${maxAgents || this.swarmConfig.maxAgents}
Parallel execution: ${this.swarmConfig.parallelExecution}`
    };

    let userContent = task;
    if (context) {
      userContent += `\n\nContext: ${JSON.stringify(context, null, 2)}`;
    }

    const userMessage: Message = {
      role: 'user',
      content: userContent
    };

    return this.chat(
      [systemMessage, userMessage],
      {
        enableSwarm: true,
        maxTokens: 8192
      }
    );
  }
}

// Example usage
async function main() {
  // Example 1: Simple chat with Ollama
  logger.info('Starting Example 1: Simple Chat (Ollama)');

  const client = new KimiClient(ProviderType.OLLAMA);

  try {
    const response = await client.chat([
      { role: 'user', content: 'Explain quantum computing in simple terms' }
    ]);
    logger.info('Received response from chat', {
      hasContent: !!response.message?.content,
      responseType: typeof response,
    });

    // Example 2: Agent Swarm for complex research
    logger.info('Starting Example 2: Agent Swarm - Multi-Domain Research');

    const swarmResponse = await client.agentSwarmTask(
      `Research the following topics and provide a comprehensive analysis:
      1. Current state of quantum computing hardware
      2. Threats to existing cryptographic systems
      3. Post-quantum cryptography solutions
      4. Timeline for industry adoption

      For each topic, provide technical details, challenges, and future outlook.`,
      {
        context: {
          depth: 'technical',
          targetAudience: 'security professionals'
        }
      }
    );
    logger.info('Swarm research completed', {
      success: true,
      hasResponse: !!swarmResponse,
    });

    // Example 3: Code analysis with agent swarm
    logger.info('Starting Example 3: Agent Swarm - Code Analysis');

    const codeSample = `
      def process_user_data(user_input):
          query = f"SELECT * FROM users WHERE username = '{user_input}'"
          return execute_query(query)
    `;

    const analysisResponse = await client.agentSwarmTask(
      `Analyze this code for:
      1. Security vulnerabilities
      2. Performance issues
      3. Best practice violations
      4. Suggested improvements

      Code:
      ${codeSample}`,
      { maxAgents: 10 }
    );
    logger.info('Code analysis completed', {
      success: true,
      hasResponse: !!analysisResponse,
    });

  } catch (error: any) {
    logger.error('Example execution failed', error, {
      hasResponse: !!error.response,
      statusCode: error.response?.status,
    });
  }
}

// Run if executed directly
if (require.main === module) {
  main();
}

export default KimiClient;
