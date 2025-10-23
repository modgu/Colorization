# Use a stable, lightweight Python base image
FROM python:3.12-slim-bookworm

# Set working directory inside the container
WORKDIR /app

# Install system dependencies for OpenCV, PyTorch, and Git
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency list and install Python packages
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files into the container
COPY . .

# Ensure that the Railway volume mount directory exists
RUN mkdir -p /mnt/data

# Expose port 8080 (Railway’s default web port)
EXPOSE 8080

# Start Flask app with Gunicorn (production-ready server)
CMD ["gunicorn", "-b", "0.0.0.0:8080", "main:app"]
