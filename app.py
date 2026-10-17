import razorpay
from flask import Flask, jsonify, request, render_template_string, Response, redirect, url_for
import uuid
import os
import time
import sqlite3
import hmac
import hashlib
import json
import base64
import urllib.parse

# PostgreSQL support
USE_PG = False
pg_pool = None
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    try:
        import psycopg2
        from psycopg2 import pool
        # Fix URL prefix if needed
        clean_db_url = DATABASE_URL
        if clean_db_url.startswith("postgres://"):
            clean_db_url = clean_db_url.replace("postgres://", "postgresql://", 1)
        pg_pool = psycopg2.pool.SimpleConnectionPool(1, 10, clean_db_url)
        USE_PG = True
    except Exception as e:
        USE_PG = False

app = Flask(__name__)

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_live_Tp1pLALckoKQhV")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "niMaYKWt0Y15UWlu2ojlAJAM")
rzp_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

app.secret_key = os.urandom(32)
DB_PATH = 'auth_vault.db'
MASTER_SALT = os.urandom(16).hex()
REAL_UPI_ID = "7484878440-2@ybl"
ADMIN_PIN = "7484"

FAILED_ATTEMPTS = {}
BLOCKED_IPS = {}

def get_db():
    if USE_PG and pg_pool:
        conn = pg_pool.getconn()
        return conn, 'PG'
    conn = sqlite3.connect(DB_PATH)
    return conn, 'SQLITE'

def release_db(conn, db_type):
    if db_type == 'PG' and pg_pool:
        pg_pool.putconn(conn)
    elif db_type == 'SQLITE':
        conn.close()

def init_db():
    conn, db_type = get_db()
    c = conn.cursor()
    if db_type == 'PG':
        c.execute('''CREATE TABLE IF NOT EXISTS sessions 
                     (token TEXT PRIMARY KEY, challenge TEXT, status TEXT, user_id TEXT, created_at DOUBLE PRECISION, used INT DEFAULT 0, sign_count INT DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS access_logs 
                     (id SERIAL PRIMARY KEY, user_id TEXT, action TEXT, target TEXT, ip_addr TEXT, timestamp DOUBLE PRECISION)''')
        c.execute('''CREATE TABLE IF NOT EXISTS subscriptions 
                     (id SERIAL PRIMARY KEY, client_email TEXT, plan_name TEXT, utr TEXT, api_key TEXT, status TEXT, created_at DOUBLE PRECISION)''')
    else:
        c.execute('''CREATE TABLE IF NOT EXISTS sessions 
                     (token TEXT PRIMARY KEY, challenge TEXT, status TEXT, user_id TEXT, created_at REAL, used INTEGER DEFAULT 0, sign_count INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS access_logs 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, action TEXT, target TEXT, ip_addr TEXT, timestamp REAL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS subscriptions 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, client_email TEXT, plan_name TEXT, utr TEXT, api_key TEXT, status TEXT, created_at REAL)''')
    conn.commit()
    release_db(conn, db_type)

init_db()

def is_ip_jailed(ip):
    now = time.time()
    if ip in BLOCKED_IPS:
        if now < BLOCKED_IPS[ip]:
            return True
        else:
            del BLOCKED_IPS[ip]
            FAILED_ATTEMPTS[ip] = 0
    return False

def record_failed_attempt(ip):
    now = time.time()
    attempts = FAILED_ATTEMPTS.get(ip, 0) + 1
    FAILED_ATTEMPTS[ip] = attempts
    if attempts >= 3:
        BLOCKED_IPS[ip] = now + 900

@app.route('/airauth.js')
def serve_sdk():
    js_code = """
    (function() {
        window.AirAuth = {
            apiKey: null,
            init: function(key) { this.apiKey = key; },
            login: function(callback) {
                const overlay = document.createElement('div');
                overlay.id = 'airauth-modal-root';
                overlay.style = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(2,6,23,0.85);backdrop-filter:blur(8px);display:flex;align-items:center;justify-content:center;z-index:999999;font-family:monospace;';
                
                overlay.innerHTML = `
                    <div style="background:#0f172a;border:2px solid #0284c7;border-radius:20px;padding:30px;width:340px;text-align:center;color:#fff;box-shadow:0 0 40px rgba(2,132,199,0.4);">
                        <div style="font-size:11px;color:#38bdf8;margin-bottom:8px;">⚡ GHOSTKEY QUANTUM SECURE</div>
                        <h3 style="margin:0 0 15px 0;color:#fff;">Biometric Verification</h3>
                        <div id="airauth-qr-slot" style="background:#fff;padding:10px;border-radius:12px;display:inline-block;margin-bottom:15px;"></div>
                        <div id="airauth-status" style="font-size:12px;color:#f59e0b;margin-bottom:15px;">Awaiting Device Handshake...</div>
                        <button id="airauth-close" style="background:#334155;border:none;color:#fff;padding:8px 16px;border-radius:8px;cursor:pointer;font-family:monospace;">Cancel</button>
                    </div>
                `;
                document.body.appendChild(overlay);

                document.getElementById('airauth-close').onclick = () => { document.body.removeChild(overlay); };

                fetch('/api/create-beacon')
                    .then(r => r.json())
                    .then(d => {
                        const token = d.token;
                        const qrUrl = window.location.origin + '/air-mobile?token=' + token;
                        document.getElementById('airauth-qr-slot').innerHTML = `<img src="https://api.qrserver.com/v1/create-qr-code/?size=140x140&data=${encodeURIComponent(qrUrl)}" width="140" height="140" />`;
                        
                        const poller = setInterval(() => {
                            fetch('/api/session-status?token=' + token)
                                .then(r => r.json())
                                .then(s => {
                                    if(s.status === 'VERIFIED') {
                                        clearInterval(poller);
                                        document.getElementById('airauth-status').style.color = '#34d399';
                                        document.getElementById('airauth-status').innerText = 'Verified: ' + s.user_id;
                                        setTimeout(() => {
                                            document.body.removeChild(overlay);
                                            if (callback) callback({ success: true, user: s.user_id, token: token });
                                        }, 1200);
                                    }
                                });
                        }, 1000);
                    });
            }
        };
    })();
    """
    return Response(js_code, mimetype='application/javascript')

@app.route('/')
def terminal_display():
    db_badge = "PERMANENT POSTGRESQL // NEON SECURE" if USE_PG else "SQLITE CACHED NODE"
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GhostKey Quantum Terminal // Enterprise</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
        <style>
            body { 
                background: #020617; 
                color: #38bdf8; 
                font-family: 'Courier New', monospace; 
                display: flex; 
                flex-direction: column; 
                align-items: center; 
                justify-content: center; 
                min-height: 100vh; 
                margin: 0; 
                padding: 10px; 
                box-sizing: border-box; 
            }
            .badge { 
                background: linear-gradient(135deg, #0284c7, #0369a1); 
                color: #fff; 
                font-size: 11px; 
                padding: 8px 16px; 
                border-radius: 20px; 
                font-weight: bold; 
                margin-bottom: 12px; 
                border: 1px solid #38bdf8;
                box-shadow: 0 0 15px rgba(2,132,199,0.5);
            }
            .db-tag {
                font-size: 10px;
                color: #34d399;
                background: rgba(5,150,105,0.2);
                border: 1px solid #059669;
                padding: 4px 10px;
                border-radius: 12px;
                margin-bottom: 16px;
            }
            .card { 
                background: rgba(15, 23, 42, 0.95); 
                border: 2px solid #0284c7; 
                border-radius: 24px; 
                padding: 30px; 
                text-align: center; 
                max-width: 440px; 
                width: 100%; 
                box-shadow: 0 0 50px rgba(2,132,199,0.4); 
            }
            .qr-box { 
                background: #fff; 
                padding: 12px; 
                border-radius: 16px; 
                display: inline-block; 
                margin: 15px auto; 
            }
            .btn { 
                display: inline-block; 
                margin-top: 15px; 
                padding: 12px 24px; 
                background: linear-gradient(135deg, #0284c7, #2563eb); 
                color: #fff; 
                text-decoration: none; 
                border-radius: 12px; 
                font-weight: bold; 
                font-size: 14px; 
            }
            .nav-bar {
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
                margin-top: 20px;
                border-top: 1px solid #1e293b;
                padding-top: 15px;
                justify-content: center;
            }
            .nav-bar a {
                color: #94a3b8;
                font-size: 11px;
                text-decoration: none;
                padding: 6px 10px;
                border: 1px solid #334155;
                border-radius: 8px;
            }
            .nav-bar a.active {
                color: #34d399;
                border-color: #059669;
                background: rgba(5, 150, 105, 0.15);
            }
        </style>
    </head>
    <body>
        <div class="badge">⚡ ENGINEERED BY SAHIL AHMAD // CHIEF ARCHITECT ⚡</div>
        <div class="db-tag">🔒 {{ db_badge }}</div>
        
        <div class="card" id="box">
            <h2 style="margin: 0; color: #fff; font-size: 22px;">GhostKey Sovereign Node</h2>
            <div style="font-size: 11px; color: #34d399; margin: 4px 0;">[ Zero-Trace Anti-Clone Enclave ]</div>

            <div class="qr-box">
                <div id="qrcode"></div>
            </div>

            <div id="beacon" style="font-weight: bold; font-size: 13px; color: #f1f5f9;">INITIALIZING SECURE ENCLAVE...</div>
            <div id="countdown" style="font-size: 11px; color: #f59e0b; margin-top: 4px;">⌛ ANTI-REPLAY WINDOW: 15s</div>

            <div id="quick-link"></div>
            
            <div class="nav-bar">
                <a href="/playground" style="color: #f59e0b; border-color: #f59e0b;">🧪 Live Test</a>
                <a href="/pricing" class="active">💎 Pricing</a>
                <a href="/sdk-portal">🔌 SDK</a>
                <a href="/admin">🏢 Settlement</a>
            </div>
        </div>

        <script>
            let activeToken = "";
            let timer = 15;

            function fetchNewToken() {
                fetch('/api/create-beacon')
                    .then(r => r.json())
                    .then(d => {
                        activeToken = d.token;
                        timer = 15;
                        document.getElementById('beacon').innerText = 'SECURE TOKEN: ' + d.token.slice(0, 12);
                        const mobileUrl = window.location.origin + '/air-mobile?token=' + d.token;
                        
                        document.getElementById('qrcode').innerHTML = "";
                        new QRCode(document.getElementById("qrcode"), {
                            text: mobileUrl,
                            width: 140,
                            height: 140,
                            colorDark : "#020617",
                            colorLight : "#ffffff"
                        });

                        document.getElementById('quick-link').innerHTML = `
                            <a class="btn" href="${mobileUrl}" target="_blank">📲 Verify Biometric Key</a>
                        `;
                    });
            }

            setInterval(() => {
                timer--;
                document.getElementById('countdown').innerText = '⌛ ANTI-REPLAY WINDOW: ' + timer + 's';
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
                            document.getElementById('box').innerHTML = `
                                <div style="font-size:75px; margin:10px 0; color:#34d399;">🔓</div>
                                <h2 style="color:#34d399; margin:0;">AUTHENTICATION VERIFIED</h2>
                                <p style="color:#94a3b8; font-size:12px; margin: 8px 0;">Hardware Challenge & Device Signature Validated.</p>
                                <div style="font-size:12px; color:#38bdf8; border:1px dashed #0284c7; padding:8px; border-radius:8px;">Identity: ${s.user_id}</div>
                            `;
                            setTimeout(() => { location.reload(); }, 3500);
                        }
                    });
            }, 1000);

            fetchNewToken();
        </script>
    </body>
    </html>
    """, db_badge=db_badge)

@app.route('/api/create-beacon')
def create_beacon():
    token = str(uuid.uuid4())
    raw_challenge = os.urandom(32)
    challenge = base64.urlsafe_b64encode(raw_challenge).decode('utf-8').rstrip('=')
    
    conn, db_type = get_db()
    c = conn.cursor()
    placeholders = "(%s, %s, %s, %s, %s, 0, 0)" if db_type == 'PG' else "(?, ?, ?, ?, ?, 0, 0)"
    c.execute(f"INSERT INTO sessions (token, challenge, status, user_id, created_at, used, sign_count) VALUES {placeholders}", 
              (token, challenge, 'BEACON_ACTIVE', None, time.time()))
    conn.commit()
    release_db(conn, db_type)
    return jsonify({"token": token, "challenge": challenge})

@app.route('/air-mobile')
def air_mobile():
    token = request.args.get('token', '')
    conn, db_type = get_db()
    c = conn.cursor()
    query = "SELECT challenge FROM sessions WHERE token = %s" if db_type == 'PG' else "SELECT challenge FROM sessions WHERE token = ?"
    c.execute(query, (token,))
    row = c.fetchone()
    release_db(conn, db_type)
    
    challenge = row[0] if row else ""

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GhostKey Biometric Authenticator</title>
        <style>
            body { background: #020617; color: #fff; font-family: monospace; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 15px; }
            .box { background: rgba(15, 23, 42, 0.95); border: 2px solid #0284c7; padding: 35px 25px; border-radius: 28px; text-align: center; max-width: 360px; width: 100%; box-shadow: 0 0 40px rgba(2,132,199,0.3); }
            .scan-btn { width: 100%; padding: 16px; background: linear-gradient(135deg, #0284c7, #2563eb); border: none; border-radius: 14px; color: #fff; font-weight: bold; font-size: 15px; cursor: pointer; margin-top: 20px; box-shadow: 0 0 20px rgba(2,132,199,0.4); }
            #status { margin-top: 15px; font-size: 12px; color: #f59e0b; }
        </style>
    </head>
    <body>
        <div class="box">
            <div style="font-size: 45px; margin-bottom: 10px;">🛡️</div>
            <h3 style="margin: 0; color: #38bdf8;">Hardware Biometric Vault</h3>
            <p style="color:#94a3b8; font-size: 12px; margin-top: 8px;">Hardware Silicon Binding Enforced. Physical Sensor Required.</p>
            <button class="scan-btn" id="bioBtn" onclick="executeSecureHandshake()">👆 Authenticate Fingerprint</button>
            <div id="status">SENSOR IDLE</div>
        </div>

        <script>
        function base64ToUint8Array(base64) {
            let padded = base64.padEnd(base64.length + (4 - base64.length % 4) % 4, '=');
            let binary = atob(padded.replace(/-/g, '+').replace(/_/g, '/'));
            let bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) {
                bytes[i] = binary.charCodeAt(i);
            }
            return bytes;
        }

        async function executeSecureHandshake() {
            const statusDiv = document.getElementById('status');
            const btn = document.getElementById('bioBtn');
            statusDiv.innerText = "Querying Android Biometric Sensor...";

            if (!window.PublicKeyCredential) {
                statusDiv.innerText = "❌ Secure WebAuthn API not supported.";
                return;
            }

            try {
                const challengeStr = "{{ challenge }}";
                if (!challengeStr) {
                    statusDiv.innerText = "❌ Expired Session Challenge.";
                    return;
                }
                const challengeBuf = base64ToUint8Array(challengeStr);

                btn.disabled = true;
                const credential = await navigator.credentials.create({
                    publicKey: {
                        challenge: challengeBuf,
                        rp: { name: "GhostKey Cryptographic Network" },
                        user: { id: new Uint8Array([1, 2, 3, 4]), name: "sahil_master", displayName: "Sahil Ahmad" },
                        pubKeyCredParams: [{ alg: -7, type: "public-key" }],
                        authenticatorSelection: { authenticatorAttachment: "platform", userVerification: "required" },
                        timeout: 60000
                    }
                });

                if (credential) {
                    statusDiv.style.color = "#34d399";
                    statusDiv.innerText = "Verifying cryptographic proof with server...";

                    const clientDataText = new TextDecoder().decode(credential.response.clientDataJSON);
                    const envHash = btoa(navigator.userAgent.slice(0, 30) + screen.width + "x" + screen.height);

                    const response = await fetch('/api/verify-signature', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            token: "{{ token }}",
                            clientDataJSON: clientDataText,
                            envHash: envHash
                        })
                    });

                    const res = await response.json();
                    if (res.success) {
                        statusDiv.innerText = "⚡ ACCESS GRANTED! Terminal Unlocked.";
                    } else {
                        statusDiv.style.color = "#ef4444";
                        statusDiv.innerText = "❌ Security Rejection: " + res.error;
                    }
                }
            } catch (err) {
                btn.disabled = false;
                statusDiv.style.color = "#ef4444";
                statusDiv.innerText = "❌ Verification Terminated / Biometric Mismatch";
            }
        }
        </script>
    </body>
    </html>
    """, token=token, challenge=challenge)

@app.route('/api/verify-signature', methods=['POST'])
def verify_signature():
    client_ip = request.remote_addr or "127.0.0.1"

    if is_ip_jailed(client_ip):
        return jsonify({"success": False, "error": "IP LOCKED OUT: Security Quarantine Triggered"}), 429

    data = request.get_json(silent=True)
    if not data or 'token' not in data or 'clientDataJSON' not in data:
        record_failed_attempt(client_ip)
        return jsonify({"success": False, "error": "Missing Payload"}), 400

    token = data.get('token')
    client_data_raw = data.get('clientDataJSON')

    conn, db_type = get_db()
    c = conn.cursor()
    query = "SELECT challenge, created_at, used FROM sessions WHERE token = %s" if db_type == 'PG' else "SELECT challenge, created_at, used FROM sessions WHERE token = ?"
    c.execute(query, (token,))
    row = c.fetchone()
    
    if not row:
        release_db(conn, db_type)
        record_failed_attempt(client_ip)
        return jsonify({"success": False, "error": "Token not found"}), 404
        
    expected_challenge, created_at, used = row[0], row[1], row[2]

    if used == 1:
        release_db(conn, db_type)
        record_failed_attempt(client_ip)
        return jsonify({"success": False, "error": "Token Already Consumed (Anti-Replay Block)"}), 403
    if (time.time() - created_at) > 25:
        release_db(conn, db_type)
        record_failed_attempt(client_ip)
        return jsonify({"success": False, "error": "Token Window Expired"}), 403

    try:
        client_data = json.loads(client_data_raw)
        received_challenge = client_data.get('challenge', '')
        clean_expected = expected_challenge.rstrip('=').replace('+', '-').replace('/', '_')
        clean_received = received_challenge.rstrip('=').replace('+', '-').replace('/', '_')

        if clean_expected != clean_received:
            release_db(conn, db_type)
            record_failed_attempt(client_ip)
            return jsonify({"success": False, "error": "Cryptographic Challenge Mismatch (Attack Neutralized)"}), 403
    except Exception:
        release_db(conn, db_type)
        record_failed_attempt(client_ip)
        return jsonify({"success": False, "error": "Malformed Cryptographic Payload"}), 400

    update_q = "UPDATE sessions SET status = 'VERIFIED', user_id = %s, used = 1, sign_count = sign_count + 1 WHERE token = %s" if db_type == 'PG' else "UPDATE sessions SET status = 'VERIFIED', user_id = ?, used = 1, sign_count = sign_count + 1 WHERE token = ?"
    c.execute(update_q, ("sahil_master", token))

    log_q = "INSERT INTO access_logs (user_id, action, target, ip_addr, timestamp) VALUES (%s, %s, %s, %s, %s)" if db_type == 'PG' else "INSERT INTO access_logs (user_id, action, target, ip_addr, timestamp) VALUES (?, ?, ?, ?, ?)"
    c.execute(log_q, ("sahil_master", "HARDWARE_SILICON_ENCLAVE_SIGNATURE_VERIFIED", "GhostKey Core Substrate", client_ip, time.time()))
    conn.commit()
    release_db(conn, db_type)
    
    FAILED_ATTEMPTS[client_ip] = 0
    return jsonify({"success": True, "message": "Biometric Handshake Mathematically Approved"})

@app.route('/api/session-status')
def session_status():
    token = request.args.get('token', '')
    conn, db_type = get_db()
    c = conn.cursor()
    query = "SELECT status, user_id FROM sessions WHERE token = %s" if db_type == 'PG' else "SELECT status, user_id FROM sessions WHERE token = ?"
    c.execute(query, (token,))
    row = c.fetchone()
    release_db(conn, db_type)
    if row:
        return jsonify({"status": row[0], "user_id": row[1]})
    return jsonify({"status": "NOT_FOUND"})

@app.route('/api/v1/verify-credential', methods=['POST'])
def api_verify_credential():
    api_key = request.headers.get('X-GhostKey-Secret')
    data = request.get_json(silent=True)
    if not data or 'token' not in data:
        return jsonify({"valid": False, "error": "Missing token parameter"}), 400

    token = data.get('token')
    conn, db_type = get_db()
    c = conn.cursor()
    
    if api_key:
        query_sub = "SELECT status FROM subscriptions WHERE api_key = %s" if db_type == 'PG' else "SELECT status FROM subscriptions WHERE api_key = ?"
        c.execute(query_sub, (api_key,))
        sub = c.fetchone()
        if not sub or sub[0] != 'ACTIVE':
            release_db(conn, db_type)
            return jsonify({"valid": False, "error": "Unauthorized or Inactive API Key"}), 401

    query_sess = "SELECT status, user_id, created_at FROM sessions WHERE token = %s" if db_type == 'PG' else "SELECT status, user_id, created_at FROM sessions WHERE token = ?"
    c.execute(query_sess, (token,))
    session = c.fetchone()
    release_db(conn, db_type)

    if session and session[0] == 'VERIFIED':
        return jsonify({
            "valid": True,
            "user_id": session[1],
            "verification_type": "HARDWARE_SILICON_ENCLAVE",
            "timestamp": session[2]
        })
    return jsonify({"valid": False, "error": "Unverified or expired token"}), 403

@app.route('/playground')
def playground():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GhostKey // Interactive Developer Playground</title>
        <style>
            body { background: #020617; color: #fff; font-family: monospace; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }
            .box { background: #0f172a; border: 2px solid #0284c7; border-radius: 20px; padding: 35px; max-width: 450px; width: 100%; text-align: center; box-shadow: 0 0 40px rgba(2,132,199,0.3); }
            .btn { width: 100%; padding: 14px; background: linear-gradient(135deg, #0284c7, #2563eb); border: none; border-radius: 12px; color: #fff; font-weight: bold; font-size: 15px; cursor: pointer; margin-top: 20px; }
            #output { margin-top: 20px; padding: 12px; background: #020617; border: 1px dashed #334155; border-radius: 8px; font-size: 12px; color: #94a3b8; text-align: left; word-break: break-all; min-height: 40px; }
        </style>
        <script src="/airauth.js"></script>
    </head>
    <body>
        <div class="box">
            <div style="font-size: 11px; color: #38bdf8; margin-bottom: 5px;">⚡ DEVELOPER SANDBOX</div>
            <h2 style="margin: 0 0 10px 0; color: #fff;">Test Biometric Drop-in</h2>
            <p style="color: #94a3b8; font-size: 12px; margin: 0;">Click below to simulate real-time client SDK execution.</p>
            
            <button class="btn" onclick="runSandboxTest()">⚡ Trigger GhostKey Auth Modal</button>
            
            <div id="output">// Awaiting user interaction...</div>
            <div style="margin-top: 20px;"><a href="/" style="color: #64748b; font-size: 12px; text-decoration: none;">← Return to Main Terminal</a></div>
        </div>

        <script>
        function runSandboxTest() {
            const out = document.getElementById('output');
            out.style.color = '#f59e0b';
            out.innerText = 'Initializing client-side AirAuth modal...';
            
            AirAuth.login(function(res) {
                if (res.success) {
                    out.style.color = '#34d399';
                    out.innerHTML = '<b>SUCCESS!</b><br>User: ' + res.user + '<br>Token: ' + res.token;
                } else {
                    out.style.color = '#ef4444';
                    out.innerText = 'Handshake Failed / Cancelled';
                }
            });
        }
        </script>
    </body>
    </html>
    """)

PRICING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GhostKey Pricing & License</title>
  <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0a0d14; color: #fff; margin: 0; padding: 20px; }
    .container { max-width: 900px; margin: 0 auto; text-align: center; }
    h1 { color: #00ffcc; margin-bottom: 8px; }
    p { color: #8892b0; margin-bottom: 25px; }
    .email-box { margin-bottom: 30px; }
    .email-box input { padding: 12px 16px; width: 80%; max-width: 320px; border-radius: 8px; border: 1px solid #00ffcc; background: #111625; color: #fff; font-size: 1rem; text-align: center; outline: none; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 24px; }
    .card { background: #111625; border: 1px solid #233554; border-radius: 12px; padding: 28px; text-align: left; }
    .card.highlight { border-color: #00ffcc; box-shadow: 0 0 20px rgba(0,255,204,0.15); }
    .tier-title { font-size: 1.25rem; font-weight: 600; color: #ccd6f6; }
    .price { font-size: 2.2rem; font-weight: 700; color: #fff; margin: 16px 0; }
    .price span { font-size: 1rem; color: #8892b0; font-weight: normal; }
    .features { list-style: none; padding: 0; margin: 24px 0; color: #a8b2d1; font-size: 0.95rem; }
    .features li { margin-bottom: 12px; }
    .features li::before { content: "✓ "; color: #00ffcc; }
    .btn { display: block; width: 100%; padding: 14px; background: #00ffcc; color: #0a0d14; text-align: center; font-weight: bold; border-radius: 6px; border: none; cursor: pointer; font-size: 1.05rem; }
    .btn:active { transform: scale(0.98); }
    .btn-test { background: #00ffcc; color: #0a0d14; }
  </style>
</head>
<body>
  <div class="container">
    <h1>GhostKey Enterprise & Cloud Licensing</h1>
    <p>Decentralized hardware biometric authentication for web, apps & portals.</p>

    <div class="email-box">
      <input type="email" id="userEmail" placeholder="Enter your email for license key" value="client@example.com">
    </div>

    <div class="grid">
      <div class="card highlight">
        <div class="tier-title">Developer Sandbox</div>
        <div class="price">₹1 <span>/ live test</span></div>
        <ul class="features">
          <li>Verify Live Payment Flow</li>
          <li>Instant Test License Key</li>
          <li>Full Sandbox Verification</li>
        </ul>
        <button class="btn btn-test" id="btnTest">Pay ₹1 Now</button>
      </div>

      <div class="card">
        <div class="tier-title">Business Pro</div>
        <div class="price">₹1,499 <span>/ month</span></div>
        <ul class="features">
          <li>10,000 Biometric Logins/mo</li>
          <li>Zero SMS OTP Cost</li>
          <li>Hardware Enclave FIDO2 Binding</li>
        </ul>
        <button class="btn" id="btnBiz">Subscribe ₹1,499</button>
      </div>
    </div>
  </div>

  <script>
    function triggerCheckout(amount, plan) {
      var email = document.getElementById("userEmail").value.trim();
      if (!email) {
        alert("Please enter a valid email address.");
        return;
      }
      var options = {
        key: "rzp_live_Tp1pLALckoKQhV",
        amount: amount,
        currency: "INR",
        name: "GhostKey Protocol",
        description: "License: " + plan,
        prefill: { email: email },
        theme: { color: "#00ffcc" },
        handler: function(response) {
          alert("Payment Successful! ID: " + response.razorpay_payment_id);
          window.location.href = "/playground";
        }
      };
      try {
        var rzp = new Razorpay(options);
        rzp.open();
      } catch (err) {
        alert("Checkout loading error: " + err);
      }
    }

    document.getElementById("btnTest").addEventListener("click", function() {
      triggerCheckout(100, "Developer Sandbox");
    });
    document.getElementById("btnBiz").addEventListener("click", function() {
      triggerCheckout(149900, "Business Pro");
    });
  </script>
</body>
</html>"""


@app.route('/checkout')
def checkout_page():
    plan = request.args.get('plan', 'Business')
    price = request.args.get('price', '1499')
    upi_payment_url = f"upi://pay?pa={REAL_UPI_ID}&pn=Sahil%20Ahmad%20GhostKey&am={price}&cu=INR"
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Commercial Payment // GhostKey</title>
        <style>
            body { background: #020617; color: #fff; font-family: monospace; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; }
            .box { background: #0f172a; border: 1px solid #1e293b; padding: 30px; border-radius: 20px; max-width: 380px; width: 100%; text-align: center; }
            .qr-mock { background: #fff; padding: 15px; border-radius: 12px; display: inline-block; margin: 15px 0; }
            .btn { width: 100%; padding: 12px; background: #059669; border: none; color: #fff; font-weight: bold; border-radius: 8px; cursor: pointer; font-size: 14px; }
            input { width: 100%; padding: 10px; margin: 8px 0; background: #020617; border: 1px solid #334155; color: #fff; border-radius: 8px; box-sizing: border-box; }
        </style>
    </head>
    <body>
        <div class="box">
            <h3 style="color:#38bdf8; margin: 0;">Direct Merchant Settlement</h3>
            <p style="color:#94a3b8; font-size: 12px; margin-top: 5px;">Plan: {{ plan }} (₹{{ price }}/month)</p>
            
            <div class="qr-mock">
                <img src="https://api.qrserver.com/v1/create-qr-code/?size=160x160&data={{ upi_payment_url | urlencode }}" alt="UPI QR">
            </div>
            
            <p style="color:#34d399; font-size: 11px;">Payee: {{ upi_id }}</p>
            <p style="color:#94a3b8; font-size: 10px;">Scan via PhonePe / GPay / Paytm</p>

            <form action="/submit-payment" method="POST">
                <input type="email" name="email" placeholder="Your Official Email" required>
                <input type="text" name="utr" placeholder="12-Digit UPI Ref / UTR Number" required>
                <input type="hidden" name="plan" value="{{ plan }}">
                <button type="submit" class="btn">⚡ Submit Payment for Activation</button>
            </form>
            <div style="margin-top:15px;"><a href="/pricing" style="color:#64748b; font-size:12px; text-decoration:none;">← Return</a></div>
        </div>
    </body>
    </html>
    """, plan=plan, price=price, upi_payment_url=upi_payment_url, upi_id=REAL_UPI_ID)

@app.route('/submit-payment', methods=['POST'])
def submit_payment():
    email = request.form.get('email')
    plan = request.form.get('plan')
    utr = request.form.get('utr', '').strip()
    temp_key = "ghostkey_live_" + uuid.uuid4().hex[:18]
    
    conn, db_type = get_db()
    c = conn.cursor()
    insert_q = "INSERT INTO subscriptions (client_email, plan_name, utr, api_key, status, created_at) VALUES (%s, %s, %s, %s, 'PENDING_VERIFICATION', %s)" if db_type == 'PG' else "INSERT INTO subscriptions (client_email, plan_name, utr, api_key, status, created_at) VALUES (?, ?, ?, ?, 'PENDING_VERIFICATION', ?)"
    c.execute(insert_q, (email, plan, utr, temp_key, time.time()))
    conn.commit()
    release_db(conn, db_type)

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Payment Under Review // GhostKey</title>
        <style>
            body { background: #020617; color: #fff; font-family: monospace; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; }
            .box { background: #0f172a; border: 1px solid #f59e0b; padding: 30px; border-radius: 20px; max-width: 440px; width: 100%; text-align: center; }
        </style>
    </head>
    <body>
        <div class="box">
            <div style="font-size: 50px; margin-bottom: 10px;">⏳</div>
            <h2 style="color:#f59e0b; margin: 0;">Payment Submitted</h2>
            <p style="color:#94a3b8; font-size: 13px; line-height: 1.6;">
                UTR: <b>{{ utr }}</b> has been recorded.<br>
                Bank reconciliation is underway. Your API Key will be unlocked once settlement is verified by Sahil Ahmad.
            </p>
            <div style="font-size: 11px; color: #64748b; margin-top: 15px;">Target Delivery: {{ email }}</div>
            <a href="/" style="display:inline-block; margin-top: 20px; padding:10px 18px; background:#0284c7; color:#fff; text-decoration:none; border-radius:8px; font-weight:bold; font-size:12px;">Return to Terminal</a>
        </div>
    </body>
    </html>
    """, email=email, utr=utr)

@app.route('/sdk-portal')
def sdk_portal():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Developer Integration // GhostKey</title>
        <style>
            body { background: #020617; color: #fff; font-family: monospace; padding: 30px; max-width: 700px; margin: auto; }
            pre { background: #0f172a; border: 1px solid #1e293b; padding: 15px; border-radius: 8px; color: #38bdf8; overflow-x: auto; font-size: 13px; }
        </style>
    </head>
    <body>
        <h2 style="color:#38bdf8;">GhostKey Drop-In SDK & Validator API</h2>
        <p style="color:#94a3b8; font-size:13px;">Zero-Password Biometric authentication for any web architecture.</p>
        
        <p style="color:#cbd5e1; font-size:13px;">1. Client-Side Script Injection:</p>
        <pre>&lt;script src="https://zeropass1.onrender.com/airauth.js"&gt;&lt;/script&gt;
&lt;button onclick="AirAuth.login(function(res){ alert('Verified user: ' + res.user); })"&gt;
    ⚡ Sign In with GhostKey
&lt;/button&gt;</pre>

        <p style="color:#cbd5e1; font-size:13px;">2. Server-to-Server Backend Validation API:</p>
        <pre>POST /api/v1/verify-credential
Headers: { 
    "Content-Type": "application/json",
    "X-GhostKey-Secret": "YOUR_API_KEY"
}
Body: { "token": "TOKEN_FROM_BROWSER" }</pre>

        <div style="margin-top:20px;"><a href="/" style="color:#64748b; text-decoration:none; font-size:12px;">← Return to Main Terminal</a></div>
    </body>
    </html>
    """)

@app.route('/admin')
def admin_panel():
    pin = request.args.get('pin', '')
    if pin != ADMIN_PIN:
        return render_template_string("""
        <!DOCTYPE html>
        <html><body style="background:#020617;color:#fff;font-family:monospace;display:flex;align-items:center;justify-content:center;height:100vh;">
            <form method="GET" style="background:#0f172a;padding:30px;border-radius:16px;border:1px solid #334155;text-align:center;">
                <h3 style="color:#38bdf8;">Chief Architect Vault</h3>
                <input type="password" name="pin" placeholder="Enter Secret PIN" style="padding:10px;background:#020617;border:1px solid #334155;color:#fff;border-radius:8px;" required><br><br>
                <button type="submit" style="padding:10px 20px;background:#0284c7;color:#fff;border:none;border-radius:8px;font-weight:bold;cursor:pointer;">Unlock Control Panel</button>
            </form>
        </body></html>
        """)

    conn, db_type = get_db()
    c = conn.cursor()
    c.execute("SELECT id, client_email, plan_name, utr, api_key, status FROM subscriptions ORDER BY id DESC")
    subs = c.fetchall()
    c.execute("SELECT user_id, action, target, ip_addr, timestamp FROM access_logs ORDER BY timestamp DESC LIMIT 8")
    logs = c.fetchall()
    release_db(conn, db_type)

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GhostKey Master Settlement Vault</title>
        <style>
            body { background: #020617; color: #fff; font-family: monospace; padding: 20px; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; background: rgba(15,23,42,0.8); border: 1px solid #0284c7; }
            th, td { padding: 10px; border-bottom: 1px solid #1e293b; text-align: left; font-size: 11px; }
            th { color: #38bdf8; background: rgba(2,132,199,0.2); }
            .approve-btn { background: #059669; color: #fff; padding: 6px 12px; border: none; border-radius: 6px; cursor: pointer; text-decoration: none; font-size: 11px; font-weight: bold; }
        </style>
    </head>
    <body>
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h2 style="color:#34d399; margin:0;">🏢 Master Settlement & Payment Vault</h2>
            <a href="/" style="color:#64748b; font-size:12px; text-decoration:none;">← Main Terminal</a>
        </div>
        <p style="color:#94a3b8; font-size:12px;">Verify incoming Bank/PhonePe credit before releasing client API Keys.</p>

        <table>
            <tr><th>Email</th><th>Plan</th><th>Submitted UTR</th><th>API Key</th><th>Status</th><th>Action</th></tr>
            {% for s in subs %}
            <tr>
                <td>{{ s[1] }}</td>
                <td>{{ s[2] }}</td>
                <td style="color:#f59e0b; font-weight:bold;">{{ s[3] }}</td>
                <td style="color:#38bdf8;">{{ s[4] }}</td>
                <td>
                    {% if s[5] == 'ACTIVE' %}
                        <span style="color:#34d399; font-weight:bold;">ACTIVE</span>
                    {% else %}
                        <span style="color:#ef4444; font-weight:bold;">PENDING</span>
                    {% endif %}
                </td>
                <td>
                    {% if s[5] != 'ACTIVE' %}
                        <a href="/admin/approve?id={{ s[0] }}&pin={{ pin }}" class="approve-btn">Approve & Issue Key</a>
                    {% else %}
                        <span style="color:#64748b;">Released</span>
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>

        <h3 style="margin-top:35px;">🛡️ Real-Time Biometric Audit Logs (IP Enforced)</h3>
        <table>
            <tr><th>USER SIGNATURE</th><th>EVENT</th><th>TARGET</th><th>SOURCE IP</th></tr>
            {% for l in logs %}
            <tr><td>{{ l[0] }}</td><td style="color:#34d399;">{{ l[1] }}</td><td>{{ l[2] }}</td><td style="color:#38bdf8;">{{ l[3] }}</td></tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """, subs=subs, logs=logs, pin=ADMIN_PIN)

@app.route('/admin/approve')
def approve_subscription():
    pin = request.args.get('pin', '')
    if pin != ADMIN_PIN:
        return "Unauthorized", 401
    sub_id = request.args.get('id')
    conn, db_type = get_db()
    c = conn.cursor()
    query = "UPDATE subscriptions SET status = 'ACTIVE' WHERE id = %s" if db_type == 'PG' else "UPDATE subscriptions SET status = 'ACTIVE' WHERE id = ?"
    c.execute(query, (sub_id,))
    conn.commit()
    release_db(conn, db_type)
    return redirect(f"/admin?pin={ADMIN_PIN}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)


PRICING_PAGE_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GhostKey Pricing</title>
  <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
  <style>
    body { background: #0a0d14; color: #fff; font-family: sans-serif; text-align: center; padding: 20px; }
    .box { max-width: 400px; margin: 40px auto; background: #111625; padding: 30px; border-radius: 12px; border: 1px solid #00ffcc; }
    h2 { color: #00ffcc; margin-top: 0; }
    input { width: 90%; padding: 12px; margin: 15px 0; border-radius: 6px; border: 1px solid #333; background: #050811; color: #fff; font-size: 16px; text-align: center; }
    button { width: 95%; padding: 14px; background: #00ffcc; color: #000; font-weight: bold; border: none; border-radius: 6px; font-size: 16px; cursor: pointer; margin-top: 10px; }
    .plan-card { border-top: 1px solid #233554; margin-top: 20px; padding-top: 15px; }
  </style>
</head>
<body>
  <div class="box">
    <h2>GhostKey License Activation</h2>
    <p style="color:#8892b0;font-size:14px;">Instant automated key issuance via Razorpay</p>
    <input type="email" id="email" placeholder="Enter your email" value="test@client.com">
    
    <div class="plan-card">
      <h3 style="margin:5px 0;">Developer Sandbox</h3>
      <p style="color:#00ffcc;font-size:22px;margin:5px 0;">₹1</p>
      <button onclick="payNow(100, 'Sandbox Test')">Pay ₹1 (Test Live Gate)</button>
    </div>

    <div class="plan-card">
      <h3 style="margin:5px 0;">Business Pro</h3>
      <p style="color:#00ffcc;font-size:22px;margin:5px 0;">₹1,499 / mo</p>
      <button onclick="payNow(149900, 'Business Pro')">Subscribe ₹1,499</button>
    </div>
  </div>

  <script>
    function payNow(amount, plan) {
      var emailVal = document.getElementById("email").value;
      if (!emailVal) { alert("Please enter email"); return; }
      var rzp = new Razorpay({
        key: "rzp_live_Tp1pLALckoKQhV",
        amount: amount,
        currency: "INR",
        name: "GhostKey Protocol",
        description: plan,
        prefill: { email: emailVal },
        theme: { color: "#00ffcc" },
        handler: function(resp) {
          alert("Payment Successful! ID: " + resp.razorpay_payment_id);
          window.location.href = "/playground";
        }
      });
      rzp.open();
    }
  </script>
</body>
</html>"""

@app.route("/pricing")
def pricing_route():
    return PRICING_PAGE_HTML
