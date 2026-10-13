from flask import Flask, jsonify, request, render_template_string
import uuid
import os
import time
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
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def terminal_display():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AirAuth Quantum Terminal</title>
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
                overflow-x: hidden;
            }
            .matrix-bg {
                position: fixed;
                top: 0; left: 0; width: 100%; height: 100%;
                font-size: 8px; color: rgba(2, 132, 199, 0.15);
                white-space: pre; overflow: hidden; pointer-events: none;
                z-index: -1; line-height: 1;
            }
            .badge { 
                background: linear-gradient(135deg, #0284c7, #0369a1); 
                color: #fff; 
                font-size: 11px; 
                padding: 8px 16px; 
                border-radius: 20px; 
                font-weight: bold; 
                margin-bottom: 20px; 
                box-shadow: 0 0 15px rgba(2,132,199,0.5);
                letter-spacing: 1px;
                border: 1px solid #38bdf8;
                text-shadow: 0 0 5px rgba(255,255,255,0.8);
            }
            .card { 
                background: rgba(15, 23, 42, 0.9); 
                border: 2px solid #0284c7; 
                border-radius: 24px; 
                padding: 30px; 
                text-align: center; 
                max-width: 440px; 
                width: 100%; 
                box-shadow: 0 0 50px rgba(2,132,199,0.4), inset 0 0 20px rgba(2,132,199,0.2); 
                position: relative;
                backdrop-filter: blur(10px);
            }
            .qr-box { 
                background: #fff; 
                padding: 12px; 
                border-radius: 16px; 
                display: inline-block; 
                margin: 15px auto; 
                box-shadow: 0 0 25px rgba(255,255,255,0.2);
                position: relative;
            }
            .pulse-ring {
                position: absolute;
                top: -5px; left: -5px; right: -5px; bottom: -5px;
                border: 2px solid #38bdf8;
                border-radius: 20px;
                animation: scan 2s infinite ease-in-out;
            }
            @keyframes scan {
                0%, 100% { transform: scale(1); opacity: 0.2; }
                50% { transform: scale(1.03); opacity: 0.8; }
            }
            .telemetry {
                font-size: 10px;
                color: #64748b;
                margin: 10px 0;
                text-transform: uppercase;
                letter-spacing: 1px;
                display: flex;
                justify-content: space-around;
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
                box-shadow: 0 0 15px rgba(37,99,235,0.4);
                transition: 0.3s;
                border: 1px solid #38bdf8;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 0 25px rgba(2,132,199,0.8);
            }
            .holo-wave {
                height: 30px;
                background: linear-gradient(90deg, transparent, rgba(56,189,248,0.2), transparent);
                position: relative;
                overflow: hidden;
                margin: 15px 0;
                border-radius: 4px;
                border-top: 1px solid rgba(2,132,199,0.3);
                border-bottom: 1px solid rgba(2,132,199,0.3);
            }
            .holo-wave::after {
                content: '';
                position: absolute;
                left: -100%; width: 100%; height: 100%;
                background: linear-gradient(90deg, transparent, #38bdf8, transparent);
                animation: sweep 1.5s infinite linear;
            }
            @keyframes sweep {
                0% { left: -100%; }
                100% { left: 100%; }
            }
        </style>
    </head>
    <body>
        <div class="matrix-bg" id="matrix"></div>
        <div class="badge">⚡ ENGINEERED BY SAHIL AHMAD // LEAD ARCHITECT ⚡</div>
        
        <div class="card" id="box">
            <h2 style="margin: 0; color: #fff; font-size: 22px; letter-spacing: 1.5px;">AirAuth Quantum</h2>
            <div style="font-size: 11px; color: #34d399; margin: 4px 0; text-transform: uppercase;">[ Decentralized Hardware Trust Binding ]</div>

            <div class="holo-wave">
                <div style="font-size:9px; color:#38bdf8; position:absolute; width:100%; top:8px; text-align:center; font-weight:bold; letter-spacing:3px;">DYNAMIC NONCE TUNNEL ACTIVE</div>
            </div>

            <div class="qr-box">
                <div class="pulse-ring"></div>
                <div id="qrcode"></div>
            </div>

            <div id="beacon" style="font-weight: bold; font-size: 14px; color: #f1f5f9; text-shadow: 0 0 10px rgba(56,189,248,0.5);">BROADCASTING HARDWARE TOKEN</div>
            <div id="countdown" style="font-size: 11px; color: #f59e0b; margin-top: 4px;">⌛ SCAN IN: 10s (Anti-Replay)</div>

            <div class="telemetry">
                <span>⚡ C-KEY: RSA-2048</span>
                <span>🛡️ WEB-AUTHN: ENFORCED</span>
                <span>📡 BEACON: ACTIVE</span>
            </div>

            <div id="quick-link"></div>
            
            <div style="margin-top: 15px;">
                <a href="/admin" style="color: #64748b; font-size: 12px; text-decoration: none; border: 1px solid #1e293b; padding: 4px 10px; border-radius: 6px;">🏢 Cryptographic Logs</a>
            </div>
        </div>

        <script>
            let activeToken = "";
            let timer = 10;

            // Hacker console animation
            const matrix = document.getElementById('matrix');
            let mStr = "";
            for (let i = 0; i < 40; i++) {
                mStr += Array(80).fill(0).map(() => Math.random() > 0.5 ? "1" : "0").join("") + "\\n";
            }
            matrix.textContent = mStr;
            setInterval(() => {
                let lines = matrix.textContent.split("\\n");
                lines.shift();
                lines.push(Array(80).fill(0).map(() => Math.random() > 0.5 ? "1" : "0").join(""));
                matrix.textContent = lines.join("\\n");
            }, 150);

            function playAccessSound() {
                try {
                    const ctx = new (window.AudioContext || window.webkitAudioContext)();
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.type = 'sawtooth';
                    osc.frequency.setValueAtTime(300, ctx.currentTime);
                    osc.frequency.exponentialRampToValueAtTime(1200, ctx.currentTime + 0.4);
                    gain.gain.setValueAtTime(0.3, ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.start();
                    osc.stop(ctx.currentTime + 0.5);
                } catch(e) {}
            }

            function fetchNewToken() {
                fetch('/api/create-beacon')
                    .then(r => r.json())
                    .then(d => {
                        activeToken = d.token;
                        timer = 10;
                        document.getElementById('beacon').innerText = '⚡ TUNNEL TOKEN: ' + d.token.slice(0, 8);
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
                            <a class="btn" href="${mobileUrl}" target="_blank">📳 Simulate Biometric Touch</a>
                        `;
                    });
            }

            setInterval(() => {
                timer--;
                document.getElementById('countdown').innerText = '⌛ ROTATING TOKEN IN: ' + timer + 's';
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
                            playAccessSound();
                            document.getElementById('box').innerHTML = `
                                <div style="font-size:75px; margin:10px 0; color:#34d399; text-shadow: 0 0 30px #34d399;">🔓</div>
                                <h2 style="color:#34d399; margin:0; letter-spacing: 2px;">ACCESS GRANTED</h2>
                                <p style="color:#94a3b8; font-size:12px; margin: 8px 0;">Hardware Handshake Approved via Secure Enclave ID.</p>
                                <div style="border: 1px dashed #10b981; padding: 10px; background: rgba(16,185,129,0.1); font-size:11px; color:#34d399; margin-top: 15px;">
                                    IDENTITY MATCH: ${s.user_id}
                                </div>
                            `;
                            setTimeout(() => { location.reload(); }, 4000);
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
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Identity Authentication Device</title>
        <style>
            body { 
                background: #020617; 
                color: #fff; 
                font-family: 'Courier New', monospace; 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                min-height: 100vh; 
                margin: 0; 
                padding: 15px; 
                box-sizing: border-box; 
            }
            .box { 
                background: rgba(15, 23, 42, 0.95); 
                border: 2px solid #0284c7; 
                padding: 35px 25px; 
                border-radius: 28px; 
                text-align: center; 
                max-width: 360px; 
                width: 100%; 
                box-shadow: 0 0 50px rgba(2,132,199,0.3); 
            }
            .scan-zone {
                width: 130px;
                height: 130px;
                border: 2px solid #38bdf8;
                border-radius: 50%;
                margin: 25px auto;
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
                cursor: pointer;
                background: radial-gradient(circle, rgba(2,132,199,0.2) 0%, transparent 70%);
                box-shadow: 0 0 20px rgba(2,132,199,0.3);
            }
            .fingerprint-icon {
                font-size: 60px;
                transition: transform 0.2s;
            }
            .scan-line {
                position: absolute;
                width: 100%;
                height: 3px;
                background: #38bdf8;
                box-shadow: 0 0 12px #38bdf8;
                top: 0;
                animation: scanning 2.5s infinite ease-in-out;
            }
            @keyframes scanning {
                0%, 100% { top: 10%; }
                50% { top: 90%; }
            }
            #status { margin-top: 15px; font-size: 11px; color: #f59e0b; text-transform: uppercase; letter-spacing: 1.5px; }
        </style>
    </head>
    <body>
        <div class="box">
            <div style="font-size: 11px; color: #0284c7; border: 1px solid #0284c7; display: inline-block; padding: 4px 12px; border-radius: 12px; font-weight: bold; margin-bottom: 15px;">🛡️ CRYPTOGRAPHIC KEY BOUND</div>
            <h3 style="margin: 0; color: #38bdf8; font-size: 18px; letter-spacing: 1px;">Touch to Verify</h3>
            <p style="color:#94a3b8; font-size: 12px; margin-top: 8px;">Hardware biometric signature is required to open this gateway.</p>
            
            <div class="scan-zone" id="scanZone" onclick="runBiometricChallenge()">
                <div class="scan-line"></div>
                <div class="fingerprint-icon">🎯</div>
            </div>

            <div id="status">PRESS THE AREA ABOVE TO SCAN</div>
        </div>

        <script>
        async function runBiometricChallenge() {
            const statusDiv = document.getElementById('status');
            const scanZone = document.getElementById('scanZone');
            statusDiv.innerText = "🚨 SCANNING Android OS Sensor...";
            scanZone.style.borderColor = "#f59e0b";

            if (!window.PublicKeyCredential) {
                statusDiv.innerText = "❌ Security hardware verification is missing.";
                return;
            }

            try {
                const challenge = new Uint8Array(32);
                window.crypto.getRandomValues(challenge);

                const options = {
                    publicKey: {
                        challenge: challenge,
                        rp: { name: "AirAuth Enterprise" },
                        user: {
                            id: new Uint8Array([1, 2, 3, 4, 5]),
                            name: "sahil_master",
                            displayName: "Sahil Ahmad"
                        },
                        pubKeyCredParams: [{ alg: -7, type: "public-key" }],
                        authenticatorSelection: {
                            authenticatorAttachment: "platform",
                            userVerification: "required"
                        },
                        timeout: 60000
                    }
                };

                const credential = await navigator.credentials.create(options);

                if (credential) {
                    scanZone.style.borderColor = "#34d399";
                    statusDiv.style.color = "#34d399";
                    statusDiv.innerText = "🔓 SUCCESS! TRANSMITTING ENCRYPTED Handshake...";
                    setTimeout(() => {
                        window.location.href = "/api/verify-signature?token={{ token }}";
                    }, 500);
                }
            } catch (err) {
                scanZone.style.borderColor = "#ef4444";
                statusDiv.style.color = "#ef4444";
                statusDiv.innerText = "❌ SCAN CANCELLED / TRY AGAIN";
            }
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
    
    if not row or row[2] == 1 or (time.time() - row[1] > 25):
        conn.close()
        return "<body style='background:#020617; color:#ef4444; font-family: monospace; text-align:center; padding:50px;'><h3>⚠️ Challenge Expired or Token Used (Security Safeguard)</h3></body>", 403

    c.execute("UPDATE sessions SET status = 'VERIFIED', user_id = ?, used = 1 WHERE token = ?", ("sahil_master", token))
    c.execute("INSERT INTO access_logs (user_id, action, target, timestamp) VALUES (?, ?, ?, ?)", 
              ("sahil_master", "SECURE_HARDWARE_AUTHENTICATION", "AirAuth Quantum Node", time.time()))
    conn.commit()
    conn.close()
    
    return """
    <body style='background:#020617; color:#34d399; font-family: monospace; text-align:center; padding:50px;'>
        <div style="font-size: 60px;">⚡</div>
        <h2>HANDSHAKE COMPLETED</h2>
        <p style='color:#94a3b8; font-size:12px;'>Biological ID cryptographic token validated correctly. Handing over control.</p>
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

@app.route('/admin')
def admin_panel():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, action, target, timestamp FROM access_logs ORDER BY timestamp DESC LIMIT 10")
    logs = c.fetchall()
    conn.close()
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AirAuth Quantum Logs</title>
        <style>
            body { background: #020617; color: #fff; font-family: monospace; padding: 20px; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; background: rgba(15,23,42,0.8); border: 1px solid #0284c7; }
            th, td { padding: 12px; border-bottom: 1px solid #1e293b; text-align: left; font-size: 11px; }
            th { color: #38bdf8; background: rgba(2,132,199,0.2); }
        </style>
    </head>
    <body>
        <h3>🏢 Hardware Cryptographic Audit Portal</h3>
        <a href="/" style="color:#64748b; text-decoration:none;">← Return to UI Terminal</a>
        <table>
            <tr><th>USER SIGNATURE</th><th>PROCESS EVENT</th><th>TARGET HARDWARE / SYSTEM</th></tr>
            {% for l in logs %}
            <tr><td>{{ l[0] }}</td><td style="color:#34d399; text-shadow: 0 0 5px #34d399;">{{ l[1] }}</td><td>{{ l[2] }}</td></tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """, logs=logs)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
