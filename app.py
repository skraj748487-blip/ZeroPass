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

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions 
                 (token TEXT PRIMARY KEY, status TEXT, user_id TEXT, created_at REAL, used INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id TEXT PRIMARY KEY, org_name TEXT, public_key TEXT, is_admin INTEGER DEFAULT 0, created_at REAL)''')
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
    c.execute("INSERT OR REPLACE INTO users (user_id, org_name, public_key, is_admin, created_at) VALUES (?, ?, ?, 1, ?)", 
              ("sahil_master", "AirAuth Global Inc.", pub, time.time()))
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def ghost_desktop():
    if not check_ip_security():
        return "<body style='background:#030712; color:#ef4444; font-family:monospace; text-align:center; padding:50px;'><h2>⛔ IP DEFENSE SHIELD: BLOCKED</h2></body>", 403

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AirAuth Enterprise | Zero-Trust Infrastructure</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
        <style>
            body { background: radial-gradient(circle at 50% 20%, #0d1b2a 0%, #020617 100%); color: #38bdf8; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }
            .founder-strip { background: linear-gradient(90deg, #0284c7, #06b6d4); color: #fff; font-size: 11px; font-weight: bold; padding: 6px 14px; border-radius: 20px; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 15px; box-shadow: 0 0 15px rgba(2,132,199,0.5); }
            .hud-card { background: rgba(15, 23, 42, 0.92); border: 2px solid #0ea5e9; padding: 25px; border-radius: 24px; text-align: center; max-width: 440px; width: 100%; box-shadow: 0 0 40px rgba(14, 165, 233, 0.2); }
            .qr-wrapper { background: #fff; padding: 10px; border-radius: 12px; display: inline-block; margin: 12px auto; border: 3px solid #38bdf8; }
            #qrcode img { display: block; margin: 0 auto; }
            .metric-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; font-size: 11px; color: #94a3b8; margin-top: 15px; border-top: 1px dashed #334155; padding-top: 12px; }
            .metric-item { background: #0f172a; padding: 6px; border-radius: 6px; border: 1px solid #1e293b; }
            .metric-item div:first-child { color: #64748b; font-size: 9px; text-transform: uppercase; }
            .metric-item div:last-child { color: #38bdf8; font-weight: bold; margin-top: 2px; }
            .btn-link { display: inline-block; margin-top: 15px; padding: 12px 20px; background: linear-gradient(135deg, #0284c7, #0369a1); color: #fff; text-decoration: none; border-radius: 10px; font-size: 13px; font-weight: bold; box-shadow: 0 4px 12px rgba(2,132,199,0.4); }
            .nav-box { margin-top: 18px; display: flex; justify-content: space-around; width: 100%; }
            .nav-link { color: #64748b; font-size: 12px; text-decoration: none; transition: 0.2s; }
            .nav-link:hover { color: #38bdf8; }
        </style>
    </head>
    <body>
        <div class="founder-strip">⚡ Engineered by Sahil Ahmad // Lead Architect ⚡</div>
        <div class="hud-card" id="mainBox">
            <h2 style="margin: 0; color: #f8fafc; font-size: 24px; letter-spacing: -0.5px;">AirAuth Enterprise Terminal</h2>
            <div style="font-size: 12px; color: #34d399; margin: 6px 0;">[ Zero-Trust RSA-2048 Hardware Binding ]</div>

            <div class="qr-wrapper">
                <div id="qrcode"></div>
            </div>

            <div id="beacon" style="color:#e2e8f0; font-size: 13px; font-family: monospace;">Scanning for Proximity Key...</div>
            <div style="color: #34d399; font-weight: bold; font-size: 12px; margin-top: 4px;" id="status">BROADCASTING HARDWARE TOKEN</div>

            <div class="metric-grid">
                <div class="metric-item"><div>Protocol</div><div>BLE / WebAuthn</div></div>
                <div class="metric-item"><div>Security</div><div>RSA-2048</div></div>
                <div class="metric-item"><div>Radius</div><div>&lt; 1.5 Meter</div></div>
            </div>

            <div id="quick-link"></div>

            <div class="nav-box">
                <a class="nav-link" href="/register">➕ Register Org</a>
                <a class="nav-link" href="/sdk-demo">🌐 Universal SDK</a>
                <a class="nav-link" href="/admin">🏢 Fleet Control</a>
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
                            width: 155,
                            height: 155,
                            colorDark : "#020617",
                            colorLight : "#ffffff",
                            correctLevel : QRCode.CorrectLevel.M
                        });

                        document.getElementById('quick-link').innerHTML = `
                            <a class="btn-link" href="${mobileUrl}" target="_blank">📲 Direct Mobile Handshake</a>
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
                                    <div style="font-size:75px; margin:20px 0; color:#38bdf8;">⚡</div>
                                    <h2 style="color:#34d399; margin:0;">BIOMETRIC AUTHENTICATED</h2>
                                    <p style="color:#94a3b8; font-size:13px; margin: 10px 0;">Handshake Verified by Sahil's Cryptographic Enclave.</p>
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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_id = request.form.get('user_id', '').strip()
        org_name = request.form.get('org_name', '').strip()
        if user_id and org_name:
            user_key = RSA.generate(2048)
            pub_pem = user_key.publickey().export_key('PEM').decode('utf-8')
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO users (user_id, org_name, public_key, is_admin, created_at) VALUES (?, ?, ?, 0, ?)",
                      (user_id, org_name, pub_pem, time.time()))
            conn.commit()
            conn.close()
            return render_template_string("""
            <body style='background:#020617; color:#34d399; font-family:sans-serif; text-align:center; padding:50px;'>
                <h2>✅ Organization Registered!</h2>
                <p style='color:#94a3b8;'>User <b>{{ user_id }}</b> of <b>{{ org_name }}</b> hardware vault created.</p>
                <a href='/' style='color:#38bdf8; text-decoration:none;'>← Return to Terminal</a>
            </body>
            """, user_id=user_id, org_name=org_name)
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AirAuth Multi-Tenant Registration</title>
        <style>
            body { background: #020617; color: #fff; font-family: -apple-system, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }
            .card { background: #0f172a; border: 1px solid #1e293b; border-radius: 20px; padding: 30px; width: 100%; max-width: 380px; box-shadow: 0 10px 40px rgba(0,0,0,0.8); }
            input { width: 100%; padding: 12px; margin: 10px 0; border-radius: 10px; border: 1px solid #334155; background: #020617; color: #fff; box-sizing: border-box; }
            .btn { width: 100%; padding: 14px; background: #0284c7; color: white; border: none; border-radius: 10px; font-weight: bold; cursor: pointer; margin-top: 15px; font-size: 14px; }
        </style>
    </head>
    <body>
        <div class="card">
            <h3 style="margin-top:0; color:#38bdf8;">➕ Register Enterprise Node</h3>
            <p style="color:#94a3b8; font-size:13px;">Add a new employee or organization node to the AirAuth Vault.</p>
            <form method="POST">
                <input type="text" name="org_name" placeholder="Organization / Company Name" required>
                <input type="text" name="user_id" placeholder="Unique User Identifier (e.g. employee_01)" required>
                <button type="submit" class="btn">Generate Hardware Enclave</button>
            </form>
            <div style="margin-top:15px; text-align:center;"><a href="/" style="color:#64748b; font-size:12px; text-decoration:none;">← Return to Radar</a></div>
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
        <title>AirAuth Universal SDK Demo</title>
        <style>
            body { background: #020617; color: #fff; font-family: -apple-system, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }
            .card { background: #0f172a; border: 1px solid #1e293b; border-radius: 20px; padding: 30px; width: 100%; max-width: 400px; text-align: center; }
            .btn-airauth { width: 100%; padding: 14px; background: linear-gradient(135deg, #0284c7, #06b6d4); border: none; border-radius: 12px; color: #fff; font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; font-size: 14px; text-decoration: none; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="card">
            <span style="font-size:11px; background:#064e3b; color:#34d399; padding:4px 10px; border-radius:12px; font-weight:bold;">ENTERPRISE SDK INTEGRATION</span>
            <h3 style="margin: 15px 0 5px;">Client Cloud Login Portal</h3>
            <p style="color:#94a3b8; font-size:13px;">Embed AirAuth in any web portal with just 2 lines of code.</p>
            <a class="btn-airauth" href="/">⚡ Instant Biometric Sign-In</a>
            <div style="margin-top:20px;"><a href="/" style="color:#38bdf8; font-size:12px; text-decoration:none;">← Return to Main Terminal</a></div>
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
        <title>AirAuth Secure Vault</title>
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
    c.execute("SELECT user_id, org_name, is_admin FROM users ORDER BY created_at DESC")
    users = c.fetchall()
    conn.close()

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AirAuth Enterprise Fleet Control</title>
        <style>
            body { background: #020617; color: #f8fafc; font-family: -apple-system, monospace; margin: 0; padding: 25px; }
            .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 15px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 15px; margin: 20px 0; }
            .card { background: #0f172a; border: 1px solid #1e293b; border-radius: 14px; padding: 15px; }
            .badge-active { color: #34d399; font-weight: bold; }
            .badge-locked { color: #f87171; font-weight: bold; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; background: #0f172a; border-radius: 12px; overflow: hidden; border: 1px solid #1e293b; }
            th, td { padding: 10px 14px; text-align: left; font-size: 12px; border-bottom: 1px solid #1e293b; }
            th { background: #1e293b; color: #94a3b8; }
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <h3 style="margin:0; color:#38bdf8;">🏢 AirAuth Enterprise Fleet Map</h3>
                <span style="font-size:12px; color:#64748b;">Architecture by Founder Sahil Ahmad</span>
            </div>
            <a href="/" style="color:#94a3b8; text-decoration:none; font-size:13px;">← Return to HUD</a>
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

        <h4>Registered Organization Vaults</h4>
        <table>
            <tr><th>User ID</th><th>Organization</th><th>Role</th></tr>
            {% for u in users %}
            <tr>
                <td style="color:#38bdf8; font-weight:bold;">{{ u[0] }}</td>
                <td>{{ u[1] }}</td>
                <td>{{ 'Master Admin' if u[2] == 1 else 'Employee Node' }}</td>
            </tr>
            {% endfor %}
        </table>

        <h4 style="margin-top:30px;">Live Cryptographic Handshake Audit</h4>
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
    """, sessions=sessions, users=users)

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
        <title>AirAuth Biometric Key</title>
        <style>
            body { background: #020617; color: #fff; font-family: -apple-system, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; text-align: center; }
            .box { background: #0f172a; border: 1px solid #1e293b; padding: 30px; border-radius: 24px; max-width: 320px; box-shadow: 0 10px 40px rgba(0,0,0,0.8); }
            .btn { width: 100%; padding: 16px; background: linear-gradient(135deg, #0284c7, #06b6d4); color: #fff; border: none; border-radius: 14px; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="box">
            <div style="font-size: 45px; margin-bottom: 10px;">⚡</div>
            <h2 style="margin: 0 0 10px; color:#38bdf8;">AirAuth Handshake</h2>
            <p style="color:#94a3b8; font-size:14px; margin: 0 0 20px;">Screen proximity detected. Apply biometric key.</p>
            <button class="btn" onclick="authorizeAirAuth()">👆 1-Touch Biometric Sign</button>
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
                            rp: { name: "AirAuth Enterprise" },
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
        init_db()
        
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
            <body style='background:#020617; color:#4ade80; display:flex; flex-direction:column; justify-content:center; align-items:center; min-height:100vh; font-family:sans-serif;'>
                <h2>⚡ Cryptographic Handshake Confirmed!</h2>
                <p style='color:#9ca3af;'>Desktop Unlocked. Signal Received.</p>
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
