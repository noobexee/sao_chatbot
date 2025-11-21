CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    session_id UUID NOT NULL,
    
    user_message TEXT NOT NULL,
    ai_message TEXT NOT NULL,
    
    retrieval_context JSONB DEFAULT '[]',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created ON conversations(created_at);