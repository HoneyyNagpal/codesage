-- CodeSage Database Schema

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    github_id VARCHAR(255) UNIQUE,
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    avatar_url TEXT,
    access_token TEXT,
    refresh_token TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Repositories table
CREATE TABLE repositories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    github_id VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    full_name VARCHAR(512) NOT NULL,
    url TEXT NOT NULL,
    clone_url TEXT,
    default_branch VARCHAR(100) DEFAULT 'main',
    language VARCHAR(100),
    stars INTEGER DEFAULT 0,
    is_private BOOLEAN DEFAULT false,
    last_analyzed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, full_name)
);

-- Analyses table
CREATE TABLE analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
    commit_sha VARCHAR(40),
    branch VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending', -- pending, processing, completed, failed
    quality_score DECIMAL(5,2),
    maintainability_index DECIMAL(5,2),
    technical_debt_ratio DECIMAL(5,2),
    complexity_score DECIMAL(10,2),
    security_rating VARCHAR(10),
    files_analyzed INTEGER DEFAULT 0,
    issues_found INTEGER DEFAULT 0,
    lines_of_code INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Issues table
CREATE TABLE issues (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id UUID REFERENCES analyses(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    line_number INTEGER,
    end_line_number INTEGER,
    column_number INTEGER,
    severity VARCHAR(20) NOT NULL, -- critical, high, medium, low, info
    category VARCHAR(100) NOT NULL, -- complexity, security, performance, maintainability, style
    rule_id VARCHAR(100),
    title VARCHAR(512) NOT NULL,
    description TEXT,
    code_snippet TEXT,
    suggestion TEXT,
    llm_explanation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Metrics table
CREATE TABLE metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id UUID REFERENCES analyses(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    metric_type VARCHAR(100) NOT NULL, -- cyclomatic_complexity, cognitive_complexity, lines_of_code, etc.
    value DECIMAL(10,2) NOT NULL,
    threshold DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Architecture Insights table
CREATE TABLE architecture_insights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id UUID REFERENCES analyses(id) ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL, -- patterns, anti_patterns, dependencies, modularity
    title VARCHAR(512) NOT NULL,
    description TEXT NOT NULL,
    severity VARCHAR(20),
    affected_files TEXT[], -- Array of file paths
    recommendation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Refactoring Suggestions table
CREATE TABLE refactoring_suggestions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    issue_id UUID REFERENCES issues(id) ON DELETE CASCADE,
    analysis_id UUID REFERENCES analyses(id) ON DELETE CASCADE,
    type VARCHAR(100) NOT NULL, -- extract_method, reduce_complexity, improve_naming, etc.
    title VARCHAR(512) NOT NULL,
    description TEXT NOT NULL,
    before_code TEXT,
    after_code TEXT,
    impact VARCHAR(20), -- high, medium, low
    effort VARCHAR(20), -- high, medium, low
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- GitHub Webhooks table
CREATE TABLE github_webhooks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
    webhook_id VARCHAR(255),
    event_type VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Analysis Queue table (for tracking background jobs)
CREATE TABLE analysis_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
    analysis_id UUID REFERENCES analyses(id) ON DELETE SET NULL,
    job_id VARCHAR(255),
    priority INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'queued', -- queued, processing, completed, failed
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- File Cache table (for incremental analysis)
CREATE TABLE file_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    file_hash VARCHAR(64) NOT NULL, -- SHA-256 hash
    last_analysis_id UUID REFERENCES analyses(id) ON DELETE SET NULL,
    cached_results JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(repository_id, file_path)
);

-- Settings table
CREATE TABLE settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key VARCHAR(255) NOT NULL,
    value JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, key)
);

-- Indexes for performance
CREATE INDEX idx_repositories_user_id ON repositories(user_id);
CREATE INDEX idx_analyses_repository_id ON analyses(repository_id);
CREATE INDEX idx_analyses_status ON analyses(status);
CREATE INDEX idx_issues_analysis_id ON issues(analysis_id);
CREATE INDEX idx_issues_severity ON issues(severity);
CREATE INDEX idx_metrics_analysis_id ON metrics(analysis_id);
CREATE INDEX idx_architecture_insights_analysis_id ON architecture_insights(analysis_id);
CREATE INDEX idx_refactoring_suggestions_analysis_id ON refactoring_suggestions(analysis_id);
CREATE INDEX idx_file_cache_repository_id ON file_cache(repository_id);
CREATE INDEX idx_file_cache_hash ON file_cache(file_hash);

-- Triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_repositories_updated_at BEFORE UPDATE ON repositories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_analyses_updated_at BEFORE UPDATE ON analyses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_github_webhooks_updated_at BEFORE UPDATE ON github_webhooks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_analysis_queue_updated_at BEFORE UPDATE ON analysis_queue
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_file_cache_updated_at BEFORE UPDATE ON file_cache
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_settings_updated_at BEFORE UPDATE ON settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();