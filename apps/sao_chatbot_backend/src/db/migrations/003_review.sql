CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE TABLE IF NOT EXISTS initial_review_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, 
    session_id UUID NOT NULL, 
    criteria_id INTEGER NOT NULL,
    field_type VARCHAR(100) NOT NULL,
    ai_value TEXT,
    user_edit BOOLEAN DEFAULT FALSE,
    user_value TEXT,
    result_correct BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_logs_user_session ON initial_review_logs(user_id, session_id);