from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import json
import uuid
import subprocess
import os
from datetime import datetime
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Admin credentials (change these!)
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

CONFIG_FILE = "/etc/xray/config.json"

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    # Restart Xray
    subprocess.run(["pkill", "xray"], check=False)
    subprocess.Popen(["/usr/bin/xray", "run", "-config", CONFIG_FILE])

def generate_uuid():
    return str(uuid.uuid4())

@app.route('/')
def index():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USER and password == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    config = load_config()
    clients = config['inbounds'][0]['settings']['clients']
    return render_template('dashboard.html', clients=clients)

@app.route('/api/add_client', methods=['POST'])
def add_client():
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    email = data.get('email', f'user_{datetime.now().strftime("%Y%m%d%H%M%S")}')
    client_id = data.get('id', generate_uuid())
    flow = data.get('flow', 'xtls-rprx-vision')
    
    config = load_config()
    clients = config['inbounds'][0]['settings']['clients']
    
    # Add new client
    new_client = {
        "id": client_id,
        "email": email,
        "flow": flow
    }
    clients.append(new_client)
    config['inbounds'][0]['settings']['clients'] = clients
    save_config(config)
    
    # Generate VLESS config for user
    vless_config = generate_vless_config(client_id, email)
    
    return jsonify({
        'success': True,
        'client': new_client,
        'vless_config': vless_config
    })

@app.route('/api/delete_client/<client_id>', methods=['DELETE'])
def delete_client(client_id):
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    config = load_config()
    clients = config['inbounds'][0]['settings']['clients']
    config['inbounds'][0]['settings']['clients'] = [c for c in clients if c['id'] != client_id]
    save_config(config)
    
    return jsonify({'success': True})

def generate_vless_config(client_id, email):
    # This should be updated with your actual domain
    worker_domain = os.environ.get('WORKER_DOMAIN', 'your-worker.workers.dev')
    server_domain = os.environ.get('RAILWAY_DOMAIN', 'your-app.railway.app')
    
    config_text = f"""# VLESS Configuration for {email}
Protocol: VLESS
Address: {worker_domain}
Port: 443
UUID: {client_id}
Flow: xtls-rprx-vision
Encryption: none
Network: ws
Path: /vless-ws
TLS: tls
SNI: {server_domain}
# Full VLESS link:
vless://{client_id}@{worker_domain}:443?encryption=none&security=tls&sni={server_domain}&type=ws&path=/vless-ws&flow=xtls-rprx-vision#{email}
"""
    return config_text

@app.route('/api/clients', methods=['GET'])
def get_clients():
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    config = load_config()
    clients = config['inbounds'][0]['settings']['clients']
    return jsonify({'clients': clients})

@app.route('/api/server_info', methods=['GET'])
def server_info():
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    worker_domain = os.environ.get('WORKER_DOMAIN', 'your-worker.workers.dev')
    server_domain = os.environ.get('RAILWAY_DOMAIN', 'your-app.railway.app')
    
    return jsonify({
        'worker_domain': worker_domain,
        'server_domain': server_domain,
        'port': 443,
        'network': 'ws',
        'path': '/vless-ws',
        'tls': 'tls'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
