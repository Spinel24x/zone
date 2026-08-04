#!/bin/bash

RAILWAY_PORT=${PORT:-8080}

echo "========================================="
echo "🚀 ZoneTunnel Starting..."
echo "Port: $RAILWAY_PORT"
echo "========================================="

echo "[1/3] Starting Xray on port 8081..."
/usr/local/xray/xray -config /usr/local/etc/xray/config.json &
sleep 2

echo "[2/3] Starting Flask on port 5000..."
cd /app
PORT=5000 python3 /app/app.py &
sleep 2

echo "[3/3] Starting Nginx on port $RAILWAY_PORT..."
sed -i "s/listen 8080/listen $RAILWAY_PORT/g" /etc/nginx/sites-available/default
nginx -g 'daemon off;'
