FROM python:3.11-slim

WORKDIR /app

# No build dependencies needed since python packages have precompiled wheels

# Copy uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy requirements from root context
COPY requirements.txt .

# Install dependencies using uv for extremely fast and reliable resolution
RUN uv pip install --system -r requirements.txt

# Copy the entire workspace
COPY . .

# Set pythonpath and disable stdout buffering
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose backend port
EXPOSE 8008

# Run the backend server
CMD ["python", "backend/server.py"]

