FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Data directory for local SQLite (telegram_pending)
RUN mkdir -p /app/data

CMD ["python", "main.py", "avvia"]
