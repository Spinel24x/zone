#!/bin/bash

# Xray روی پورت 8081 (داخلی - فقط برای Nginx)
/usr/local/xray/xray -config /usr/local/etc/xray/config.json &

# Flask روی پورت 5000 (داخلی - فقط برای Nginx)
python3 /app.py &

# Nginx روی پورت 8080 (عمومی)
nginx -g 'daemon off;'
