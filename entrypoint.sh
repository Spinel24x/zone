#!/bin/bash

# مسیر Xray دستی نصب شده
/usr/local/xray/xray -config /usr/local/etc/xray/config.json &

# پنل مدیریت
python3 /app.py
