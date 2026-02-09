#!/bin/sh

if [ ! -f "/app/storage/faiss_index/index.faiss" ]; then
    echo "FAISS index not found in storage. Ingesting Data..."
    python scripts/ingest_data.py
else
    echo "Found persistent FAISS index in storage. Skipping ingestion."
fi

echo "Starting FastAPI Server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000