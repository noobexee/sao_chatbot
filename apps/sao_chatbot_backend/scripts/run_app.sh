#!/bin/sh

echo "Ingesting Data into FAISS"
python scripts/ingest_data.py

if [ $? -eq 0 ]; then
    echo "Step 2: Starting FastAPI Serve"
    exec uvicorn main:app --host 0.0.0.0 --port 8000
else
    echo "Ingestion failed! Blocking server start."
    exit 1
fi