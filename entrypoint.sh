#!/bin/bash

echo "=== Starting VLESS Server ==="

# Generate SSL certificate
if [ ! -f /app/cert.pem ]; then
    echo "Generating SSL certificate..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /app/key.pem \
        -out /app/cert.pem \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=${RAILWAY_PUBLIC_DOMAIN:-localhost}"
fi

# Set environment variables
export WORKER_DOMAIN=${WORKER_DOMAIN:-"your-worker.workers.dev"}
export RAILWAY_DOMAIN=${RAILWAY_PUBLIC_DOMAIN:-"localhost"}

# Create templates and static directories if they don't exist
mkdir -p /app/templates /app/static

# Start Xray
echo "Starting Xray core..."
/usr/bin/xray run -config /etc/xray/config.json &
sleep 2

# Start Flask app
echo "Starting management panel..."
cd /app
python3 app.py &
sleep 2

# Start Nginx
echo "Starting Nginx..."
nginx -g "daemon off;"
