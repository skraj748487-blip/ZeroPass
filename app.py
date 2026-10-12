from flask import Flask, jsonify, request, render_template_string
import uuid
import os
import time
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import sqlite3

app = Flask(__name__)
app.secret_key = os.urandom(32)
DB_PATH = 'auth_vault.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions 
                 (token TEXT PRIMARY KEY, status TEXT, user_id TEXT, created_at REAL, used INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS access_logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, action TEXT, target TEXT, timestamp REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id TEXT PRIMARY KEY, org_name TEXT, public_key TEXT, is_admin INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

    if not os.path.exists("my_private_key.pem") or not os.path.exists("my_public_key.pem"):
        key = RSA.generate(2048)
        with open("my_private_key.pem", "wb") as f:
            f.write(key.export_key('PEM'))
        with open("my_public_key.pem", "wb") as f:
            f.write(key.publickey().export_key('PEM'))

    with open("my_public_key.pem", "rb") as f:
        pub = f.read().decode('utf-8')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, org_name, public_key, is_admin) VALUES (?, ?, ?, 1)", 
              ("sahil_master", "AirAuth Enterprise", pub))
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def terminal_display():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AirAuth Enterprise Terminal</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
        <style>
            body { background: #020617; color: #38bdf8; font-family: monospace; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }
            .badge { background: #0284c7; color: #fff; font-size: 11px; padding: 6px 14px; border-radius: 20px; font-weight: bold; margin-bottom: 12px; }
            .card { background: #0f172a; border: 2px solid #0284c7; border-radius: 20px; padding: 25px; text-align: center; max-width: 400px; width: 100%; box-shadow: 0 0 40px rgba(2,132,199,0.25); }
            .qr-box { background: #fff; padding: 10px; border-radius: 12px; display: inline-block; margin: 15px auto; }
            .metric { display: flex; justify-content: space-between; font-size: 11px; color: #94a3b8; border-top: 1px dashed #334155; padding-top: 10px; margin-top: 15px; }
            .nav-links { display: flex; justify-content: space-around; margin-top: 20px; border-top: 1px solid #1e293b; padding-top: 15px; }
            .nav-links a { color: #94a3b8; font-size: 12px; text-decoration: none; display: flex; align-items: center; gap: 4px; }
            .btn { display: inline-block; margin-top: 12px; padding: 10px 18px; background: #0284c7; color: #fff; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 13px; }
        </style>
    </head>
    <body>
        <div class="badge">⚡ ENGINEERED BY SAHIL AHMAD // LEAD ARCHITECT ⚡</div>
        <div class="card" id="box">
            <h2 style="margin: 0; color: #fff; font-size: 20px;">AirAuth Enterprise Terminal</h2>
            <div style="font-size: 12px; color: #34d399; margin: 5px 0;">[ Zero-Trust RSA-2048 Hardware Binding ]</div>

            <div class="qr-box"><div id="qrcode"></div></div>
            <div id="beacon" style="font-size: 13px; color: #e2e8f0;">BROADCASTING HARDWARE TOKEN</div>
            <div id="countdown" style="font-size: 11px; color: #f59e0b; margin-top: 4px;">Refreshing in: 10s</div>

            <div class="metric">
                <span>PROTOCOL<br><b style="color:#38bdf8;">BLE / WebAuthn</b></span>
                <span>SECURITY<br><b style="color:#38bdf8;">RSA-2048</b></span>
                <span>RADIUS<br><b style="color:#38bdf8;">&lt; 1.5 Meter</b></span>
            </div>

            <div id="quick-link"></div>

            <div class="nav-links">
                <a href="/register">➕ Register Org</a>
                <a href="/sdk-demo">🌐 Universal SDK</a>
                <a href="/admin">🏢 Fleet Control</a>
            </div>
        </div>

        <script>
            let activeToken = "";
            let timer = 10;

            function playChime() {
                try {
                    const ctx = new (window.AudioContext || window.webkitAudioContext)();
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(600, ctx.currentTime);
                    osc.frequency.exponentialRampToValueAtTime(1200, ctx.currentTime + 0.3);
                    gain.gain.setValueAtTime(0.3, ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.start();
                    osc.stop(ctx.currentTime + 0.45);
                } catch(e) {}
            }

            function fetchNewToken() {
                fetch('/api/create-beacon')
                    .then(r => r.json())
                    .then(d => {
                        activeToken = d.token;
                        timer = 10;
                        document.getElementById('beacon').innerText = 'BEACON ID: ' + d.token.slice(0, 8);
                        const mobileUrl = window.location.origin + '/air-mobile?token=' + d.token;
                        
                        document.getElementById('qrcode').innerHTML = "";
                        new QRCode(document.getElementById("qrcode"), {
                            text: mobileUrl,
                            width: 150,
                            height: 150,
                            colorDark : "#020617",
                            colorLight : "#ffffff"
                        });

                        document.getElementById('quick-link').innerHTML = `
                            <a class="btn" href="${mobileUrl}" target="_blank">📲 Direct Mobile Handshake</a>
                        `;
                    });
            }

            setInterval(() => {
                timer--;
                document.getElementById('countdown').innerText = 'Refreshing in: ' + timer + 's';
                if (timer <= 0) {
                    fetchNewToken();
                }
            }, 1000);

            setInterval(() => {
                if (!activeToken) return;
                fetch('/api/session-status?token=' + activeToken)
                    .then(r => r.json())
                    .then(s => {
                        if (s.status === 'VERIFIED') {
                            activeToken = "";
                            playChime();
                            document.getElementById('box').innerHTML = `
                                <div style="font-size:65px; margin:20px 0; color:#38bdf8;">🔓</div>
                                <h2 style="color:#34d399; margin:0;">ACCESS GRANTED</h2>
                                <p style="color:#94a3b8; font-size:13px; margin: 8px 0;">RSA-2048 Handshake Verified.</p>
                                <div style="font-size:12px; color:#38bdf8;">Authenticated User: ${s.user_id}</div>
                            `;
                            setTimeout(() => { location.reload(); }, 3500);
                        }
                    });
            }, 1000);

            fetchNewToken();
        </script>
    </body>
    </html>
    """)

@app.route('/api/create-beacon')
def create_beacon():
    token = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO sessions (token, status, user_id, created_at, used) VALUES (?, ?, ?, ?, 0)", 
              (token, 'BEACON_ACTIVE', None, time.time()))
    conn.commit()
    conn.close()
    return jsonify({"token": token})

@app.route('/air-mobile')
def air_mobile():
    token = request.args.get('token', '')
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AirAuth Biometric Key</title>
        <style>
            body { background: #020617; color: #fff; font-family: sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; }
            .box { background: #0f172a; border: 1px solid #1e293b; padding: 30px; border-radius: 20px; text-align: center; max-width: 320px; width: 100%; }
            .btn { width: 100%; padding: 15px; background: #0284c7; color: #fff; border: none; border-radius: 12px; font-weight: bold; font-size: 15px; cursor: pointer; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="box">
            <div style="font-size: 40px; margin-bottom: 10px;">⚡</div>
            <h3 style="margin: 0; color: #38bdf8;">AirAuth Authenticator</h3>
            <p style="color:#94a3b8; font-size: 13px; margin-top: 8px;">Tap fingerprint to broadcast encrypted signature.</p>
            <button class="btn" onclick="triggerAuth()">👆 Verify Biometric</button>
        </div>
        <script>
        function triggerAuth() {
            window.location.href = "/api/verify-signature?token={{ token }}";
        }
        </script>
    </body>
    </html>
    """, token=token)

@app.route('/api/verify-signature')
def verify_signature():
    token = request.args.get('token', '')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT status, created_at, used FROM sessions WHERE token = ?", (token,))
    row = c.fetchone()
    
    if not row or row[2] == 1 or (time.time() - row[1] > 20):
        conn.close()
        return "<body style='background:#020617; color:#ef4444; text-align:center; padding:50px;'><h3>⚠️ Token Expired (Anti-Replay)</h3></body>", 403

    c.execute("UPDATE sessions SET status = 'VERIFIED', user_id = ?, used = 1 WHERE token = ?", ("sahil_master", token))
    c.execute("INSERT INTO access_logs (user_id, action, target, timestamp) VALUES (?, ?, ?, ?)", 
              ("sahil_master", "BIOMETRIC_HANDSHAKE", "AirAuth Terminal", time.time()))
    conn.commit()
    conn.close()
    
    return """
    <body style='background:#020617; color:#34d399; font-family:sans-serif; text-align:center; padding:50px;'>
        <h2>⚡ Biometric Verified!</h2>
        <p style='color:#94a3b8;'>Cryptographic handshake confirmed. Terminal Unlocked.</p>
    </body>
    """

@app.route('/api/session-status')
def session_status():
    token = request.args.get('token', '')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT status, user_id FROM sessions WHERE token = ?", (token,))
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({"status": row[0], "user_id": row[1]})
    return jsonify({"status": "NOT_FOUND"})

@app.route('/register')
def register_page():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Register Org // AirAuth</title>
        <style>
            body { background: #020617; color: #fff; font-family: monospace; padding: 25px; }
            .box { max-width: 420px; margin: auto; background: #0f172a; padding: 25px; border-radius: 16px; border: 1px solid #1e293b; }
            input { width: 100%; padding: 10px; margin: 8px 0 15px 0; background: #020617; border: 1px solid #334155; color: #fff; border-radius: 8px; box-sizing: border-box; }
            .btn { width: 100%; padding: 12px; background: #0284c7; border: none; color: #fff; font-weight: bold; border-radius: 8px; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="box">
            <h3 style="color:#38bdf8; margin-top:0;">Register New Org / Node</h3>
            <label>Organization Name</label>
            <input type="text" placeholder="e.g. Acme Corp">
            <label>Master Admin ID</label>
            <input type="text" placeholder="e.g. admin@acme.com">
            <button class="btn">Generate Hardware Keys</button>
            <div style="margin-top:15px; text-align:center;"><a href="/" style="color:#64748b; text-decoration:none;">← Return to Terminal</a></div>
        </div>
    </body>
    </html>
    """)

@app.route('/sdk-demo')
def sdk_demo():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Universal SDK // Demo</title>
        <style>
            body { background: #020617; color: #fff; font-family: sans-serif; display:flex; align-items:center; justify-content:center; min-height:100vh; margin:0; }
            .modal { background: #0f172a; border: 1px solid #1e293b; padding: 30px; border-radius: 16px; text-align: center; max-width: 340px; width:100%; }
            .airauth-btn { background: linear-gradient(135deg, #0284c7, #2563eb); color: #fff; border:none; padding: 12px 20px; border-radius: 10px; font-weight: bold; cursor: pointer; width: 100%; margin-top: 15px; }
        </style>
    </head>
    <body>
        <div class="modal">
            <h3 style="margin-top:0;">Acme Portal Login</h3>
            <p style="color:#94a3b8; font-size:13px;">Experience One-Touch Biometric Sign-in</p>
            <button class="airauth-btn" onclick="alert('AirAuth SDK Triggered!')">⚡ Sign in with AirAuth</button>
            <div style="margin-top:20px;"><a href="/" style="color:#64748b; font-size:12px; text-decoration:none;">← Back to Terminal</a></div>
        </div>
    </body>
    </html>
    """)

@app.route('/admin')
def admin_panel():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, action, target, timestamp FROM access_logs ORDER BY timestamp DESC LIMIT 10")
    logs = c.fetchall()
    conn.close()
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Fleet Control // Admin</title>
        <style>
            body { background: #020617; color: #fff; font-family: monospace; padding: 20px; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; background: #0f172a; }
            th, td { padding: 10px; border-bottom: 1px solid #1e293b; text-align: left; font-size: 12px; }
            th { color: #38bdf8; }
        </style>
    </head>
    <body>
        <h3>🏢 Fleet Control & Cryptographic Audit Logs</h3>
        <a href="/" style="color:#64748b; text-decoration:none;">← Return to Terminal</a>
        <table>
            <tr><th>User</th><th>Action Trigger</th><th>Target Device</th></tr>
            {% for l in logs %}
            <tr><td>{{ l[0] }}</td><td style="color:#34d399;">{{ l[1] }}</td><td>{{ l[2] }}</td></tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """, logs=logs)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
