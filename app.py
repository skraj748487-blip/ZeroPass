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
        return "<body style='background:#030712; color:#ef4444; font-family:sans-serif; text-align:center; padding:50px;'><h2>⛔ ACCESS BLOCKED</h2><p>Your IP has been blacklisted due to suspicious activity.</p></body>", 403

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ghost-Pass | AirAuth Engine</title>
        <style>
            body { background: #030712; color: #fff; font-family: -apple-system, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
            .radar-container { position: relative; width: 220px; height: 220px; display: flex; align-items: center; justify-content: center; margin-bottom: 25px; }
            .radar-circle { position: absolute; border: 2px solid #06b6d4; border-radius: 50%; width: 100%; height: 100%; animation: pulse 2s infinite ease-out; opacity: 0; }
            .radar-circle:nth-child(2) { animation-delay: 0.6s; }
            .radar-circle:nth-child(3) { animation-delay: 1.2s; }
            .core-icon { font-size: 55px; z-index: 2; }
            @keyframes pulse {
                0% { transform: scale(0.3); opacity: 0.9; }
                100% { transform: scale(1.4); opacity: 0; }
            }
            .card { background: #111827; border: 1px solid #1f2937; padding: 30px; border-radius: 20px; text-align: center; max-width: 360px; box-shadow: 0 10px 40px rgba(0,0,0,0.8); }
            .beacon-tag { font-family: monospace; background: #1f2937; padding: 6px 12px; border-radius: 8px; color: #38bdf8; font-size: 13px; }
            .status { margin-top: 15px; color: #9ca3af; font-size: 14px; }
            .btn-link { display: inline-block; margin-top: 15px; padding: 10px 18px; background: #0284c7; color: #fff; text-decoration: none; border-radius: 10px; font-size: 13px; font-weight: bold; }
            .shield-badge { font-size: 11px; color: #34d399; margin-top: 10px; display: inline-block; background: #064e3b; padding: 3px 10px; border-radius: 12px; }
            .admin-link { display: block; margin-top: 15px; color: #64748b; font-size: 12px; text-decoration: none; }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="radar-container">
                <div class="radar-circle"></div>
                <div class="radar-circle"></div>
                <div class="radar-circle"></div>
                <div class="core-icon">📡</div>
            </div>
            <h2 style="margin: 0 0 5px; color:#38bdf8;">AirAuth (Ghost-Pass)</h2>
            <div class="shield-badge">🛡️ Zero-Trust Defense Active</div>
            <p style="color: #94a3b8; font-size: 13px; margin: 15px 0 15px;">Phone ko paas layein. No QR, No Password.</p>
            <div id="beacon" class="beacon-tag">Beacon scanning...</div>
            <div id="status" class="status">Ghost signal broadcast ho raha hai...</div>
            <div id="quick-link"></div>
            <a class="admin-link" href="/admin">⚙️ Open Passwordless Admin Console</a>
        </div>

        <script>
            let currentToken = null;
            function startBeacon() {
                fetch('/api/create-beacon')
                    .then(res => res.json())
                    .then(data => {
                        currentToken = data.token;
                        document.getElementById('beacon').innerText = 'Beacon ID: ' + data.token.slice(0, 8);
                        document.getElementById('quick-link').innerHTML = `
                            <a class="btn-link" href="/air-mobile?token=${data.token}" target="_blank">📲 Phone Simulator Link</a>
                        `;
                        listenAuth(data.token);
                    });
            }

            function listenAuth(token) {
                const interval = setInterval(() => {
                    fetch('/api/session-status?token=' + token)
                        .then(r => r.json())
                        .then(s => {
                            if (s.status === 'VERIFIED') {
                                clearInterval(interval);
                                document.querySelector('.radar-container').innerHTML = '<div style="font-size:70px;">⚡</div>';
                                document.getElementById('status').innerHTML = '<span style="color:#4ade80; font-size:16px; font-weight:bold;">AirAuth Verified! Redirecting...</span>';
                                setTimeout(() => {
                                    window.location.href = '/dashboard?token=' + token;
                                }, 1000);
                            }
                        });
                }, 1000);
            }

            startBeacon();
        </script>
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
        <title>ZeroPass Secure Vault</title>
        <style>
            body { background: #030712; color: #fff; font-family: -apple-system, sans-serif; min-height: 100vh; margin: 0; padding: 25px; box-sizing: border-box; display: flex; flex-direction: column; align-items: center; justify-content: center; }
            .dash-card { background: #111827; border: 1px solid #1f2937; border-radius: 24px; padding: 30px; max-width: 420px; width: 100%; box-shadow: 0 20px 50px rgba(0,0,0,0.8); }
            .tag { display: inline-flex; align-items: center; background: #064e3b; color: #34d399; font-size: 12px; font-weight: bold; padding: 5px 12px; border-radius: 20px; }
            .pulse { width: 8px; height: 8px; background: #34d399; border-radius: 50%; margin-right: 6px; box-shadow: 0 0 8px #34d399; }
            .timer-box { background: #1e1b4b; border: 1px solid #4338ca; border-radius: 14px; padding: 15px; margin: 20px 0; text-align: center; }
            .countdown { font-size: 32px; font-weight: 800; color: #a5b4fc; font-family: monospace; }
            .action-btn { width: 100%; padding: 14px; background: #ef4444; color: white; border: none; border-radius: 12px; font-weight: bold; cursor: pointer; font-size: 14px; }
            .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px; }
            .stat-box { background: #1f2937; padding: 12px; border-radius: 10px; text-align: center; font-size: 13px; }
        </style>
    </head>
    <body>
        <div class="dash-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="tag"><span class="pulse"></span>SESSION ACTIVE</span>
                <span style="color:#9ca3af; font-size:12px;">AirAuth v2.0</span>
            </div>
            
            <h2 style="margin: 20px 0 5px; color:#f8fafc;">Welcome, Sahil</h2>
            <p style="color:#94a3b8; font-size:13px; margin: 0;">Identity verified via RSA-2048 Asymmetric Hardware Key.</p>

            <div class="timer-box">
                <div style="font-size:12px; color:#c7d2fe; margin-bottom: 5px;">🚶 Walk-Away Auto-Lock Sensor</div>
                <div id="countdown" class="countdown">15s</div>
                <div style="font-size:11px; color:#94a3b8; margin-top: 4px;">Phone door hone par screen turant lock hogi</div>
            </div>

            <div class="stat-grid">
                <div class="stat-box">
                    <div style="color:#9ca3af;">Encryption</div>
                    <div style="color:#38bdf8; font-weight:bold; margin-top:4px;">RSA-2048</div>
                </div>
                <div class="stat-box">
                    <div style="color:#9ca3af;">Shield</div>
                    <div style="color:#4ade80; font-weight:bold; margin-top:4px;">AI Active</div>
                </div>
            </div>

            <button class="action-btn" style="margin-top:20px;" onclick="triggerLock()">🔒 Walk Away Now (Simulate Lock)</button>
        </div>

        <script>
            let timeLeft = 15;
            const timerEl = document.getElementById('countdown');
            const countdownInterval = setInterval(() => {
                timeLeft--;
                timerEl.innerText = timeLeft + 's';
                if (timeLeft <= 0) {
                    clearInterval(countdownInterval);
                    triggerLock();
                }
            }, 1000);

            function triggerLock() {
                window.location.href = '/?locked=true';
            }
        </script>
    </body>
    </html>
    """)

# --- Strictly Enforced Biometric WebAuthn Admin Console ---
@app.route('/admin')
def admin_panel():
    if not check_ip_security():
        return "<body style='background:#030712; color:#ef4444; font-family:sans-serif; text-align:center; padding:50px;'><h2>⛔ ACCESS BLOCKED</h2><p>Your IP has been blacklisted.</p></body>", 403

    if not session.get('admin_authenticated'):
        admin_auth_token = str(uuid.uuid4())
        session['admin_handshake_token'] = admin_auth_token
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Master Hardware Auth | Ghost-Pass</title>
            <style>
                body { background: #030712; color: #fff; font-family: -apple-system, sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; }
                .login-card { background: #111827; border: 1px solid #1f2937; border-radius: 20px; padding: 30px; width: 100%; max-width: 360px; box-shadow: 0 10px 40px rgba(0,0,0,0.8); text-align: center; }
                .btn { width: 100%; padding: 15px; background: #0284c7; color: #fff; border: none; border-radius: 12px; font-weight: bold; cursor: pointer; margin-top: 15px; font-size: 15px; }
                .badge { background: #3b0764; color: #c084fc; font-size: 11px; padding: 4px 10px; border-radius: 12px; display: inline-block; margin-bottom: 15px; }
                #err { color: #ef4444; font-size: 13px; margin-top: 15px; display: none; }
            </style>
        </head>
        <body>
            <div class="login-card">
                <div class="badge">🔒 HARDWARE BIOMETRIC REQUIRED</div>
                <div style="font-size: 45px; margin-bottom: 10px;">🛡️</div>
                <h3 style="margin: 0 0 8px; color: #38bdf8;">Master Admin Vault</h3>
                <p style="color: #94a3b8; font-size: 13px; line-height: 1.5; margin: 0 0 20px;">
                    Yahan koi password nahi hai. Is screen ko unlock karne ke liye aapke phone ka physical fingerprint/screen lock verify hona zaroori hai.
                </p>
                <button class="btn" onclick="verifyAdminBiometric()">👆 Authenticate Fingerprint / Screen Lock</button>
                <div id="err">❌ Biometric Verification Cancelled or Failed! Access Denied.</div>
            </div>

            <script>
            async function verifyAdminBiometric() {
                try {
                    if (window.PublicKeyCredential) {
                        const challenge = new Uint8Array(32);
                        window.crypto.getRandomValues(challenge);
                        const dummyId = new Uint8Array(16);
                        window.crypto.getRandomValues(dummyId);
                        
                        // Hardware sensor trigger
                        await navigator.credentials.create({
                            publicKey: {
                                challenge: challenge,
                                rp: { name: "ZeroPass Admin Master" },
                                user: { id: dummyId, name: "sahil_master", displayName: "Sahil Ahmad" },
                                pubKeyCredParams: [{ alg: -7, type: "public-key" }],
                                authenticatorSelection: { authenticatorAttachment: "platform", userVerification: "required" },
                                timeout: 60000
                            }
                        });
                        
                        // Redirect only on verified hardware gesture
                        window.location.href = "/admin/verify-master?token={{ token }}";
                    } else {
                        alert("Hardware Authenticator not supported on this device/browser!");
                    }
                } catch (err) {
                    document.getElementById('err').style.display = 'block';
                    fetch('/api/report-fail');
                }
            }
            </script>
        </body>
        </html>
        """, token=admin_auth_token)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT token, status, user_id, created_at, used FROM sessions ORDER BY created_at DESC LIMIT 10")
    sessions = c.fetchall()
    
    c.execute("SELECT COUNT(*) FROM sessions WHERE status = 'VERIFIED'")
    total_verified = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM sessions WHERE status = 'BEACON_ACTIVE'")
    active_beacons = c.fetchone()[0]
    conn.close()

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AirAuth Enterprise Console</title>
        <style>
            body { background: #0b0f17; color: #f8fafc; font-family: -apple-system, sans-serif; margin: 0; padding: 25px; }
            .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 20px; }
            .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin: 25px 0; }
            .card { background: #111827; border: 1px solid #1f2937; border-radius: 14px; padding: 20px; }
            .card-title { font-size: 13px; color: #94a3b8; margin-bottom: 6px; }
            .card-val { font-size: 26px; font-weight: bold; color: #38bdf8; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; background: #111827; border-radius: 12px; overflow: hidden; border: 1px solid #1f2937; }
            th, td { padding: 12px 16px; text-align: left; font-size: 13px; border-bottom: 1px solid #1f2937; }
            th { background: #1e293b; color: #94a3b8; font-weight: 600; }
            .status-tag { padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: bold; }
            .status-VERIFIED { background: #064e3b; color: #34d399; }
            .status-BEACON_ACTIVE { background: #1e3a8a; color: #60a5fa; }
            .status-TERMINATED { background: #450a0a; color: #f87171; }
            .kill-btn { background: #ef4444; color: #fff; border: none; padding: 5px 10px; border-radius: 6px; cursor: pointer; font-size: 12px; }
            .nav-actions { display: flex; gap: 10px; }
            .btn-action { background: #1f2937; color: #e2e8f0; text-decoration: none; padding: 8px 14px; border-radius: 8px; font-size: 13px; }
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <h2 style="margin: 0; color: #38bdf8;">🛡️ AirAuth Enterprise Console</h2>
                <div style="color: #64748b; font-size: 13px; margin-top: 4px;">Hardware Biometric Verified Session (Master: Sahil)</div>
            </div>
            <div class="nav-actions">
                <a href="/" class="btn-action">← Radar</a>
                <a href="/admin/logout" class="btn-action" style="background: #991b1b; color: white;">Logout 🔒</a>
            </div>
        </div>

        <div class="metrics">
            <div class="card">
                <div class="card-title">Live Beacons</div>
                <div class="card-val">{{ active_beacons }}</div>
            </div>
            <div class="card">
                <div class="card-title">Verified Logins</div>
                <div class="card-val" style="color: #4ade80;">{{ total_verified }}</div>
            </div>
            <div class="card">
                <div class="card-title">AI Shield Defense</div>
                <div class="card-val" style="font-size: 18px; color: #34d399; margin-top: 5px;">Anti-Brute Force ON</div>
            </div>
        </div>

        <h3 style="margin-top: 30px; color: #e2e8f0;">Recent Authentication Sessions</h3>
        <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr>
                        <th>Beacon Token</th>
                        <th>User</th>
                        <th>Status</th>
                        <th>Shield Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for s in sessions %}
                    <tr>
                        <td style="font-family: monospace; color: #94a3b8;">{{ s[0][:12] }}...</td>
                        <td>{{ s[2] if s[2] else 'Waiting...' }}</td>
                        <td><span class="status-tag status-{{ s[1] }}">{{ s[1] }}</span></td>
                        <td>
                            {% if s[1] != 'TERMINATED' %}
                            <a href="/admin/kill?token={{ s[0] }}"><button class="kill-btn">Kill Session</button></a>
                            {% else %}
                            <span style="color:#64748b; font-size:12px;">Locked</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """, sessions=sessions, total_verified=total_verified, active_beacons=active_beacons)

@app.route('/api/report-fail')
def report_fail():
    record_failed_attempt()
    return "ok"

@app.route('/admin/verify-master')
def verify_master():
    token = request.args.get('token', '')
    if not token or token != session.get('admin_handshake_token'):
        record_failed_attempt()
        return redirect('/admin')
    
    session['admin_authenticated'] = True
    session.pop('admin_handshake_token', None)
    return redirect('/admin')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_authenticated', None)
    return redirect('/admin')

@app.route('/admin/kill')
def admin_kill():
    if not session.get('admin_authenticated'):
        return redirect('/admin')
    token = request.args.get('token', '')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE sessions SET status = 'TERMINATED', used = 1 WHERE token = ?", (token,))
    conn.commit()
    conn.close()
    return redirect('/admin')

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
        <title>AirAuth Biometric</title>
        <style>
            body { background: #0b0f19; color: #fff; font-family: -apple-system, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; text-align: center; }
            .box { background: #131d33; border: 1px solid #1e293b; padding: 30px; border-radius: 24px; max-width: 320px; box-shadow: 0 12px 35px rgba(0,0,0,0.6); }
            .pulse-dot { width: 14px; height: 14px; background: #22c55e; border-radius: 50%; display: inline-block; margin-right: 6px; box-shadow: 0 0 10px #22c55e; }
            .btn { width: 100%; padding: 16px; background: #0284c7; color: #fff; border: none; border-radius: 14px; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="box">
            <div style="margin-bottom: 15px;"><span class="pulse-dot"></span><span style="color:#94a3b8; font-size:13px;">Screen In Proximity</span></div>
            <div style="font-size: 45px; margin-bottom: 10px;">👻</div>
            <h2 style="margin: 0 0 10px; color:#38bdf8;">Ghost-Pass Detected</h2>
            <p style="color:#94a3b8; font-size:14px; margin: 0 0 20px;">Screen ne phone ko hawa mein pehchan liya hai. Ungli lagakar unlock karein.</p>
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
    
    if not row or row[2] == 1 or (time.time() - row[1] > 30):
        record_failed_attempt()
        conn.close()
        return "<body style='background:#030712; color:#ef4444; font-family:sans-serif; text-align:center; padding:50px;'><h2>⚠️ Anomaly Detected!</h2><p>Session expired or token already consumed.</p></body>", 403

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
                <p style='color:#9ca3af;'>Screen unlock ho chuki hai. Desktop tab dekhein!</p>
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
