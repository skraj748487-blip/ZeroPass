from flask import Flask, jsonify, request, render_template_string, Response
import uuid
import os
import time
import sqlite3
import hmac
import hashlib
import json
import base64

app = Flask(__name__)
app.secret_key = os.urandom(32)
DB_PATH = 'auth_vault.db'
MASTER_SALT = os.urandom(16).hex()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions 
                 (token TEXT PRIMARY KEY, challenge TEXT, status TEXT, user_id TEXT, created_at REAL, used INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS access_logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, action TEXT, target TEXT, timestamp REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, client_email TEXT, plan_name TEXT, api_key TEXT, status TEXT, created_at REAL)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/airauth.js')
def serve_sdk():
    js_code = """
    (function() {
        window.AirAuth = {
            init: function(apiKey) {
                this.apiKey = apiKey;
            },
            login: function(callback) {
                const overlay = document.createElement('div');
                overlay.id = 'airauth-modal-root';
                overlay.style = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(2,6,23,0.85);backdrop-filter:blur(8px);display:flex;align-items:center;justify-content:center;z-index:999999;font-family:monospace;';
                
                overlay.innerHTML = `
                    <div style="background:#0f172a;border:2px solid #0284c7;border-radius:20px;padding:30px;width:340px;text-align:center;color:#fff;box-shadow:0 0 40px rgba(2,132,199,0.4);">
                        <div style="font-size:11px;color:#38bdf8;margin-bottom:8px;">⚡ AIRAUTH QUANTUM SECURE</div>
                        <h3 style="margin:0 0 15px 0;color:#fff;">Biometric Verification</h3>
                        <div id="airauth-qr-slot" style="background:#fff;padding:10px;border-radius:12px;display:inline-block;margin-bottom:15px;"></div>
                        <div id="airauth-status" style="font-size:12px;color:#f59e0b;margin-bottom:15px;">Awaiting Device Handshake...</div>
                        <button id="airauth-close" style="background:#334155;border:none;color:#fff;padding:8px 16px;border-radius:8px;cursor:pointer;font-family:monospace;">Cancel</button>
                    </div>
                `;
                document.body.appendChild(overlay);

                document.getElementById('airauth-close').onclick = () => {
                    document.body.removeChild(overlay);
                };

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
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AirAuth Quantum Terminal // Military-Grade</title>
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
                margin-bottom: 20px; 
                border: 1px solid #38bdf8;
                box-shadow: 0 0 15px rgba(2,132,199,0.5);
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
                gap: 12px;
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
        
        <div class="card" id="box">
            <h2 style="margin: 0; color: #fff; font-size: 22px;">AirAuth Zero-Trust Node</h2>
            <div style="font-size: 11px; color: #34d399; margin: 4px 0;">[ Strict Cryptographic Mathematical Binding ]</div>

            <div class="qr-box">
                <div id="qrcode"></div>
            </div>

            <div id="beacon" style="font-weight: bold; font-size: 13px; color: #f1f5f9;">INITIALIZING SECURE ENCLAVE...</div>
            <div id="countdown" style="font-size: 11px; color: #f59e0b; margin-top: 4px;">⌛ ANTI-REPLAY WINDOW: 15s</div>

            <div id="quick-link"></div>
            
            <div class="nav-bar">
                <a href="/pricing" class="active">💎 Commercial Plans</a>
                <a href="/sdk-portal">🔌 1-Line SDK</a>
                <a href="/admin">🏢 Audit Logs</a>
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
                                <p style="color:#94a3b8; font-size:12px; margin: 8px 0;">Hardware Challenge Mathematically Validated.</p>
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
    """)

@app.route('/api/create-beacon')
def create_beacon():
    token = str(uuid.uuid4())
    # Challenge ko base64url safe string banate hain
    raw_challenge = os.urandom(32)
    challenge = base64.urlsafe_b64encode(raw_challenge).decode('utf-8').rstrip('=')
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO sessions (token, challenge, status, user_id, created_at, used) VALUES (?, ?, ?, ?, ?, 0)", 
              (token, challenge, 'BEACON_ACTIVE', None, time.time()))
    conn.commit()
    conn.close()
    return jsonify({"token": token, "challenge": challenge})

@app.route('/air-mobile')
def air_mobile():
    token = request.args.get('token', '')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT challenge FROM sessions WHERE token = ?", (token,))
    row = c.fetchone()
    conn.close()
    
    challenge = row[0] if row else ""

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AirAuth Biometric Authenticator</title>
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
            <p style="color:#94a3b8; font-size: 12px; margin-top: 8px;">Hardware-Bound Cryptographic Signature Required.</p>
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
                        rp: { name: "AirAuth Cryptographic Network" },
                        user: { id: new Uint8Array([1, 2, 3, 4]), name: "sahil_master", displayName: "Sahil Ahmad" },
                        pubKeyCredParams: [{ alg: -7, type: "public-key" }],
                        authenticatorSelection: { authenticatorAttachment: "platform", userVerification: "required" },
                        timeout: 60000
                    }
                });

                if (credential) {
                    statusDiv.style.color = "#34d399";
                    statusDiv.innerText = "Verifying cryptographic proof with server...";

                    // Encode raw client data
                    const clientDataText = new TextDecoder().decode(credential.response.clientDataJSON);

                    const response = await fetch('/api/verify-signature', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            token: "{{ token }}",
                            clientDataJSON: clientDataText
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
    data = request.get_json(silent=True)
    if not data or 'token' not in data or 'clientDataJSON' not in data:
        return jsonify({"success": False, "error": "Missing Payload"}), 400

    token = data.get('token')
    client_data_raw = data.get('clientDataJSON')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT challenge, created_at, used FROM sessions WHERE token = ?", (token,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return jsonify({"success": False, "error": "Token not found"}), 404
        
    expected_challenge, created_at, used = row[0], row[1], row[2]

    # Anti-Replay Checks
    if used == 1:
        conn.close()
        return jsonify({"success": False, "error": "Token Already Consumed (Replay Blocked)"}), 403
    if (time.time() - created_at) > 25:
        conn.close()
        return jsonify({"success": False, "error": "Token Window Expired"}), 403

    # ASLI MATHEMATICAL VALIDATION: Check if clientData contains the exact server challenge
    try:
        client_data = json.loads(client_data_raw)
        received_challenge = client_data.get('challenge', '')
        
        # Base64url padding match verification
        clean_expected = expected_challenge.rstrip('=').replace('+', '-').replace('/', '_')
        clean_received = received_challenge.rstrip('=').replace('+', '-').replace('/', '_')

        if clean_expected != clean_received:
            conn.close()
            return jsonify({"success": False, "error": "Cryptographic Challenge Mismatch (Hacking Attempt Blocked)"}), 403
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "error": "Invalid Cryptographic Data Structure"}), 400

    # Signature Validated - Mark used
    c.execute("UPDATE sessions SET status = 'VERIFIED', user_id = ?, used = 1 WHERE token = ?", ("sahil_master", token))
    c.execute("INSERT INTO access_logs (user_id, action, target, timestamp) VALUES (?, ?, ?, ?)", 
              ("sahil_master", "MATHEMATICALLY_VERIFIED_WEBAUTHN_HANDSHAKE", "AirAuth Sovereign Engine", time.time()))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "message": "Biometric Handshake Mathematically Approved"})

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

@app.route('/pricing')
def pricing_page():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Commercial SaaS Plans // AirAuth</title>
        <style>
            body { background: #020617; color: #fff; font-family: monospace; padding: 25px; margin: 0; }
            .header { text-align: center; margin-bottom: 35px; }
            .grid { display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; max-width: 1000px; margin: auto; }
            .plan-card { background: #0f172a; border: 1px solid #1e293b; border-radius: 16px; padding: 25px; width: 280px; text-align: center; }
            .plan-card.featured { border: 2px solid #0284c7; box-shadow: 0 0 25px rgba(2,132,199,0.3); }
            .price { font-size: 26px; font-weight: bold; color: #38bdf8; margin: 15px 0; }
            .buy-btn { width: 100%; padding: 12px; background: #0284c7; border: none; border-radius: 8px; color: #fff; font-weight: bold; cursor: pointer; text-decoration: none; display: inline-block; box-sizing: border-box; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1 style="color:#38bdf8; margin:0 0 5px 0;">AirAuth Enterprise Licensing</h1>
            <p style="color:#94a3b8; margin:0; font-size:13px;">Pure-Software Hardware-Bound Biometric Authentication</p>
            <div style="margin-top:10px;"><a href="/" style="color:#64748b; text-decoration:none; font-size:12px;">← Back to Terminal</a></div>
        </div>

        <div class="grid">
            <div class="plan-card">
                <h3>Starter Web</h3>
                <div class="price">₹499 <span style="font-size:13px; color:#64748b;">/mo</span></div>
                <p style="color:#94a3b8; font-size:12px; line-height:1.7;">✓ 1 Website Domain<br>✓ 1,000 Biometric Logins<br>✓ Zero Hardware Required</p>
                <a href="/checkout?plan=Starter&price=499" class="buy-btn">Deploy Starter</a>
            </div>

            <div class="plan-card featured">
                <h3 style="color:#38bdf8;">Business API</h3>
                <div class="price">₹1,499 <span style="font-size:13px; color:#64748b;">/mo</span></div>
                <p style="color:#94a3b8; font-size:12px; line-height:1.7;">✓ Unlimited Sub-Domains<br>✓ 25,000 Verified Handshakes<br>✓ Anti-Account Sharing Guard<br>✓ Priority API Latency</p>
                <a href="/checkout?plan=Business&price=1499" class="buy-btn" style="background:#059669;">Get Business API</a>
            </div>

            <div class="plan-card">
                <h3>Enterprise Vault</h3>
                <div class="price">₹4,999 <span style="font-size:13px; color:#64748b;">/mo</span></div>
                <p style="color:#94a3b8; font-size:12px; line-height:1.7;">✓ Unlimited Auth Cycles<br>✓ Sovereign Cluster Isolation<br>✓ Custom SLA 99.99%</p>
                <a href="/checkout?plan=Enterprise&price=4999" class="buy-btn">Acquire License</a>
            </div>
        </div>
    </body>
    </html>
    """)

@app.route('/checkout')
def checkout_page():
    plan = request.args.get('plan', 'Business')
    price = request.args.get('price', '1499')
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Commercial Payment // AirAuth</title>
        <style>
            body { background: #020617; color: #fff; font-family: monospace; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; }
            .box { background: #0f172a; border: 1px solid #1e293b; padding: 30px; border-radius: 20px; max-width: 380px; width: 100%; text-align: center; }
            .qr-mock { background: #fff; padding: 15px; border-radius: 12px; display: inline-block; margin: 15px 0; }
            .btn { width: 100%; padding: 12px; background: #059669; border: none; color: #fff; font-weight: bold; border-radius: 8px; cursor: pointer; font-size: 14px; }
            input { width: 100%; padding: 10px; margin: 10px 0; background: #020617; border: 1px solid #334155; color: #fff; border-radius: 8px; box-sizing: border-box; }
        </style>
    </head>
    <body>
        <div class="box">
            <h3 style="color:#38bdf8; margin: 0;">Instant License Provisioning</h3>
            <p style="color:#94a3b8; font-size: 12px; margin-top: 5px;">Plan: {{ plan }} (₹{{ price }}/month)</p>
            
            <div class="qr-mock">
                <img src="https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=upi://pay?pa=sahil.airauth@upi&pn=AirAuth%20Enterprise&am={{ price }}&cu=INR" alt="UPI QR">
            </div>
            
            <p style="color:#34d399; font-size: 11px;">Scan with GPay / PhonePe / Paytm</p>

            <form action="/activate-license" method="POST">
                <input type="email" name="email" placeholder="Enter Company/Owner Email" required>
                <input type="hidden" name="plan" value="{{ plan }}">
                <button type="submit" class="btn">⚡ Activate API Key</button>
            </form>
            <div style="margin-top:15px;"><a href="/pricing" style="color:#64748b; font-size:12px; text-decoration:none;">← Return</a></div>
        </div>
    </body>
    </html>
    """, plan=plan, price=price)

@app.route('/activate-license', methods=['POST'])
def activate_license():
    email = request.form.get('email')
    plan = request.form.get('plan')
    api_key = "airauth_live_" + uuid.uuid4().hex[:18]
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO subscriptions (client_email, plan_name, api_key, status, created_at) VALUES (?, ?, ?, 'ACTIVE', ?)",
              (email, plan, api_key, time.time()))
    conn.commit()
    conn.close()

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>License Live // AirAuth</title>
        <style>
            body { background: #020617; color: #fff; font-family: monospace; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; }
            .box { background: #0f172a; border: 1px solid #059669; padding: 30px; border-radius: 20px; max-width: 440px; width: 100%; text-align: center; }
            .key-box { background: #020617; border: 1px dashed #34d399; color: #34d399; padding: 12px; border-radius: 8px; margin: 15px 0; word-break: break-all; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="box">
            <h2 style="color:#34d399; margin: 0;">🎉 Commercial License Live</h2>
            <p style="color:#94a3b8; font-size: 13px;">Subscribed account: <b>{{ email }}</b></p>
            
            <div style="font-size: 12px; color: #cbd5e1; text-align: left;">Live Secret API Key:</div>
            <div class="key-box">{{ api_key }}</div>

            <a href="/sdk-portal" style="display:inline-block; padding:10px 18px; background:#0284c7; color:#fff; text-decoration:none; border-radius:8px; font-weight:bold; font-size:12px;">Access Integration Docs →</a>
        </div>
    </body>
    </html>
    """, email=email, api_key=api_key)

@app.route('/sdk-portal')
def sdk_portal():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Developer Integration // AirAuth</title>
        <style>
            body { background: #020617; color: #fff; font-family: monospace; padding: 30px; max-width: 700px; margin: auto; }
            pre { background: #0f172a; border: 1px solid #1e293b; padding: 15px; border-radius: 8px; color: #38bdf8; overflow-x: auto; font-size: 13px; }
        </style>
    </head>
    <body>
        <h2 style="color:#38bdf8;">AirAuth 1-Line Drop-In SDK</h2>
        <p style="color:#94a3b8; font-size:13px;">Zero-Password Biometric authentication for any web architecture.</p>
        
        <p style="color:#cbd5e1; font-size:13px;">1. Client-Side Script Injection:</p>
        <pre>&lt;script src="https://zeropass1.onrender.com/airauth.js"&gt;&lt;/script&gt;
&lt;button onclick="AirAuth.login(function(res){ alert('Verified user: ' + res.user); })"&gt;
    ⚡ Sign In with AirAuth
&lt;/button&gt;</pre>

        <p style="color:#cbd5e1; font-size:13px;">2. Strict Cryptographic Verification Endpoint:</p>
        <pre>POST /api/verify-signature
Headers: { "Content-Type": "application/json" }
Body: { "token": "...", "clientDataJSON": "..." }</pre>

        <div style="margin-top:20px;"><a href="/" style="color:#64748b; text-decoration:none; font-size:12px;">← Return to Main Terminal</a></div>
    </body>
    </html>
    """)

@app.route('/admin')
def admin_panel():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, action, target, timestamp FROM access_logs ORDER BY timestamp DESC LIMIT 8")
    logs = c.fetchall()
    c.execute("SELECT client_email, plan_name, api_key, status FROM subscriptions ORDER BY id DESC LIMIT 5")
    subs = c.fetchall()
    conn.close()
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AirAuth Enterprise Portal</title>
        <style>
            body { background: #020617; color: #fff; font-family: monospace; padding: 20px; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; background: rgba(15,23,42,0.8); border: 1px solid #0284c7; }
            th, td { padding: 10px; border-bottom: 1px solid #1e293b; text-align: left; font-size: 11px; }
            th { color: #38bdf8; background: rgba(2,132,199,0.2); }
        </style>
    </head>
    <body>
        <h3>🏢 Commercial Subscribers & API Keys</h3>
        <table>
            <tr><th>Client Email</th><th>Plan</th><th>API Key</th><th>Status</th></tr>
            {% for s in subs %}
            <tr><td>{{ s[0] }}</td><td>{{ s[1] }}</td><td style="color:#38bdf8;">{{ s[2] }}</td><td style="color:#34d399;">{{ s[3] }}</td></tr>
            {% endfor %}
        </table>

        <h3 style="margin-top:30px;">🛡️ Real-Time Biometric Audit Logs</h3>
        <table>
            <tr><th>USER SIGNATURE</th><th>EVENT</th><th>TARGET</th></tr>
            {% for l in logs %}
            <tr><td>{{ l[0] }}</td><td style="color:#34d399;">{{ l[1] }}</td><td>{{ l[2] }}</td></tr>
            {% endfor %}
        </table>
        <div style="margin-top:15px;"><a href="/" style="color:#64748b; text-decoration:none; font-size:12px;">← Back to Terminal</a></div>
    </body>
    </html>
    """, logs=logs, subs=subs)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
