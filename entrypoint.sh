#!/bin/bash

# اجرای Xray روی پورت 8081 (داخلی)
/usr/local/xray/xray -config /usr/local/etc/xray/config.json &

# اجرای Flask روی پورت 8080 (عمومی برای Railway)
python3 /app.py
