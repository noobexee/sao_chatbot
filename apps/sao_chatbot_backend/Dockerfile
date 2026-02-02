FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    libopenblas-dev \
    libomp-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH="/app"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x scripts/run_app.sh

EXPOSE 8000

CMD ["./scripts/run_app.sh"]