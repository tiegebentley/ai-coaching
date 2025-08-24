-- AI Coaching Management System - Initial Schema
-- Migration: 001_initial_schema.sql
-- Description: Create core tables with pgvector extension for AI coaching system

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create custom types for better type safety
CREATE TYPE user_role AS ENUM ('admin', 'coach', 'assistant');
CREATE TYPE email_category AS ENUM (
    'schedule_request',
    'payment_inquiry', 
    'absence_notice',
    'general_question',
    'complaint',
    'feedback',
    'emergency',
    'other'
);
CREATE TYPE email_priority AS ENUM ('low', 'medium', 'high', 'urgent');
CREATE TYPE task_status AS ENUM ('pending', 'processing', 'completed', 'failed');
CREATE TYPE agent_type AS ENUM ('email_processing', 'schedule_optimization', 'knowledge_base', 'orchestrator');

-- Users table for authentication and role management
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'assistant',
    password_hash VARCHAR(255), -- For local auth, can be null for OAuth
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Knowledge base table with vector embeddings for AI context
CREATE TABLE knowledge_base (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    source_url TEXT,
    category VARCHAR(100) NOT NULL,
    tags TEXT[], -- Array of tags for flexible categorization
    relevance_score DECIMAL(3,2) DEFAULT 0.0, -- 0.0 to 1.0 relevance score
    embedding VECTOR(1536), -- OpenAI text-embedding-ada-002 dimensions
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Email processing and logging table
CREATE TABLE email_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thread_id VARCHAR(255) NOT NULL,
    message_id VARCHAR(255) UNIQUE NOT NULL,
    subject TEXT NOT NULL,
    sender_name VARCHAR(255),
    sender_email VARCHAR(255) NOT NULL,
    recipient_email VARCHAR(255) NOT NULL,
    body_text TEXT,
    body_html TEXT,
    category email_category DEFAULT 'other',
    priority email_priority DEFAULT 'medium',
    confidence_score DECIMAL(3,2), -- AI classification confidence
    ai_summary TEXT,
    ai_draft_response TEXT,
    is_processed BOOLEAN DEFAULT false,
    is_approved BOOLEAN DEFAULT false,
    is_sent BOOLEAN DEFAULT false,
    processed_by UUID REFERENCES users(id),
    processed_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- System configuration and settings
CREATE TABLE system_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(255) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    is_sensitive BOOLEAN DEFAULT false, -- For sensitive config like API keys
    updated_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Task queue for asynchronous processing
CREATE TABLE task_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_type VARCHAR(100) NOT NULL,
    agent_type agent_type NOT NULL,
    payload JSONB NOT NULL,
    status task_status DEFAULT 'pending',
    priority INTEGER DEFAULT 5, -- 1-10 priority scale
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    error_message TEXT,
    result JSONB,
    scheduled_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Agent activity logging for monitoring and analytics
CREATE TABLE agent_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_type agent_type NOT NULL,
    task_id UUID REFERENCES task_queue(id),
    action VARCHAR(100) NOT NULL,
    details JSONB,
    execution_time_ms INTEGER,
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance optimization
-- Users
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_active ON users(is_active);

-- Knowledge base with vector similarity search
CREATE INDEX idx_knowledge_base_category ON knowledge_base(category);
CREATE INDEX idx_knowledge_base_tags ON knowledge_base USING GIN(tags);
CREATE INDEX idx_knowledge_base_embedding ON knowledge_base USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100); -- Adjust lists based on data volume

-- Email logs
CREATE INDEX idx_email_logs_thread ON email_logs(thread_id);
CREATE INDEX idx_email_logs_sender ON email_logs(sender_email);
CREATE INDEX idx_email_logs_category ON email_logs(category);
CREATE INDEX idx_email_logs_priority ON email_logs(priority);
CREATE INDEX idx_email_logs_processed ON email_logs(is_processed);
CREATE INDEX idx_email_logs_received ON email_logs(received_at);

-- System config
CREATE INDEX idx_system_config_key ON system_config(key);

-- Task queue
CREATE INDEX idx_task_queue_status ON task_queue(status);
CREATE INDEX idx_task_queue_agent ON task_queue(agent_type);
CREATE INDEX idx_task_queue_priority ON task_queue(priority, scheduled_at);
CREATE INDEX idx_task_queue_scheduled ON task_queue(scheduled_at) WHERE status = 'pending';

-- Agent logs
CREATE INDEX idx_agent_logs_type ON agent_logs(agent_type);
CREATE INDEX idx_agent_logs_task ON agent_logs(task_id);
CREATE INDEX idx_agent_logs_created ON agent_logs(created_at);

-- Row Level Security (RLS) policies for multi-tenant security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_base ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_logs ENABLE ROW LEVEL SECURITY;

-- RLS Policies for users table
CREATE POLICY users_select_policy ON users FOR SELECT
    USING (auth.uid() = id OR EXISTS (
        SELECT 1 FROM users WHERE id = auth.uid() AND role IN ('admin', 'coach')
    ));

CREATE POLICY users_update_policy ON users FOR UPDATE
    USING (auth.uid() = id OR EXISTS (
        SELECT 1 FROM users WHERE id = auth.uid() AND role = 'admin'
    ));

-- RLS Policies for knowledge_base (readable by all authenticated users)
CREATE POLICY knowledge_base_select_policy ON knowledge_base FOR SELECT
    USING (auth.role() = 'authenticated');

CREATE POLICY knowledge_base_insert_policy ON knowledge_base FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM users WHERE id = auth.uid() AND role IN ('admin', 'coach')
    ));

-- RLS Policies for email_logs (accessible based on role)
CREATE POLICY email_logs_select_policy ON email_logs FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM users WHERE id = auth.uid() AND is_active = true
    ));

CREATE POLICY email_logs_insert_policy ON email_logs FOR INSERT
    WITH CHECK (auth.role() = 'service_role' OR EXISTS (
        SELECT 1 FROM users WHERE id = auth.uid() AND role IN ('admin', 'coach', 'assistant')
    ));

-- RLS Policies for system_config (admin only for sensitive configs)
CREATE POLICY system_config_select_policy ON system_config FOR SELECT
    USING (
        NOT is_sensitive OR EXISTS (
            SELECT 1 FROM users WHERE id = auth.uid() AND role = 'admin'
        )
    );

CREATE POLICY system_config_modify_policy ON system_config FOR ALL
    USING (EXISTS (
        SELECT 1 FROM users WHERE id = auth.uid() AND role = 'admin'
    ));

-- Functions for updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add updated_at triggers to all tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_knowledge_base_updated_at BEFORE UPDATE ON knowledge_base
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_email_logs_updated_at BEFORE UPDATE ON email_logs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_task_queue_updated_at BEFORE UPDATE ON task_queue
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert initial system admin user (password should be changed immediately)
INSERT INTO users (email, name, role, password_hash) VALUES 
('admin@aicoaching.system', 'System Administrator', 'admin', '$2b$12$placeholder_hash_change_immediately');

-- Insert initial system configuration
INSERT INTO system_config (key, value, description) VALUES 
('app_version', '"1.0.0"', 'Application version'),
('max_email_processing_batch', '10', 'Maximum emails to process in one batch'),
('ai_confidence_threshold', '0.8', 'Minimum confidence score for auto-approval'),
('vector_similarity_threshold', '0.7', 'Minimum similarity for knowledge base matches'),
('rate_limit_openai_rpm', '3000', 'OpenAI API rate limit requests per minute'),
('rate_limit_airtable_rps', '5', 'Airtable API rate limit requests per second');

-- Create materialized view for email processing analytics
CREATE MATERIALIZED VIEW email_processing_stats AS
SELECT 
    DATE_TRUNC('day', received_at) as date,
    category,
    priority,
    COUNT(*) as total_emails,
    COUNT(*) FILTER (WHERE is_processed = true) as processed_emails,
    COUNT(*) FILTER (WHERE is_approved = true) as approved_emails,
    COUNT(*) FILTER (WHERE is_sent = true) as sent_emails,
    AVG(confidence_score) as avg_confidence,
    AVG(EXTRACT(EPOCH FROM (processed_at - received_at))/60) as avg_processing_minutes
FROM email_logs 
WHERE received_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', received_at), category, priority
ORDER BY date DESC, category, priority;

-- Index for the materialized view
CREATE INDEX idx_email_stats_date ON email_processing_stats(date);
CREATE INDEX idx_email_stats_category ON email_processing_stats(category);

-- Function to refresh analytics (should be called by cron job)
CREATE OR REPLACE FUNCTION refresh_email_stats()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY email_processing_stats;
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE users IS 'User authentication and role management';
COMMENT ON TABLE knowledge_base IS 'Vector-based knowledge storage for AI context';
COMMENT ON TABLE email_logs IS 'Email processing history and AI responses';
COMMENT ON TABLE system_config IS 'Application configuration and settings';
COMMENT ON TABLE task_queue IS 'Asynchronous task processing queue';
COMMENT ON TABLE agent_logs IS 'AI agent activity monitoring and analytics';

COMMENT ON COLUMN knowledge_base.embedding IS 'OpenAI text-embedding-ada-002 vector (1536 dimensions)';
COMMENT ON COLUMN email_logs.confidence_score IS 'AI classification confidence (0.0-1.0)';
COMMENT ON COLUMN task_queue.priority IS 'Task priority (1=highest, 10=lowest)';

-- Migration completed
INSERT INTO system_config (key, value, description) VALUES 
('migration_version', '"001"', 'Current database migration version'),
('migration_applied_at', to_jsonb(NOW()), 'When the migration was applied');

-- Grant necessary permissions for the application user
-- Note: Adjust these grants based on your actual Supabase service role configuration
GRANT USAGE ON SCHEMA public TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO service_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;