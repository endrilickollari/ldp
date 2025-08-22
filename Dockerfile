# Multi-stage build for React frontend and Python backend
# Stage 1: Build React frontend
FROM node:18-alpine AS frontend-build

# Set working directory for frontend
WORKDIR /frontend

# Copy package files
COPY ui/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY ui/ ./

# Build the React app
RUN npm run build

# Stage 2: Python backend with built frontend
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for OCR and document processing
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    poppler-utils \
    libglib2.0-0 \
    libgomp1 \
    libffi-dev \
    pkg-config \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libfreetype6-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies for monitoring
RUN pip install flower

# Copy application code
COPY . .

# Copy built React frontend from previous stage
COPY --from=frontend-build /frontend/build ./ui/build

# Create directories for uploads and logs
RUN mkdir -p uploads logs

# Initialize database with required tables and data
RUN python init_db.py

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Add health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]