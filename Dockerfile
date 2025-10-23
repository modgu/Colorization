# Use a lightweight Python base image
FROM python:3.12-slim

WORKDIR /app

# Install Git + Git LFS + system dependencies for OpenCV
RUN apt-get update && apt-get install -y \
    git git-lfs libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Enable Git LFS
RUN git lfs install

# Clone your repo manually WITH LFS
RUN git clone https://github.com/yourusername/yourrepo.git . && git lfs pull

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080
CMD ["gunicorn", "-b", "0.0.0.0:8080", "main:app"]
