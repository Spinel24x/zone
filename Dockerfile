FROM teddysun/xray:latest

# Install Python and nginx for management panel
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    nginx \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy configuration files
COPY config.json /etc/xray/config.json
COPY nginx.conf /etc/nginx/nginx.conf
COPY app.py /app/app.py
COPY dashboard.html /app/dashboard.html
COPY login.html /app/login.html
COPY style.css /app/style.css
COPY entrypoint.sh /entrypoint.sh
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip3 install -r /app/requirements.txt

# Make entrypoint executable
RUN chmod +x /entrypoint.sh

EXPOSE 443 80 8080

ENTRYPOINT ["/entrypoint.sh"]
