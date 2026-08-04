from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import wraps
import subprocess
import os
import json
import uuid
import qrcode
from io import BytesIO
import base64

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'zone-secret-key-change-me-2024')

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Load CSS
with open('style.css', 'r', encoding='utf-8') as f:
    CSS = f.read()

# Load Zone JS
with open('zone.js', 'r', encoding='utf-8') as f:
    ZONE_JS = f.read()

# Config path
CONFIG_PATH = '/usr/local/etc/xray/config.json'
USERS_FILE = '/data/users.json'

# Default admin
ADMIN_USERNAME = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASS', 'zone2024')

# Ensure data directory
os.makedirs('/data', exist_ok=True)
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w') as f:
        json.dump([], f)

# Domain
DOMAIN = os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'localhost')
RAILWAY_PORT = os.environ.get('PORT', '8080')

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    if user_id == '1':
        return User('1', ADMIN_USERNAME)
    return None

def load_config():
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except:
        return {
            "log": {"loglevel": "warning"},
            "inbounds": [{
                "port": 8081,
                "listen": "127.0.0.1",
                "protocol": "vless",
                "settings": {"clients": [], "decryption": "none"},
                "streamSettings": {"network": "ws", "wsSettings": {"path": "/ws"}}
            }],
            "outbounds": [{"protocol": "freedom", "tag": "direct"}]
        }

def save_config(config):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)
    restart_xray_service()

def restart_xray_service():
    subprocess.run(['pkill', '-x', 'xray'], capture_output=True)
    subprocess.Popen(['/usr/local/xray/xray', '-config', CONFIG_PATH])

def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def generate_vless_link(client_id, email, cleanip=None):
    host = DOMAIN
    sni = DOMAIN
    
    name = email.split('@')[0] if '@' in email else email
    
    if cleanip and cleanip.strip():
        host = cleanip.strip()
    
    link = f"vless://{client_id}@{host}:443?encryption=none&security=tls&type=ws&path=%2Fws&host={DOMAIN}&sni={DOMAIN}#{name}-ZONE"
    return link

def generate_qr_base64(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#00ff88", back_color="#0a0a0a")
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            user = User('1', username)
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid credentials'
    
    return render_template('login.html', css=CSS, error=error)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    config = load_config()
    clients = config['inbounds'][0]['settings']['clients']
    
    for client in clients:
        if 'cleanip' not in client:
            client['cleanip'] = ''
        if 'enabled' not in client:
            client['enabled'] = True
    
    return render_template('dashboard.html', 
                         css=CSS, 
                         js=ZONE_JS,
                         clients=clients,
                         domain=DOMAIN)

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/api/clients', methods=['GET'])
@login_required
def get_clients():
    config = load_config()
    clients = config['inbounds'][0]['settings']['clients']
    
    result = []
    for client in clients:
        link = generate_vless_link(client['id'], client.get('email', ''), client.get('cleanip', ''))
        qr = generate_qr_base64(link)
        result.append({
            'id': client['id'],
            'email': client.get('email', 'Unknown'),
            'cleanip': client.get('cleanip', ''),
            'enabled': client.get('enabled', True),
            'link': link,
            'qr': qr,
            'subscription': f"https://{DOMAIN}/sub/{client['id']}"
        })
    
    return jsonify(result)

@app.route('/api/clients/add', methods=['POST'])
@login_required
def add_client():
    try:
        data = request.json
        email = data.get('email', f'user{uuid.uuid4().hex[:8]}@zone.local')
        cleanip = data.get('cleanip', '')
        
        client_id = str(uuid.uuid4())
        
        config = load_config()
        config['inbounds'][0]['settings']['clients'].append({
            'id': client_id,
            'email': email,
            'level': 0,
            'cleanip': cleanip,
            'enabled': True
        })
        save_config(config)
        
        link = generate_vless_link(client_id, email, cleanip)
        qr = generate_qr_base64(link)
        
        return jsonify({
            'success': True,
            'client': {
                'id': client_id,
                'email': email,
                'cleanip': cleanip,
                'link': link,
                'qr': qr,
                'subscription': f"https://{DOMAIN}/sub/{client_id}"
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clients/bulk-add', methods=['POST'])
@login_required
def bulk_add_clients():
    try:
        data = request.json
        emails = data.get('emails', '').strip().split('\n')
        cleanips = data.get('cleanips', '').strip().split('\n')
        
        emails = [e.strip() for e in emails if e.strip()]
        cleanips = [c.strip() for c in cleanips if c.strip()]
        
        config = load_config()
        added = []
        
        for i, email in enumerate(emails):
            client_id = str(uuid.uuid4())
            cleanip = cleanips[i] if i < len(cleanips) else ''
            
            config['inbounds'][0]['settings']['clients'].append({
                'id': client_id,
                'email': email,
                'level': 0,
                'cleanip': cleanip,
                'enabled': True
            })
            
            link = generate_vless_link(client_id, email, cleanip)
            qr = generate_qr_base64(link)
            added.append({
                'id': client_id,
                'email': email,
                'cleanip': cleanip,
                'link': link,
                'qr': qr,
                'subscription': f"https://{DOMAIN}/sub/{client_id}"
            })
        
        save_config(config)
        return jsonify({'success': True, 'clients': added})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clients/<client_id>/delete', methods=['DELETE'])
@login_required
def delete_client(client_id):
    try:
        config = load_config()
        clients = config['inbounds'][0]['settings']['clients']
        config['inbounds'][0]['settings']['clients'] = [c for c in clients if c['id'] != client_id]
        save_config(config)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clients/<client_id>/toggle', methods=['POST'])
@login_required
def toggle_client(client_id):
    try:
        config = load_config()
        clients = config['inbounds'][0]['settings']['clients']
        for client in clients:
            if client['id'] == client_id:
                client['enabled'] = not client.get('enabled', True)
                break
        save_config(config)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/sub/<client_id>')
def subscription(client_id):
    config = load_config()
    clients = config['inbounds'][0]['settings']['clients']
    
    for client in clients:
        if client['id'] == client_id:
            link = generate_vless_link(client['id'], client.get('email', ''), client.get('cleanip', ''))
            return f"{link}\n", 200, {'Content-Type': 'text/plain; charset=utf-8'}
    
    return "Client not found", 404

@app.route('/api/status')
@login_required
def status():
    try:
        result = subprocess.run(['pgrep', '-x', 'xray'], capture_output=True)
        xray_running = result.returncode == 0
        config = load_config()
        total_clients = len(config['inbounds'][0]['settings']['clients'])
        return jsonify({
            'xray_running': xray_running,
            'total_clients': total_clients
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/<client_id>')
@login_required
def export_config(client_id):
    config = load_config()
    clients = config['inbounds'][0]['settings']['clients']
    
    for client in clients:
        if client['id'] == client_id:
            client_config = {
                "dns": {"servers": ["1.1.1.1", "8.8.8.8"]},
                "inbounds": [{"port": 10808, "listen": "127.0.0.1", "protocol": "socks"}],
                "outbounds": [{
                    "protocol": "vless",
                    "settings": {"vnext": [{
                        "address": DOMAIN,
                        "port": 443,
                        "users": [{"id": client['id'], "encryption": "none", "level": 0}]
                    }]},
                    "streamSettings": {
                        "network": "ws",
                        "security": "tls",
                        "wsSettings": {"path": "/ws"},
                        "tlsSettings": {"serverName": DOMAIN}
                    }
                }]
            }
            return jsonify(client_config)
    
    return jsonify({'error': 'Client not found'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
