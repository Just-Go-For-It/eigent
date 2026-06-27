FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app

COPY pyproject.toml ./
COPY src ./src
COPY mcp.json ./

# Install with the "live" extra (broker + api + worker + llm). Add others as needed.
RUN pip install --no-cache-dir ".[live]" || pip install --no-cache-dir pandas numpy python-dotenv

# Default: run the always-on worker (the trading brain). Override for the API service.
CMD ["python", "-m", "src.worker"]
