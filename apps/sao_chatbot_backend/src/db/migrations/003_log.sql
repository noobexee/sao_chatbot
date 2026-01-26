-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. InitialReview Sessions Table (Optional but recommended for linking logs to specific files/sessions)
-- This helps if you want to track which file was uploaded for a specific InitialReview_id
CREATE TABLE IF NOT EXISTS InitialReview_sessions (
    InitialReview_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INTEGER, -- Link to your existing users table if needed
    file_name TEXT,  
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    file_data BYTEA
);

-- 2. InitialReview Feedback Logs Table
-- Stores the specific feedback interactions (Thumb Up/Down, Edits)
CREATE TABLE IF NOT EXISTS InitialReview_feedback_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- InitialReview_id: Links to the session. If you don't use the table above, just keep this as UUID or TEXT.
    InitialReview_id UUID NOT NULL, 
    
    -- criteria_id: The criteria number (e.g., 4, 6)
    criteria_id INTEGER NOT NULL,
    
    -- timestamp: When the feedback occurred
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- field_type: Specific field being edited (e.g., 'date', 'entity') or 'overall_result' for thumbs
    field_type VARCHAR(50) NOT NULL,
    
    -- ai_value: The original value returned by the AI
    ai_value TEXT,
    
    -- user_edit: Boolean flag (0 = No/Thumb Only, 1 = Yes/Text Edit)
    user_edit BOOLEAN DEFAULT FALSE,
    
    -- user_value: The new value entered by the user (if edited)
    user_value TEXT,
    
    -- result_correct: Feedback status ('up', 'down', or NULL if just an edit without explicit rating)
    result_correct BOOLEAN DEFAULT FALSE
);

-- Create indexes for faster querying (analytics)
CREATE INDEX IF NOT EXISTS idx_InitialReview_logs_InitialReview_id ON InitialReview_feedback_logs(InitialReview_id);
CREATE INDEX IF NOT EXISTS idx_InitialReview_logs_criteria ON InitialReview_feedback_logs(criteria_id);
CREATE INDEX IF NOT EXISTS idx_InitialReview_logs_created_at ON InitialReview_feedback_logs(created_at);