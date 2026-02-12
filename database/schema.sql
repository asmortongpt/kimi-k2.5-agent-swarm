-- ============================================================================
-- Kimi K2.5 Agent Swarm - Production Database Schema
-- PostgreSQL 14+
-- ============================================================================
-- Security: All queries MUST use parameterized statements ($1, $2, etc.)
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================================================
-- Core Tables
-- ============================================================================

-- Agents table - stores agent instances
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    agent_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'idle', -- idle, active, busy, error, terminated
    capabilities JSONB NOT NULL DEFAULT '[]',
    config JSONB NOT NULL DEFAULT '{}',
    parent_agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    swarm_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_agents_swarm_id ON agents(swarm_id);
CREATE INDEX idx_agents_parent_id ON agents(parent_agent_id);
CREATE INDEX idx_agents_type ON agents(agent_type);

-- Tasks table - stores task assignments and execution
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    task_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, assigned, in_progress, completed, failed, cancelled
    priority INTEGER DEFAULT 5, -- 1-10, higher is more urgent
    assigned_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    parent_task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    swarm_id UUID,
    input_data JSONB DEFAULT '{}',
    output_data JSONB DEFAULT '{}',
    error_info JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deadline TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_agent_id ON tasks(assigned_agent_id);
CREATE INDEX idx_tasks_swarm_id ON tasks(swarm_id);
CREATE INDEX idx_tasks_priority ON tasks(priority DESC);
CREATE INDEX idx_tasks_parent_id ON tasks(parent_task_id);

-- Conversations table - stores chat interactions
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    session_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL, -- user, assistant, system, tool
    content TEXT NOT NULL,
    tool_calls JSONB,
    tool_results JSONB,
    tokens_used INTEGER,
    model VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_conversations_agent_id ON conversations(agent_id);
CREATE INDEX idx_conversations_session_id ON conversations(session_id);
CREATE INDEX idx_conversations_created_at ON conversations(created_at DESC);

-- Knowledge base table - stores documents for RAG
CREATE TABLE knowledge_base (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id VARCHAR(500) UNIQUE NOT NULL,
    title VARCHAR(1000),
    content TEXT NOT NULL,
    content_type VARCHAR(100) DEFAULT 'text/plain',
    source VARCHAR(500),
    category VARCHAR(100),
    tags TEXT[],
    embedding vector(1536), -- OpenAI ada-002 dimension
    embedding_model VARCHAR(100) DEFAULT 'text-embedding-ada-002',
    chunk_index INTEGER DEFAULT 0,
    parent_doc_id VARCHAR(500),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    indexed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_knowledge_doc_id ON knowledge_base(document_id);
CREATE INDEX idx_knowledge_category ON knowledge_base(category);
CREATE INDEX idx_knowledge_source ON knowledge_base(source);
CREATE INDEX idx_knowledge_embedding ON knowledge_base USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_knowledge_tags ON knowledge_base USING gin(tags);

-- Training data table - stores agent learning examples
CREATE TABLE training_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    input_example TEXT NOT NULL,
    output_example TEXT NOT NULL,
    feedback_score DECIMAL(3, 2), -- 0.00 - 1.00
    feedback_text TEXT,
    success BOOLEAN NOT NULL,
    execution_time_ms INTEGER,
    tokens_used INTEGER,
    error_info JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_training_agent_id ON training_data(agent_id);
CREATE INDEX idx_training_task_id ON training_data(task_id);
CREATE INDEX idx_training_success ON training_data(success);
CREATE INDEX idx_training_score ON training_data(feedback_score DESC);

-- Agent metrics table - stores performance metrics
CREATE TABLE agent_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    metric_type VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15, 4) NOT NULL,
    unit VARCHAR(50),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    aggregation_period VARCHAR(50), -- second, minute, hour, day
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_metrics_agent_id ON agent_metrics(agent_id);
CREATE INDEX idx_metrics_type ON agent_metrics(metric_type);
CREATE INDEX idx_metrics_timestamp ON agent_metrics(timestamp DESC);

-- Tool executions table - tracks MCP tool usage
CREATE TABLE tool_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    tool_name VARCHAR(255) NOT NULL,
    tool_type VARCHAR(100) NOT NULL,
    parameters JSONB NOT NULL,
    result JSONB,
    success BOOLEAN NOT NULL,
    execution_time_ms INTEGER,
    error_info JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_tool_exec_agent_id ON tool_executions(agent_id);
CREATE INDEX idx_tool_exec_task_id ON tool_executions(task_id);
CREATE INDEX idx_tool_exec_name ON tool_executions(tool_name);
CREATE INDEX idx_tool_exec_success ON tool_executions(success);

-- Swarms table - tracks agent swarm instances
CREATE TABLE swarms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    coordinator_agent_id UUID REFERENCES agents(id),
    max_agents INTEGER DEFAULT 100,
    current_agent_count INTEGER DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'initializing',
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_swarms_status ON swarms(status);
CREATE INDEX idx_swarms_coordinator ON swarms(coordinator_agent_id);

-- ============================================================================
-- Functions and Triggers
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $body$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$body$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_knowledge_base_updated_at BEFORE UPDATE ON knowledge_base
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate task duration
CREATE OR REPLACE FUNCTION calculate_task_duration(task_id UUID)
RETURNS INTERVAL AS $body$
DECLARE
    duration INTERVAL;
BEGIN
    SELECT completed_at - started_at INTO duration
    FROM tasks
    WHERE id = $1;
    RETURN duration;
END;
$body$ LANGUAGE plpgsql;

-- Function to get agent workload
CREATE OR REPLACE FUNCTION get_agent_workload(agent_id_param UUID)
RETURNS INTEGER AS $body$
BEGIN
    RETURN (
        SELECT COUNT(*)
        FROM tasks
        WHERE assigned_agent_id = agent_id_param
        AND status IN ('assigned', 'in_progress')
    );
END;
$body$ LANGUAGE plpgsql;

-- Function to get average task completion time by agent
CREATE OR REPLACE FUNCTION get_agent_avg_completion_time(agent_id_param UUID)
RETURNS INTERVAL AS $body$
BEGIN
    RETURN (
        SELECT AVG(completed_at - started_at)
        FROM tasks
        WHERE assigned_agent_id = agent_id_param
        AND status = 'completed'
        AND completed_at IS NOT NULL
        AND started_at IS NOT NULL
    );
END;
$body$ LANGUAGE plpgsql;

-- ============================================================================
-- Views
-- ============================================================================

-- Active agents view
CREATE OR REPLACE VIEW v_active_agents AS
SELECT
    a.id,
    a.name,
    a.agent_type,
    a.status,
    a.swarm_id,
    COUNT(t.id) as active_tasks,
    a.last_active_at,
    a.created_at
FROM agents a
LEFT JOIN tasks t ON a.id = t.assigned_agent_id AND t.status IN ('assigned', 'in_progress')
WHERE a.status IN ('active', 'busy')
GROUP BY a.id, a.name, a.agent_type, a.status, a.swarm_id, a.last_active_at, a.created_at;

-- Task statistics view
CREATE OR REPLACE VIEW v_task_statistics AS
SELECT
    status,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration_seconds,
    MIN(created_at) as oldest_created,
    MAX(created_at) as newest_created
FROM tasks
GROUP BY status;

-- Agent performance view
CREATE OR REPLACE VIEW v_agent_performance AS
SELECT
    a.id,
    a.name,
    a.agent_type,
    COUNT(t.id) as total_tasks,
    COUNT(CASE WHEN t.status = 'completed' THEN 1 END) as completed_tasks,
    COUNT(CASE WHEN t.status = 'failed' THEN 1 END) as failed_tasks,
    AVG(EXTRACT(EPOCH FROM (t.completed_at - t.started_at))) as avg_task_duration_seconds,
    SUM(COALESCE((td.feedback_score * 100)::INTEGER, 0)) / NULLIF(COUNT(td.id), 0) as avg_feedback_score
FROM agents a
LEFT JOIN tasks t ON a.id = t.assigned_agent_id
LEFT JOIN training_data td ON t.id = td.task_id
GROUP BY a.id, a.name, a.agent_type;

-- ============================================================================
-- Security - Row Level Security (RLS)
-- ============================================================================

-- Enable RLS on sensitive tables
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_base ENABLE ROW LEVEL SECURITY;
ALTER TABLE training_data ENABLE ROW LEVEL SECURITY;

-- Create policies (examples - adjust based on your auth system)
-- Note: In production, you would create specific roles and policies

-- ============================================================================
-- Sample Indexes for Performance
-- ============================================================================

-- Composite indexes for common queries
CREATE INDEX idx_tasks_status_priority ON tasks(status, priority DESC);
CREATE INDEX idx_tasks_agent_status ON tasks(assigned_agent_id, status);
CREATE INDEX idx_conversations_agent_session ON conversations(agent_id, session_id);
CREATE INDEX idx_training_agent_success ON training_data(agent_id, success);

-- ============================================================================
-- Initial Data (Optional)
-- ============================================================================

-- Insert system agent (coordinator)
INSERT INTO agents (id, name, agent_type, status, capabilities, config)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'System Coordinator',
    'coordinator',
    'active',
    '["task_distribution", "agent_spawning", "swarm_management"]'::jsonb,
    '{"max_child_agents": 100, "auto_scale": true}'::jsonb
);

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON TABLE agents IS 'Stores agent instances with their configuration and status';
COMMENT ON TABLE tasks IS 'Stores tasks assigned to agents with execution tracking';
COMMENT ON TABLE conversations IS 'Stores chat message history for all agents';
COMMENT ON TABLE knowledge_base IS 'Vector store for RAG with embeddings';
COMMENT ON TABLE training_data IS 'Stores examples for agent learning and improvement';
COMMENT ON TABLE agent_metrics IS 'Time-series metrics for agent performance monitoring';
COMMENT ON TABLE tool_executions IS 'Tracks MCP tool usage and results';
COMMENT ON TABLE swarms IS 'Tracks multi-agent swarm instances';

COMMENT ON COLUMN knowledge_base.embedding IS 'Vector embedding (1536-dim for OpenAI ada-002)';
COMMENT ON COLUMN tasks.priority IS 'Task priority 1-10, higher is more urgent';
COMMENT ON COLUMN training_data.feedback_score IS 'Feedback score 0.00-1.00';
