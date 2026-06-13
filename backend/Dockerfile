FROM python:3.11-slim

WORKDIR /app

# No build dependencies needed since python packages have precompiled wheels

# Copy requirements from root context
COPY requirements.txt .

# Install dependencies with increased timeout for network robustness
RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# Copy the entire workspace
COPY . .

# Set pythonpath and disable stdout buffering
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose backend port
EXPOSE 8000

# Run the backend server
CMD ["python", "backend/server.py"]

