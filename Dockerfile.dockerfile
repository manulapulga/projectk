# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

# Configure nginx
COPY nginx.conf /etc/nginx/nginx.conf

# Configure supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create necessary directories
RUN mkdir -p /tmp/nginx_cache && \
    chmod -R 755 /tmp && \
    chown -R www-data:www-data /tmp

# Expose port
EXPOSE 8501

# Start application
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]