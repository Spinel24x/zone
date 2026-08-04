// Zone Background Animation
const canvas = document.getElementById('hexCanvas');
const ctx = canvas.getContext('2d');
canvas.width = window.innerWidth;
canvas.height = window.innerHeight;

let particles = [];
const mouse = { x: -1000, y: -1000بسیار عالی! پروژه **Zone** با دیزاین حرفه‌ای. بذار همه فایل‌ها رو کامل بازنویسی کنم.

---

## 1. Dockerfile (بدون تغییر - فقط اسم پوشه‌ها)

```dockerfile
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    python3 \
    python3-pip \
    wget \
    nginx \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /usr/local/xray && \
    cd /tmp && \
    wget https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip && \
    unzip Xray-linux-64.zip -d /usr/local/xray && \
    chmod +x /usr/local/xray/xray && \
    rm Xray-linux-64.zip && \
    mkdir -p /usr/local/etc/xray

COPY requirements.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt

COPY nginx.conf /etc/nginx/sites-available/default
COPY entrypoint.sh /entrypoint.sh
COPY config.json /usr/local/etc/xray/config.json
COPY app.py /app.py
COPY login.html /login.html
COPY dashboard.html /dashboard.html
COPY style.css /style.css
COPY zone.js /zone.js

RUN chmod +x /entrypoint.sh

EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
