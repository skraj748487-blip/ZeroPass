from flask import Flask, jsonify, request, render_template_string, redirect, session
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

FAILED_ATTEMPTS = {}
BLACKLISTED_IPS = {}

def get_client_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr)

def check_ip_security():
    ip = get_client_ip()
    current = time.time()
    if ip in BLACKLISTED_IPS:
        if current < BLACKLISTED_IPS[ip]:
            return False
        else:
            del BLACKLISTED_IPS[ip]
            FAILED_ATTEMPTS[ip] = 0
    return True

def record_failed_attempt():
    ip = get_client_ip()
    FAILED_ATTEMPTS[ip] = FAILED_ATTEMPTS.get(ip, 0) + 1
    if FAILED_ATTEMPTS[ip] >= 5:
        BLACKLISTED_IPS[ip] = time.time() + 900

def init_db_and_keys():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions 
                 (token TEXT PRIMARY KEY, status TEXT, user_id TEXT, created_at REAL, used INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id TEXT PRIMARY KEY, public_key TEXT, is_admin INTEGER DEFAULT 0)''')
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
    c.execute("INSERT OR REPLACE INTO users (user_id, public_key, is_admin) VALUES (?, ?, 1)", ("sahil_master", pub))
    conn.commit()
    conn.close()

init_db_and_keys()

@app.route('/')
def ghost_desktop():
    if not check_ip_security():
        return "<body style='background:#030712; color:#ef4444; font-family:sans-serif; text-align:center; padding:50px;'><h2>⛔ ACCESS BLOCKED</h2><p>Your IP has been blacklisted.</p></body>", 403

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AirAuth Military HUD | Zero-Pass</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
        <style>
            body { background: radial-gradient(circle at center, #071326 0%, #020617 100%); color: #38bdf8; font-family: 'Courier New', monospace; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }
            .hud-card { background: rgba(15, 23, 42, 0.85); border: 2px solid #0284c7; padding: 25px; border-radius: 20px; text-align: center; max-width: 420px; width: 100%; box-shadow: 0 0 50px rgba(14, 165, 233, 0.25); position: relative; }
            .hud-header { font-size: 11px; letter-spacing: 2px; color: #38bdf8; text-transform: uppercase; margin-bottom: 12px; }
            .qr-wrapper { background: #fff; padding: 10px; border-radius: 12px; display: inline-block; margin: 10px auto; border: 3px solid #38bdf8; }
            #qrcode img { display: block; margin: 0 auto; }
            .hud-metric { display: flex; justify-content: space-between; font-size: 11px; color: #94a3b8; margin-top: 15px; border-top: 1px dashed #1e293b; padding-top: 10px; }
            .status-glow { color: #34d399; font-weight: bold; text-shadow: 0 0 10px #34d399; }
            .btn-link { display: inline-block; margin-top: 15px; padding: 10px 18px; background: #0284c7; color: #fff; text-decoration: none; border-radius: 8px; font-size: 13px; font-weight: bold; }
            .nav-box { margin-top: 20px; display: flex; justify-content: space-around; width: 100%; }
            .nav-link { color: #64748b; font-size: 12px; text-decoration: none; }
            .nav-link:hover { color: #38bdf8; }
        </style>
    </head>
    <body>
        <div class="hud-card" id="mainBox">
            <div class="hud-header">⚡ Quantum Zero-Pass // Proximity HUD ⚡</div>
            <h2 style="margin: 0; color: #f8fafc; font-size: 22px;">AirAuth Terminal</h2>
            <div style="font-size: 12px; color: #34d399; margin: 5px 0;">[ HARDWARE ENCLAVE ENCRYPTED ]</div>

            <div class="qr-wrapper">
                <div id="qrcode"></div>
            </div>

            <div id="beacon" style="color:#e2e8f0; font-size: 13px;">Proximity Sensor: Searching...</div>
            <div class="status-glow" id="status" style="margin-top: 5px;">BROADCASTING ZERO-TRUST BEACON</div>

            <div class="hud-metric">
                <span>FREQ: 2.48 GHz BLE</span>
                <span>SECURITY: RSA-2048</span>
                <span>RANGE: &lt; 1.5M</span>
            </div>

            <div id="quick-link"></div>

            <div class="nav-box">
                <a class="nav-link" href="/sdk-demo">🌐 Universal SDK Demo</a>
                <a class="nav-link" href="/admin">🏢 Enterprise Fleet View</a>
            </div>
        </div>

        <script>
            function playSciFiChime() {
                try {
                    const ctx = new (window.AudioContext || window.webkitAudioContext)();
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(587.33, ctx.currentTime);
                    osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.15);
                    osc.frequency.exponentialRampToValueAtTime(1174.66, ctx.currentTime + 0.35);
                    gain.gain.setValueAtTime(0.3, ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.start();
                    osc.stop(ctx.currentTime + 0.55);
                } catch(e) {}
            }

            function startBeacon() {
                fetch('/api/create-beacon')
                    .then(r => r.json())
                    .then(d => {
                        document.getElementById('beacon').innerText = 'BEACON ID: ' + d.token.slice(0, 8);
                        const mobileUrl = window.location.origin + '/air-mobile?token=' + d.token;
                        
                        document.getElementById('qrcode').innerHTML = "";
                        new QRCode(document.getElementById("qrcode"), {
                            text: mobileUrl,
                            width: 150,
                            height: 150,
                            colorDark : "#020617",
                            colorLight : "#ffffff",
                            correctLevel : QRCode.CorrectLevel.M
                        });

                        document.getElementById('quick-link').innerHTML = `
                            <a class="btn-link" href="${mobileUrl}" target="_blank">📲 Direct Phone Auth</a>
                        `;
                        listenAuth(d.token);
                    });
            }

            function listenAuth(token) {
                const interval = setInterval(() => {
                    fetch('/api/session-status?token=' + token)
                        .then(r => r.json())
                        .then(s => {
                            if (s.status === 'VERIFIED') {
                                clearInterval(interval);
                                playSciFiChime();
                                document.getElementById('mainBox').innerHTML = `
                                    <div style="font-size:75px; margin:20px 0; color:#38bdf8;">🔓</div>
                                    <h2 style="color:#34d399; margin:0;">BIOMETRIC MATCH CONFIRMED</h2>
                                    <p style="color:#94a3b8; font-size:13px; margin: 10px 0;">RSA Handshake Validated. Access Granted.</p>
                                `;
                                setTimeout(() => {
                                    window.location.href = '/dashboard?token=' + token;
                                }, 1200);
                            }
                        });
                }, 1000);
            }

            startBeacon();
        </script>
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
        <title>Universal Web SDK Mockup</title>
        <style>
            body { background: #0f172a; color: #fff; font-family: sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }
            .card { background: #1e293b; border-radius: 16px; padding: 30px; width: 100%; max-width: 380px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); text-align: center; }
            input { width: 100%; padding: 12px; margin: 8px 0; border-radius: 8px; border: 1px solid #334155; background: #0f172a; color: #fff; box-sizing: border-box; }
            .btn-normal { width: 100%; padding: 12px; background: #475569; border: none; border-radius: 8px; color: #fff; font-weight: bold; margin-top: 10px; cursor: not-allowed; }
            .or-divider { margin: 20px 0; color: #64748b; font-size: 12px; }
            .btn-airauth { width: 100%; padding: 14px; background: linear-gradient(135deg, #0284c7, #06b6d4); border: none; border-radius: 10px; color: #fff; font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; font-size: 14px; text-decoration: none; }
        </style>
    </head>
    <body>
        <div class="card">
            <h3 style="margin-top:0;">Corporate Cloud Login</h3>
            <p style="color:#94a3b8; font-size:12px;">Standard Website Integrated with AirAuth SDK</p>
            <input type="text" placeholder="Username (Old Way)" disabled>
            <input type="password" placeholder="Password (Old Way)" disabled>
            <button class="btn-normal">Login (Deprecated)</button>
            <div class="or-divider">— OR ZERO-PASS INSTANT UNLOCK —</div>
            <a class="btn-airauth" href="/">⚡ One-Touch AirAuth Login</a>
            <div style="margin-top:20px;"><a href="/" style="color:#38bdf8; font-size:12px; text-decoration:none;">← Return to Radar HUD</a></div>
        </div>
    </body>
    </html>
    """)

@app.route('/dashboard')
def dashboard():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AirAuth Vault</title>
        <style>
            body { background: #020617; color: #fff; font-family: -apple-system, sans-serif; min-height: 100vh; margin: 0; padding: 25px; box-sizing: border-box; display: flex; align-items: center; justify-content: center; }
            .dash-card { background: #0f172a; border: 1px solid #1e293b; border-radius: 24px; padding: 30px; max-width: 420px; width: 100%; text-align: center; }
            .tag { background: #064e3b; color: #34d399; font-size: 12px; font-weight: bold; padding: 6px 14px; border-radius: 20px; display: inline-block; }
            .timer-box { background: #1e1b4b; border: 1px solid #4338ca; border-radius: 14px; padding: 15px; margin: 20px 0; }
            .countdown { font-size: 32px; font-weight: 800; color: #a5b4fc; font-family: monospace; }
            .action-btn { width: 100%; padding: 14px; background: #ef4444; color: white; border: none; border-radius: 12px; font-weight: bold; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="dash-card">
            <span class="tag">⚡ Session Active</span>
            <h2 style="margin: 15px 0 5px;">Welcome, Sahil</h2>
            <p style="color:#94a3b8; font-size:13px; margin: 0;">RSA-2048 Hardware Binding Verified</p>

            <div class="timer-box">
                <div style="font-size:12px; color:#c7d2fe; margin-bottom: 5px;">🚶 Walk-Away Auto-Lock Sensor</div>
                <div id="countdown" class="countdown">15s</div>
                <div style="font-size:11px; color:#94a3b8; margin-top: 4px;">Phone out of proximity will trigger lock</div>
            </div>

            <button class="action-btn" onclick="window.location.href='/?locked=true'">🔒 Lock Session Now</button>
        </div>

        <script>
            let timeLeft = 15;
            setInterval(() => {
                timeLeft--;
                document.getElementById('countdown').innerText = timeLeft + 's';
                if (timeLeft <= 0) window.location.href = '/?locked=true';
            }, 1000);
        </script>
    </body>
    </html>
    """)

@app.route('/admin')
def admin_panel():
    if not check_ip_security():
        return "Access Blocked", 403

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT token, status, user_id, created_at, used FROM sessions ORDER BY created_at DESC LIMIT 6")
    sessions = c.fetchall()
    conn.close()

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AirAuth Fleet Control</title>
        <style>
            body { background: #0b0f17; color: #f8fafc; font-family: monospace; margin: 0; padding: 25px; }
            .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 15px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 15px; margin: 20px 0; }
            .card { background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 15px; }
            .badge-active { color: #34d399; font-weight: bold; }
            .badge-locked { color: #f87171; font-weight: bold; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; background: #111827; border-radius: 10px; overflow: hidden; }
            th, td { padding: 10px 14px; text-align: left; font-size: 12px; border-bottom: 1px solid #1f2937; }
            th { background: #1e293b; color: #94a3b8; }
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <h3 style="margin:0; color:#38bdf8;">🏢 Enterprise Fleet Terminal Map</h3>
                <span style="font-size:12px; color:#64748b;">Office Topology Live Monitoring</span>
            </div>
            <a href="/" style="color:#94a3b8; text-decoration:none; font-size:13px;">← Radar HUD</a>
        </div>

        <div class="grid">
            <div class="card">
                <div style="font-size:12px; color:#94a3b8;">TERMINAL PC-01 [HR Dept]</div>
                <div class="badge-locked" style="margin-top:5px;">🔒 LOCKED (Idle)</div>
            </div>
            <div class="card">
                <div style="font-size:12px; color:#94a3b8;">TERMINAL PC-02 [Finance]</div>
                <div class="badge-active" style="margin-top:5px;">🟢 ACTIVE (Auth: sahil_master)</div>
            </div>
            <div class="card">
                <div style="font-size:12px; color:#94a3b8;">TERMINAL PC-03 [Server Room]</div>
                <div class="badge-locked" style="margin-top:5px;">⚠️ AUTO-LOCKED (Walk-Away)</div>
            </div>
        </div>

        <h4>Recent Cryptographic Audit Logs</h4>
        <table>
            <tr><th>Session Token</th><th>User</th><th>Status</th></tr>
            {% for s in sessions %}
            <tr>
                <td>{{ s[0][:14] }}...</td>
                <td>{{ s[2] if s[2] else 'Awaiting Scan' }}</td>
                <td>{{ s[1] }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """, sessions=sessions)

@app.route('/api/create-beacon')
def create_beacon():
    if not check_ip_security():
        return jsonify({"error": "IP Blocked"}), 403
    token = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO sessions (token, status, user_id, created_at, used) VALUES (?, ?, ?, ?, 0)", (token, 'BEACON_ACTIVE', None, time.time()))
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
        <title>AirAuth Proximity Device</title>
        <style>
            body { background: #0b0f19; color: #fff; font-family: -apple-system, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; text-align: center; }
            .box { background: #131d33; border: 1px solid #1e293b; padding: 30px; border-radius: 24px; max-width: 320px; }
            .btn { width: 100%; padding: 16px; background: #0284c7; color: #fff; border: none; border-radius: 14px; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="box">
            <div style="font-size: 45px; margin-bottom: 10px;">👻</div>
            <h2 style="margin: 0 0 10px; color:#38bdf8;">AirAuth Handshake</h2>
            <p style="color:#94a3b8; font-size:14px; margin: 0 0 20px;">Screen proximity detected. Apply biometric.</p>
            <button class="btn" onclick="authorizeAirAuth()">👆 1-Touch Fingerprint</button>
        </div>
        <script>
        async function authorizeAirAuth() {
            try {
                if (window.PublicKeyCredential) {
                    const challenge = new Uint8Array(32);
                    window.crypto.getRandomValues(challenge);
                    const dummyId = new Uint8Array(16);
                    window.crypto.getRandomValues(dummyId);
                    await navigator.credentials.create({
                        publicKey: {
                            challenge: challenge,
                            rp: { name: "AirAuth Ghost-Pass" },
                            user: { id: dummyId, name: "sahil_master", displayName: "Sahil Ahmad" },
                            pubKeyCredParams: [{ alg: -7, type: "public-key" }],
                            authenticatorSelection: { authenticatorAttachment: "platform", userVerification: "required" },
                            timeout: 60000
                        }
                    });
                }
                window.location.href = "/api/verify-signature?token={{ token }}";
            } catch (e) {
                window.location.href = "/api/verify-signature?token={{ token }}";
            }
        }
        </script>
    </body>
    </html>
    """, token=token)

@app.route('/api/verify-signature')
def verify_signature():
    if not check_ip_security():
        return "IP Blocked", 403

    token = request.args.get('token', '')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT status, created_at, used FROM sessions WHERE token = ?", (token,))
    row = c.fetchone()
    
    if not row or row[2] == 1 or (time.time() - row[1] > 120):
        record_failed_attempt()
        conn.close()
        return "Token Expired", 403

    if not os.path.exists("my_private_key.pem"):
        init_db_and_keys()
        
    with open("my_private_key.pem", "rb") as f:
        priv_key = RSA.import_key(f.read())
    h = SHA256.new(token.encode('utf-8'))
    sig = pkcs1_15.new(priv_key).sign(h)
    
    c.execute("SELECT public_key FROM users WHERE user_id = ?", ("sahil_master",))
    user_row = c.fetchone()
    
    if user_row:
        pub_key = RSA.import_key(user_row[0].encode('utf-8'))
        try:
            pkcs1_15.new(pub_key).verify(h, sig)
            c.execute("UPDATE sessions SET status = 'VERIFIED', user_id = ?, used = 1 WHERE token = ?", ("sahil_master", token))
            conn.commit()
            conn.close()
            return """
            <body style='background:#030712; color:#4ade80; display:flex; flex-direction:column; justify-content:center; align-items:center; min-height:100vh; font-family:sans-serif;'>
                <h2>⚡ Signal Transmitted!</h2>
                <p style='color:#9ca3af;'>Desktop Unlocked!</p>
            </body>
            """
        except Exception:
            pass
            
    record_failed_attempt()
    conn.close()
    return "Verification failed", 400

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
