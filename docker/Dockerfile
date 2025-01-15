# Use Python 2.7 slim image
FROM python:2.7-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Indian/Antananarivo

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install GSM modem library
RUN git clone https://github.com/faucamp/python-gsmmodem.git && \
    cd python-gsmmodem && \
    pip install . && \
    cd .. && \
    rm -rf python-gsmmodem

# Copy the application files
COPY . .

# Create directory for logs
RUN mkdir -p /app/logs && \
    chmod -R 755 /app/logs

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Expose port 5000
EXPOSE 5000

# Command to run the app with Gunicorn
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--worker-class", "eventlet", \
     "--workers", "1", \
     "--timeout", "120", \
     "--log-level", "info", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "wsgi:app"]