FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (needed for compiling certain packages if necessary)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application files
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Run alembic migrations and start Uvicorn production server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
