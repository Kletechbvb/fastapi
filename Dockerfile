# # Use slim Python base image
# FROM python:3.11-slim

# # Install system dependencies (Poppler is required for pdf2image)
# RUN apt-get update && apt-get install -y \
#     poppler-utils \
#     && rm -rf /var/lib/apt/lists/*

# # Set workdir
# WORKDIR /app

# # Copy requirements first (better layer caching)
# COPY requirements.txt .

# # Install Python dependencies
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy app source code
# COPY . .

# # Expose port for Railway
# EXPOSE 8080

# # Run FastAPI with Uvicorn
# CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]


# ==========================================================
# FastAPI + Tesseract OCR + Poppler (for pdf2image)
# ==========================================================
FROM python:3.11-slim

# Install system dependencies
# - poppler-utils: for pdf2image
# - tesseract-ocr: for local OCR
# - libjpeg, zlib: for Pillow image handling
RUN apt-get update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency list first (for Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the FastAPI app source code
COPY . .

# Expose Railway’s dynamic port
EXPOSE 8080

# Optional: define where Tesseract language data lives
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata/

# Run FastAPI app (Railway will auto-inject PORT env var)
CMD ["bash", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"]

