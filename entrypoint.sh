#!/bin/bash
set -e

RAILWAY_PORT=${PORT:-8080}

echo "========================================="
echo "🚀 ZONE Tunnel Starting..."
echo "Port: $RAILWAY_PORT"
echo "========================================="

echo "[1/3] Starting Xray (port 8081)..."
/usr/local/xray/xray run -config /usr/local/etc/xray/config.json &
sleep 3

if pgrep -x xray > /dev/null; then
    echo "✅ Xray PID: $(pgrep xray)"
else
    echo "❌ Xray failed!"
    exit 1
fi

echo "[2/3] Starting Flask (port 5000)..."
cd /app
PORT=5000 python3 /app/app.py &
sleep 2

echo "[3/3] Starting Nginx (port $RAILWAY_PORT)..."
sed -i "s/listen 8080/listen $RAILWAY_PORT/g" /etc/nginx/sites-available/default
exec nginx -g 'daemon off;'
