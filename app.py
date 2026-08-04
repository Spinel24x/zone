from flask import Flask, render_template_string, request, jsonify, redirect, session
from functools import wraps
import json
import uuid
import qrcode
import io
import base64
import os
import subprocess

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-secret-key')

ADMIN_USERNAME = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASS', 'admin123')
XRAY_CONFIG_PATH = '/usr/local/etc/xray/config.json'
RAILWAY_DOMAIN = os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'localhost')
WORKER_DOMAIN = os.environ.get('WORKER_DOMAIN', 'your-worker.workers.dev')

# خواندن فایل‌های HTML
with open('/login.html', 'r', encoding='utf-8') as f:
    LOGIN_HTML = f.read()

with open('/dashboard.html', 'r', encoding='utf-8') as f:
    DASHBOARD_HTML = f.read()

with open('/style.css', 'r', encoding='utf-8') as f:
    CSS_STYLE = f.read()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'logged_in' in session:
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/health')
def health():
    return 'OK', 200

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USERNAME and \
           request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect('/dashboard')
        error = 'نام کاربری یا رمز عبور اشتباه است'
    
    return render_template_string(LOGIN_HTML, error=error, css=CSS_STYLE)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect('/login')

@app.route('/dashboard')
@login_required
def dashboard():
    config = load_config()
    clients = config['inbounds'][0]['settings']['clients']
    return render_template_string(DASHBOARD_HTML, clients=clients, css=CSS_STYLE)

@app.route('/api/clients')
@login_required
def get_clients():
    config = load_config()
    clients = config['inbounds'][0]['settings']['clients']
    
    for client in clients:
        client['vless_link'] = generate_vless_link(client['id'], client.get('email', 'Unknown'))
        client['qr_code'] = generate_qr_base64(client['vless_link'])
    
    return jsonify(clients)

@app.route('/api/clients/add', methods=['POST'])
@login_required
def add_client():
    data = request.json
    email = data.get('email', 'user@example.com')
    client_uuid = str(uuid.uuid4())
    
    config = load_config()
    config['inbounds'][0]['settings']['clients'].append({
        "id": client_uuid,
        "email": email,
        "level": 1,
        "alterId": 0
    })
    
    save_config(config)
    restart_xray()
    
    vless_link = generate_vless_link(client_uuid, email)
    qr_code = generate_qr_base64(vless_link)
    
    return jsonify({
        'success': True,
        'id': client_uuid,
        'email': email,
        'vless_link': vless_link,
        'qr_code': qr_code
    })

@app.route('/api/clients/<client_uuid>/delete', methods=['DELETE'])
@login_required
def delete_client(client_uuid):
    config = load_config()
    config['inbounds'][0]['settings']['clients'] = [
        c for c in config['inbounds'][0]['settings']['clients'] 
        if c['id'] != client_uuid
    ]
    save_config(config)
    restart_xray()
    return jsonify({'success': True})

@app.route('/api/export/<client_uuid>')
@login_required
def export_config(client_uuid):
    config = load_config()
    client = next((c for c in config['inbounds'][0]['settings']['clients'] if c['id'] == client_uuid), None)
    
    if not client:
        return jsonify({'error': 'Not found'}), 404
    
    return jsonify({
        "v": "2",
        "ps": client.get('email', 'VPN'),
        "add": WORKER_DOMAIN,
        "port": "443",
        "id": client_uuid,
        "aid": "0",
        "net": "ws",
        "type": "none",
        "host": WORKER_DOMAIN,
        "path": "/ws",
        "tls": "tls",
        "sni": WORKER_DOMAIN
    })

def load_config():
    with open(XRAY_CONFIG_PATH, 'r') as f:
        return json.load(f)

def save_config(config):
    with open(XRAY_CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)

def restart_xray():
    os.system('pkill xray')
    subprocess.Popen(['/usr/local/xray/xray', '-config', XRAY_CONFIG_PATH])

def generate_vless_link(uuid, email):
    return f"vless://{uuid}@{WORKER_DOMAIN}:443?path=%2Fws&security=tls&encryption=none&host={WORKER_DOMAIN}&type=ws&sni={WORKER_DOMAIN}#{email}"

def generate_qr_base64(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
