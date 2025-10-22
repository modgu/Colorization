# Use a lightweight Python base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies for OpenCV and Git LFS
RUN apt-get update && apt-get install -y \
    git \
    git-lfs \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    && git lfs install \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Make sure LFS files are fetched (your model weights)
RUN git lfs pull

# Expose port for Railway
EXPOSE 8080

# Start Flask app with Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:8080", "main:app"]
