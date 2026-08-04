#!/bin/bash

# Generate self-signed certificate for development
if [ ! -f /app/cert.pem ]; then
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /app/key.pem \
        -out /app/cert.pem \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
fi

# Start Xray in background
echo "Starting Xray..."
/usr/bin/xray run -config /etc/xray/config.json &

# Start Python management panel
echo "Starting Management Panel..."
cd /app
python3 app.py &

# Start Nginx
echo "Starting Nginx..."
nginx -g "daemon off;"
