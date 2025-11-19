-- 1. Create CONVERSATIONS Table
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Foreign Key: Links to the 'id' column in the 'users' table
    -- ON DELETE CASCADE: If user #1 is deleted, all their chats are deleted automatically.
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Session Grouping: Used to group messages in the UI
    session_id UUID NOT NULL,
    
    -- The Content
    user_message TEXT NOT NULL,
    ai_message TEXT NOT NULL,
    
    -- RAG Context: Stores what the AI read to generate the answer
    retrieval_context JSONB DEFAULT '[]',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Create Indexes for speed
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created ON conversations(created_at);