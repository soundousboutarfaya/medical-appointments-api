FROM python:3.13-slim

# Avoid .pyc files and force unbuffered stdout/stderr (better logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create the data directory (used by the mounted volume) and run as non-root
RUN mkdir -p /app/data && useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Render and most platforms inject $PORT; default to 8000 locally
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
