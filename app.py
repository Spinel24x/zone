from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
import subprocess
import os
import json
import uuid
import qrcode
from io import BytesIO
import base64

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', str(uuid.uuid4()))

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

CONFIG_PATH = '/usr/local/etc/xray/config.json'
CSS_PATH = '/app/static/style.css'
JS_PATH = '/app/static/zone.js'

CSS = ''
if os.path.exists(CSS_PATH):
    with open(CSS_PATH, 'r', encoding='utf-8') as f:
        CSS = f.read()

ZONE_JS = ''
if os.path.exists(JS_PATH):
    with open(JS_PATH, 'r', encoding='utf-8') as f:
        ZONE_JS = f.read()

ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'zone2024')
DOMAIN = os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'localhost')

WS_PATH = '/ws'  # مسیر ثابت WebSocket

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    if user_id == '1':
        return User('1', ADMIN_USER)
    return None

def load_config():
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
            # اطمینان از path صحیح
            config['inbounds'][0]['streamSettings']['wsSettings']['path'] = WS_PATH
            return config
    except:
        return create_default_config()

def create_default_config():
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "port": 8081,
            "listen": "127.0.0.1",
            "protocol": "vless",
            "settings": {
                "clients": [],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "ws",
                "wsSettings": {
                    "path": WS_PATH
                }
            }
        }],
        "outbounds": [{"protocol": "freedom", "tag": "direct"}]
    }

def save_config(config):
    config['inbounds'][0]['streamSettings']['wsSettings']['path'] = WS_PATH
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)
    restart_xray()

def restart_xray():
    subprocess.run(['pkill', '-x', 'xray'], capture_output=True)
    subprocess.Popen(['/usr/local/xray/xray', '-config', CONFIG_PATH],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def generate_vless_link(client_id, email, cleanip=None):
    name = email.split('@')[0] if '@' in email else email
    
    if cleanip and cleanip.strip():
        host = cleanip.strip()
    else:
        host = DOMAIN
    
    # path=%2Fws یعنی /ws
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

# ==================== ROUTES ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USER and password == ADMIN_PASS:
            login_user(User('1', username))
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
    
    for c in clients:
        c.setdefault('email', 'Unknown')
        c.setdefault('cleanip', '')
        c.setdefault('enabled', True)
    
    total = len(clients)
    active = sum(1 for c in clients if c.get('enabled', True))
    
    return render_template('dashboard.html',
                         css=CSS,
                         js=ZONE_JS,
                         clients=clients,
                         total_clients=total,
                         active_clients=active,
                         domain=DOMAIN)

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

# ==================== API ====================

@app.route('/api/clients')
@login_required
def api_clients():
    config = load_config()
    clients = config['inbounds'][0]['settings']['clients']
    result = []
    for c in clients:
        link = generate_vless_link(c['id'], c.get('email', ''), c.get('cleanip', ''))
        qr = generate_qr_base64(link)
        result.append({
            'id': c['id'],
            'email': c.get('email', 'Unknown'),
            'cleanip': c.get('cleanip', ''),
            'enabled': c.get('enabled', True),
            'link': link,
            'qr': qr,
            'sub': f"https://{DOMAIN}/sub/{c['id']}"
        })
    return jsonify(result)

@app.route('/api/clients/add', methods=['POST'])
@login_required
def api_add_client():
    data = request.json or {}
    email = data.get('email', '').strip() or f"user{uuid.uuid4().hex[:6]}@zone.local"
    cleanip = data.get('cleanip', '').strip()
    bulk_emails = data.get('bulk_emails', '').strip()
    bulk_ips = data.get('bulk_ips', '').strip()
    
    config = load_config()
    clients = config['inbounds'][0]['settings']['clients']
    
    if len(clients) >= 100:
        return jsonify({'error': 'Max 100 clients reached'}), 400
    
    if bulk_emails:
        email_list = [e.strip() for e in bulk_emails.split('\n') if e.strip()]
        ip_list = [i.strip() for i in bulk_ips.split('\n') if i.strip()]
        added = []
        for idx, em in enumerate(email_list):
            if len(clients) >= 100:
                break
            cid = str(uuid.uuid4())
            cip = ip_list[idx] if idx < len(ip_list) else ''
            clients.append({
                'id': cid, 'email': em, 'level': 0,
                'cleanip': cip, 'enabled': True
            })
            link = generate_vless_link(cid, em, cip)
            added.append({
                'id': cid, 'email': em, 'cleanip': cip,
                'link': link, 'qr': generate_qr_base64(link),
                'sub': f"https://{DOMAIN}/sub/{cid}"
            })
        config['inbounds'][0]['settings']['clients'] = clients
        save_config(config)
        return jsonify({'success': True, 'clients': added})
    
    cid = str(uuid.uuid4())
    clients.append({
        'id': cid, 'email': email, 'level': 0,
        'cleanip': cleanip, 'enabled': True
    })
    config['inbounds'][0]['settings']['clients'] = clients
    save_config(config)
    
    link = generate_vless_link(cid, email, cleanip)
    return jsonify({
        'success': True,
        'client': {
            'id': cid, 'email': email, 'cleanip': cleanip,
            'link': link, 'qr': generate_qr_base64(link),
            'sub': f"https://{DOMAIN}/sub/{cid}"
        }
    })

@app.route('/api/clients/<cid>/delete', methods=['DELETE'])
@login_required
def api_delete_client(cid):
    config = load_config()
    config['inbounds'][0]['settings']['clients'] = [
        c for c in config['inbounds'][0]['settings']['clients'] if c['id'] != cid
    ]
    save_config(config)
    return jsonify({'success': True})

@app.route('/api/clients/<cid>/toggle', methods=['POST'])
@login_required
def api_toggle_client(cid):
    config = load_config()
    for c in config['inbounds'][0]['settings']['clients']:
        if c['id'] == cid:
            c['enabled'] = not c.get('enabled', True)
            break
    save_config(config)
    return jsonify({'success': True})

@app.route('/sub/<cid>')
def subscription(cid):
    config = load_config()
    for c in config['inbounds'][0]['settings']['clients']:
        if c['id'] == cid:
            link = generate_vless_link(c['id'], c.get('email', ''), c.get('cleanip', ''))
            return f"{link}\n", 200, {'Content-Type': 'text/plain; charset=utf-8'}
    return "Client not found", 404

@app.route('/api/status')
@login_required
def api_status():
    result = subprocess.run(['pgrep', '-x', 'xray'], capture_output=True)
    config = load_config()
    total = len(config['inbounds'][0]['settings']['clients'])
    active = sum(1 for c in config['inbounds'][0]['settings']['clients'] if c.get('enabled', True))
    return jsonify({
        'xray_running': result.returncode == 0,
        'total_clients': total,
        'active_clients': active
    })

@app.route('/api/export/<cid>')
@login_required
def api_export(cid):
    config = load_config()
    for c in config['inbounds'][0]['settings']['clients']:
        if c['id'] == cid:
            address = c.get('cleanip') or DOMAIN
            exp = {
                "dns": {"servers": ["1.1.1.1", "8.8.8.8"]},
                "inbounds": [{"port": 10808, "listen": "127.0.0.1", "protocol": "socks"}],
                "outbounds": [{
                    "protocol": "vless",
                    "settings": {"vnext": [{
                        "address": address,
                        "port": 443,
                        "users": [{"id": cid, "encryption": "none", "level": 0}]
                    }]},
                    "streamSettings": {
                        "network": "ws",
                        "security": "tls",
                        "wsSettings": {"path": WS_PATH},
                        "tlsSettings": {"serverName": DOMAIN}
                    }
                }]
            }
            return jsonify(exp)
    return jsonify({'error': 'Not found'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
