CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,

    -- Core identity
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    version INTEGER NOT NULL,

    -- Dates
    announce_date DATE NOT NULL,
    effective_date DATE,

    -- Status & processing
    status TEXT NOT NULL DEFAULT 'queued',
    current_page INTEGER,
    total_pages INTEGER,
    pages INTEGER,

    -- Content
    pdf_file_name TEXT NOT NULL,
    pdf_file_data BYTEA NOT NULL,
    text_content TEXT,

    -- Metadata (source of truth)
    meta_json JSONB NOT NULL,

    -- Versioning flags
    is_latest BOOLEAN NOT NULL DEFAULT TRUE,
    is_snapshot BOOLEAN NOT NULL DEFAULT FALSE,

    -- Soft delete (recommended)
    deleted_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_files (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_data BYTEA NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_document_files_document
        FOREIGN KEY (document_id)
        REFERENCES documents(id)
        ON DELETE CASCADE
);

-- List documents
CREATE INDEX IF NOT EXISTS idx_documents_created_at
    ON documents (created_at DESC);

-- Filter latest versions
CREATE INDEX IF NOT EXISTS idx_documents_latest
    ON documents (type, title, is_latest)
    WHERE deleted_at IS NULL;

-- Status polling
CREATE INDEX IF NOT EXISTS idx_documents_status
    ON documents (status)
    WHERE deleted_at IS NULL;

-- Soft delete filter
CREATE INDEX IF NOT EXISTS idx_documents_not_deleted
    ON documents (id)
    WHERE deleted_at IS NULL;
