from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
import subprocess, os, json, uuid, qrcode
from io import BytesIO
import base64

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', str(uuid.uuid4()))

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

CONFIG_PATH = '/usr/local/etc/xray/config.json'
ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'zone2024')
DOMAIN = os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'localhost')

# Load CSS
CSS = ''
try:
    with open('/app/static/style.css', 'r', encoding='utf-8') as f:
        CSS = f.read()
except: pass

# Load JS
ZONE_JS = ''
try:
    with open('/app/static/zone.js', 'r', encoding='utf-8') as f:
        ZONE_JS = f.read()
except: pass

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    if user_id == '1': return User('1', ADMIN_USER)
    return None

def load_config():
    try:
        with open(CONFIG_PATH, 'r') as f: return json.load(f)
    except: return {
        "log": {"loglevel": "warning"},
        "inbounds": [{"tag":"vless-ws-in","port":8081,"listen":"127.0.0.1","protocol":"vless",
        "settings":{"clients":[],"decryption":"none"},
        "streamSettings":{"network":"ws","wsSettings":{"path":"/ws"}}}],
        "outbounds": [{"protocol":"freedom","tag":"direct"}]
    }

def save_config(cfg):
    with open(CONFIG_PATH, 'w') as f: json.dump(cfg, f, indent=2)
    restart_xray()

def restart_xray():
    subprocess.run(['pkill', '-x', 'xray'], capture_output=True)
    subprocess.Popen(['/usr/local/xray/xray','run','-config',CONFIG_PATH],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def mk_link(uid, email, cleanip=''):
    name = email.split('@')[0] if '@' in email else email
    host = cleanip.strip() if (cleanip and cleanip.strip()) else DOMAIN
    return (f"vless://{uid}@{host}:443?"
            f"encryption=none&security=tls&sni={DOMAIN}"
            f"&alpn=h2,http/1.1&fp=chrome&type=ws"
            f"&path=%2Fws&host={DOMAIN}#{name}-ZONE")

def qr_b64(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data); qr.make(fit=True)
    img = qr.make_image(fill_color="#00ff88", back_color="#0a0a0a")
    buf = BytesIO(); img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

# Routes
@app.route('/login', methods=['GET','POST'])
def login():
    err = None
    if request.method == 'POST':
        if request.form.get('username')==ADMIN_USER and request.form.get('password')==ADMIN_PASS:
            login_user(User('1', ADMIN_USER))
            return redirect(url_for('dashboard'))
        err = 'Invalid credentials'
    return render_template('login.html', css=CSS, error=err)

@app.route('/logout')
@login_required
def logout():
    logout_user(); return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    cfg = load_config()
    clients = cfg['inbounds'][0]['settings']['clients']
    for c in clients: c.setdefault('email','Unknown'); c.setdefault('cleanip',''); c.setdefault('enabled',True)
    return render_template('dashboard.html', css=CSS, js=ZONE_JS,
                           clients=clients,
                           total_clients=len(clients),
                           active_clients=sum(1 for c in clients if c.get('enabled',True)),
                           domain=DOMAIN)

@app.route('/')
def index(): return redirect(url_for('dashboard'))

@app.route('/api/clients')
@login_required
def api_clients():
    cfg = load_config()
    return jsonify([{
        'id':c['id'], 'email':c.get('email',''), 'cleanip':c.get('cleanip',''),
        'enabled':c.get('enabled',True), 'link':mk_link(c['id'],c.get('email',''),c.get('cleanip','')),
        'qr':qr_b64(mk_link(c['id'],c.get('email',''),c.get('cleanip',''))),
        'sub':f"https://{DOMAIN}/sub/{c['id']}"
    } for c in cfg['inbounds'][0]['settings']['clients']])

@app.route('/api/clients/add', methods=['POST'])
@login_required
def api_add():
    data = request.json or {}
    cfg = load_config(); clients = cfg['inbounds'][0]['settings']['clients']
    if len(clients) >= 100: return jsonify({'error':'Max 100'}),400
    
    bulk = data.get('bulk_emails','').strip()
    if bulk:
        emails = [e.strip() for e in bulk.split('\n') if e.strip()]
        ips = [i.strip() for i in data.get('bulk_ips','').strip().split('\n') if i.strip()]
        added = []
        for idx,em in enumerate(emails):
            if len(clients)>=100: break
            cid = str(uuid.uuid4()); cip = ips[idx] if idx<len(ips) else ''
            clients.append({'id':cid,'email':em,'level':0,'cleanip':cip,'enabled':True})
            link = mk_link(cid,em,cip)
            added.append({'id':cid,'email':em,'cleanip':cip,'link':link,'qr':qr_b64(link),'sub':f"https://{DOMAIN}/sub/{cid}"})
        save_config(cfg)
        return jsonify({'success':True,'clients':added})
    
    cid = str(uuid.uuid4())
    email = data.get('email','').strip() or f"user{uuid.uuid4().hex[:6]}@zone.local"
    cleanip = data.get('cleanip','').strip()
    clients.append({'id':cid,'email':email,'level':0,'cleanip':cleanip,'enabled':True})
    save_config(cfg)
    link = mk_link(cid,email,cleanip)
    return jsonify({'success':True,'client':{'id':cid,'email':email,'cleanip':cleanip,'link':link,'qr':qr_b64(link),'sub':f"https://{DOMAIN}/sub/{cid}"}})

@app.route('/api/clients/<cid>/delete', methods=['DELETE'])
@login_required
def api_del(cid):
    cfg = load_config()
    cfg['inbounds'][0]['settings']['clients'] = [c for c in cfg['inbounds'][0]['settings']['clients'] if c['id']!=cid]
    save_config(cfg)
    return jsonify({'success':True})

@app.route('/api/clients/<cid>/toggle', methods=['POST'])
@login_required
def api_toggle(cid):
    cfg = load_config()
    for c in cfg['inbounds'][0]['settings']['clients']:
        if c['id']==cid: c['enabled'] = not c.get('enabled',True); break
    save_config(cfg)
    return jsonify({'success':True})

@app.route('/sub/<cid>')
def sub(cid):
    cfg = load_config()
    for c in cfg['inbounds'][0]['settings']['clients']:
        if c['id']==cid: return f"{mk_link(cid,c.get('email',''),c.get('cleanip',''))}\n",200,{'Content-Type':'text/plain'}
    return "Not found",404

@app.route('/api/status')
@login_required
def api_status():
    r = subprocess.run(['pgrep','-x','xray'], capture_output=True)
    cfg = load_config()
    return jsonify({
        'xray_running': r.returncode==0,
        'total_clients': len(cfg['inbounds'][0]['settings']['clients']),
        'active_clients': sum(1 for c in cfg['inbounds'][0]['settings']['clients'] if c.get('enabled',True))
    })

@app.route('/api/export/<cid>')
@login_required
def api_export(cid):
    cfg = load_config()
    for c in cfg['inbounds'][0]['settings']['clients']:
        if c['id']==cid:
            address = c.get('cleanip') or DOMAIN
            return jsonify({
                "dns":{"servers":["1.1.1.1","8.8.8.8"]},
                "inbounds":[{"port":10808,"listen":"127.0.0.1","protocol":"socks"}],
                "outbounds":[{
                    "protocol":"vless",
                    "settings":{"vnext":[{"address":address,"port":443,"users":[{"id":cid,"encryption":"none"}]}]},
                    "streamSettings":{"network":"ws","security":"tls","wsSettings":{"path":"/ws","headers":{"Host":DOMAIN}},"tlsSettings":{"serverName":DOMAIN,"fingerprint":"chrome","alpn":["h2","http/1.1"]}}
                }]
            })
    return jsonify({'error':'Not found'}),404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)), debug=False)
