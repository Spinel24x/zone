FROM ubuntu:22.04

WORKDIR /app

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
COPY app.py /app/app.py
COPY login.html /app/login.html
COPY dashboard.html /app/dashboard.html
COPY style.css /app/style.css
COPY zone.js /app/zone.js

RUN chmod +x /entrypoint.sh

EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
