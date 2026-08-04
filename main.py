from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import json
import uuid
import subprocess
import os
from datetime import datetime
import secrets
import threading
import time

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin123")
CONFIG_FILE = "/etc/xray/config.json"

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"inbounds": [{"settings": {"clients": []}}]}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    # Restart Xray
    os.system("pkill xray")
    time.sleep(1)
    subprocess.Popen(["/usr/bin/xray", "run", "-config", CONFIG_FILE])

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
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/api/server_info')
def server_info():
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    worker_domain = os.environ.get("WORKER_DOMAIN", "your-worker.workers.dev")
    railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "localhost")
    
    return jsonify({
        'worker_domain': worker_domain,
        'server_domain': railway_domain,
        'port': 443,
        'network': 'ws',
        'path': '/vless-ws',
        'security': 'tls',
        'type': 'ws'
    })

@app.route('/api/clients')
def get_clients():
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    config = load_config()
    clients = config.get('inbounds', [{}])[0].get('settings', {}).get('clients', [])
    return jsonify({'clients': clients})

@app.route('/api/add_client', methods=['POST'])
def add_client():
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json or {}
    email = data.get('email', f'user_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
    client_id = data.get('id', str(uuid.uuid4()))
    
    config = load_config()
    clients = config['inbounds'][0]['settings'].get('clients', [])
    
    new_client = {
        "id": client_id,
        "email": email,
        "flow": "xtls-rprx-vision"
    }
    
    clients.append(new_client)
    config['inbounds'][0]['settings']['clients'] = clients
    save_config(config)
    
    # Generate VLESS link
    worker_domain = os.environ.get("WORKER_DOMAIN", "your-worker.workers.dev")
    railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "localhost")
    
    vless_link = f"vless://{client_id}@{worker_domain}:443?encryption=none&security=tls&sni={railway_domain}&type=ws&path=/vless-ws&flow=xtls-rprx-vision#{email}"
    
    return jsonify({
        'success': True,
        'client': new_client,
        'vless_link': vless_link
    })

@app.route('/api/delete_client/<client_id>', methods=['DELETE'])
def delete_client(client_id):
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    config = load_config()
    clients = config['inbounds'][0]['settings'].get('clients', [])
    config['inbounds'][0]['settings']['clients'] = [c for c in clients if c['id'] != client_id]
    save_config(config)
    
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
