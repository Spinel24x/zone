from flask import Flask, render_template_string, request, jsonify, send_from_directory
import subprocess
import os
import json

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ZoneTunnel | تانل شخصی</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: #1a1a1a;
            border-radius: 12px;
            padding: 30px;
            width: 100%;
            max-width: 900px;
            box-shadow: 0 0 30px rgba(0,255,100,0.1);
            border: 1px solid #333;
        }
        h1 {
            color: #00ff64;
            text-align: center;
            margin-bottom: 10px;
            font-size: 28px;
        }
        .subtitle {
            text-align: center;
            color: #888;
            margin-bottom: 30px;
        }
        .status-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            padding: 15px;
            background: #111;
            border-radius: 8px;
        }
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #ff4444;
        }
        .dot.active { background: #00ff64; }
        textarea {
            width: 100%;
            min-height: 400px;
            background: #0d0d0d;
            color: #00ff64;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 15px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            resize: vertical;
            direction: ltr;
        }
        .btn-group {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        button {
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            font-size: 16px;
            transition: all 0.3s;
        }
        .btn-save {
            background: #00ff64;
            color: #000;
        }
        .btn-save:hover { background: #00cc50; }
        .btn-refresh {
            background: #333;
            color: #fff;
        }
        .btn-refresh:hover { background: #444; }
        .btn-restart {
            background: #ff4444;
            color: #fff;
        }
        .btn-restart:hover { background: #cc0000; }
        .message {
            margin-top: 15px;
            padding: 10px;
            border-radius: 5px;
            text-align: center;
            display: none;
        }
        .message.success { background: #0a3d0a; color: #00ff64; display: block; }
        .message.error { background: #3d0a0a; color: #ff4444; display: block; }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚡ ZoneTunnel</h1>
        <p class="subtitle">مدیریت کانفیگ Xray</p>
        
        <div class="status-bar">
            <div class="status-indicator">
                <div class="dot" id="statusDot"></div>
                <span id="statusText">در حال بررسی...</span>
            </div>
            <button class="btn-restart" onclick="restartXray()">🔄 ریستارت Xray</button>
        </div>
        
        <textarea id="configEditor" placeholder="در حال بارگذاری کانفیگ..."></textarea>
        
        <div class="btn-group">
            <button class="btn-save" onclick="saveConfig()">💾 ذخیره کانفیگ</button>
            <button class="btn-refresh" onclick="loadConfig()">🔄 بارگذاری مجدد</button>
        </div>
        
        <div id="message" class="message"></div>
    </div>

    <script>
        async function loadConfig() {
            try {
                const res = await fetch('/api/config');
                const data = await res.json();
                if (data.error) {
                    showMessage('⚠️ ' + data.error, 'error');
                } else {
                    document.getElementById('configEditor').value = data.content;
                    showMessage('✅ کانفیگ بارگذاری شد', 'success');
                }
            } catch (e) {
                showMessage('❌ خطا در بارگذاری', 'error');
            }
            checkStatus();
        }

        async function saveConfig() {
            const content = document.getElementById('configEditor').value;
            try {
                const res = await fetch('/api/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content })
                });
                const data = await res.json();
                if (data.error) {
                    showMessage('❌ ' + data.error, 'error');
                } else {
                    showMessage('✅ کانفیگ ذخیره و Xray ریستارت شد', 'success');
                }
            } catch (e) {
                showMessage('❌ خطا در ذخیره', 'error');
            }
            checkStatus();
        }

        async function restartXray() {
            try {
                const res = await fetch('/api/restart', { method: 'POST' });
                const data = await res.json();
                showMessage(data.message || '✅ Xray ریستارت شد', 'success');
            } catch (e) {
                showMessage('❌ خطا در ریستارت', 'error');
            }
            setTimeout(checkStatus, 2000);
        }

        async function checkStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                const dot = document.getElementById('statusDot');
                const text = document.getElementById('statusText');
                if (data.xray_running) {
                    dot.classList.add('active');
                    text.textContent = 'Xray فعال است';
                } else {
                    dot.classList.remove('active');
                    text.textContent = 'Xray غیرفعال است';
                }
            } catch (e) {
                document.getElementById('statusText').textContent = 'عدم اتصال';
            }
        }

        function showMessage(msg, type) {
            const el = document.getElementById('message');
            el.textContent = msg;
            el.className = 'message ' + type;
            setTimeout(() => { el.className = 'message'; }, 4000);
        }

        loadConfig();
        setInterval(checkStatus, 10000);
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/config', methods=['GET'])
def get_config():
    try:
        if not os.path.exists('/usr/local/etc/xray/config.json'):
            return jsonify({'error': 'فایل کانفیگ پیدا نشد'}), 404
        
        with open('/usr/local/etc/xray/config.json', 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'content': content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config', methods=['POST'])
def save_config():
    try:
        data = request.json
        if not data or 'content' not in data:
            return jsonify({'error': 'محتوای کانفیگ ارسال نشده'}), 400
        
        # اعتبارسنجی JSON
        try:
            json.loads(data['content'])
        except json.JSONDecodeError:
            return jsonify({'error': 'فرمت JSON نامعتبر است'}), 400
        
        # بکاپ از کانفیگ قبلی
        if os.path.exists('/usr/local/etc/xray/config.json'):
            os.rename('/usr/local/etc/xray/config.json', '/usr/local/etc/xray/config.json.bak')
        
        with open('/usr/local/etc/xray/config.json', 'w', encoding='utf-8') as f:
            f.write(data['content'])
        
        # ریستارت xray
        subprocess.run(['pkill', '-x', 'xray'], capture_output=True)
        subprocess.Popen(['/usr/local/xray/xray', '-config', '/usr/local/etc/xray/config.json'])
        
        return jsonify({'message': 'کانفیگ ذخیره و Xray ریستارت شد'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status')
def status():
    try:
        result = subprocess.run(['pgrep', '-x', 'xray'], capture_output=True)
        xray_running = result.returncode == 0
        config_exists = os.path.exists('/usr/local/etc/xray/config.json')
        return jsonify({
            'xray_running': xray_running,
            'config_exists': config_exists
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/restart', methods=['POST'])
def restart_xray():
    try:
        subprocess.run(['pkill', '-x', 'xray'], capture_output=True)
        subprocess.Popen(['/usr/local/xray/xray', '-config', '/usr/local/etc/xray/config.json'])
        return jsonify({'message': 'Xray ریستارت شد'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
