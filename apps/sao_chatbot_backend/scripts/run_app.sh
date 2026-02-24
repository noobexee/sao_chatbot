#!/bin/sh

# Check if BOTH indexes exist. If either one is missing, trigger ingestion.
if [ ! -f "/app/storage/regulations/index.faiss" ] || [ ! -f "/app/storage/others/index.faiss" ]; then
    echo "FAISS indexes not found in storage. Ingesting Data..."
    python scripts/ingest_data.py
else
    echo "Found persistent FAISS indexes in storage. Skipping ingestion."
fi

echo "Starting FastAPI Server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000