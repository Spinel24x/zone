FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install

COPY requirements.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt

COPY entrypoint.sh /entrypoint.sh
COPY config.json /usr/local/etc/xray/config.json
COPY app.py /app.py
COPY login.html /login.html
COPY dashboard.html /dashboard.html
COPY style.css /style.css

RUN chmod +x /entrypoint.sh

EXPOSE 8080 5000
ENTRYPOINT ["/entrypoint.sh"]
