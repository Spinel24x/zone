FROM teddysun/xray:latest

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    nginx \
    openssl \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY config.json /etc/xray/config.json
COPY nginx.conf /etc/nginx/nginx.conf
COPY app.py /app/app.py
COPY requirements.txt /app/requirements.txt
COPY dashboard.html /app/templates/dashboard.html
COPY login.html /app/templates/login.html
COPY style.css /app/static/style.css
COPY entrypoint.sh /entrypoint.sh

RUN pip3 install --break-system-packages -r /app/requirements.txt

RUN chmod +x /entrypoint.sh

RUN mkdir -p /app/templates /app/static

EXPOSE 443 80 5000

ENTRYPOINT ["/entrypoint.sh"]
