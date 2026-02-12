/**
 * Example 2: Agent Swarm Demo
 * Demonstrates agent swarm capabilities for complex multi-domain tasks
 */

import KimiClient, { ProviderType } from '../kimi_client';
import { createComponentLogger } from '../lib/logger';

const logger = createComponentLogger('AgentSwarmDemo');

async function agentSwarmDemo() {
  logger.info('Starting agent swarm demo');

  const client = new KimiClient(ProviderType.OLLAMA, undefined, undefined, 'kimi-k2.5:cloud', {
    maxAgents: 50,
    parallelExecution: true
  });

  try {
    // Example 1: Multi-domain technical research
    logger.info('Task 1: Multi-Domain Technical Research');

    const research = await client.agentSwarmTask(
      `Conduct comprehensive research on AI Agent Swarms:

      1. Technical Architecture
         - Core algorithms and coordination mechanisms
         - Communication protocols between agents
         - Resource allocation strategies

      2. Real-World Applications
         - Current production deployments
         - Success stories and case studies
         - ROI and performance metrics

      3. Implementation Challenges
         - Technical limitations
         - Scalability concerns
         - Security considerations

      4. Future Outlook
         - Emerging trends
         - Next-generation capabilities
         - Industry predictions for 2026-2027

      For each section, provide technical depth, cite specific examples, and include actionable insights.`,
      {
        context: {
          audience: 'technical architects',
          depth: 'expert',
          format: 'structured_report'
        },
        maxAgents: 20
      }
    );

    logger.info('Research task completed', {
      hasResults: !!(research.message?.content || research),
      maxAgents: 20,
    });

    // Example 2: Competitive analysis
    logger.info('Task 2: Competitive Analysis');

    const competitive = await client.agentSwarmTask(
      `Perform competitive analysis of top 5 AI agent frameworks:

      Analyze:
      1. AutoGPT
      2. LangChain Agents
      3. CrewAI
      4. Semantic Kernel
      5. Kimi K2.5 Agent Swarm

      For each framework, evaluate:
      - Architecture and design patterns
      - Agent coordination capabilities
      - Ease of use and developer experience
      - Performance and scalability
      - Community and ecosystem
      - Pricing and deployment costs
      - Best use cases

      Provide comparative scoring (1-10) and recommendations.`,
      {
        context: {
          purpose: 'technology selection',
          budget: 'enterprise',
          timeline: '6 months'
        },
        maxAgents: 15
      }
    );

    logger.info('Competitive analysis completed', {
      hasResults: !!(competitive.message?.content || competitive),
      maxAgents: 15,
    });

    // Example 3: Complex problem solving
    logger.info('Task 3: Complex Problem Solving');

    const problem = await client.agentSwarmTask(
      `Design a scalable architecture for a real-time fleet management system with:

      Requirements:
      - 10,000+ vehicles with GPS tracking
      - Real-time telemetry (OBD-II data)
      - Route optimization
      - Predictive maintenance
      - Driver safety monitoring
      - Fuel consumption analytics
      - Multi-tenant architecture
      - FedRAMP compliance

      Deliverables:
      1. System architecture diagram (textual description)
      2. Technology stack recommendations
      3. Database schema design
      4. API design
      5. Security architecture
      6. Scalability strategy
      7. Cost estimation
      8. Implementation roadmap (6-month timeline)

      Use agent swarm to parallelize: architecture design, security analysis,
      cost estimation, and implementation planning.`,
      {
        context: {
          scale: 'enterprise',
          compliance: ['FedRAMP', 'HIPAA'],
          budget: '$500K-$1M',
          team_size: 8
        },
        maxAgents: 30
      }
    );

    logger.info('Problem solving task completed', {
      hasResults: !!(problem.message?.content || problem),
      maxAgents: 30,
    });

  } catch (error: any) {
    logger.error('Agent swarm demo failed', error, {
      hasResponse: !!error.response,
      statusCode: error.response?.status,
    });
  }
}

agentSwarmDemo();
