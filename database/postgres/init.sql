-- Initial setup SQL for Postgres
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Example table
CREATE TABLE IF NOT EXISTS example (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
