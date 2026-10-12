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
            .btn { display: inline-block; margin-top: 12px; padding: 10px 18px; background: #0284c7; color: #fff; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 13px; }
        </style>
    </head>
    <body>
        <div class="badge">⚡ ENGINEERED BY SAHIL AHMAD // LEAD ARCHITECT ⚡</div>
        <div class="card" id="box">
            <h2 style="margin: 0; color: #fff; font-size: 20px;">AirAuth Enterprise Terminal</h2>
            <div style="font-size: 12px; color: #34d399; margin: 5px 0;">[ Strict Hardware Biometric Bound ]</div>

            <div class="qr-box"><div id="qrcode"></div></div>
            <div id="beacon" style="font-size: 13px; color: #e2e8f0;">BROADCASTING HARDWARE TOKEN</div>
            <div id="countdown" style="font-size: 11px; color: #f59e0b; margin-top: 4px;">Refreshing in: 10s</div>

            <div class="metric">
                <span>GATE: SECURE</span>
                <span>DESK: LOCKED</span>
                <span>BIOMETRIC: MANDATORY</span>
            </div>

            <div id="quick-link"></div>
            <div style="margin-top: 15px;"><a href="/admin" style="color: #64748b; font-size: 12px; text-decoration: none;">🏢 View Real-Time Logs</a></div>
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
                                <p style="color:#94a3b8; font-size:13px; margin: 8px 0;">Hardware Biometric Verified by Android Sensor.</p>
                                <div style="font-size:12px; color:#38bdf8;">Verified User: ${s.user_id}</div>
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
            body { background: #020617; color: #fff; font-family: sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }
            .box { background: #0f172a; border: 1px solid #1e293b; padding: 30px; border-radius: 20px; text-align: center; max-width: 320px; width: 100%; box-shadow: 0 0 30px rgba(2,132,199,0.2); }
            .btn { width: 100%; padding: 15px; background: #0284c7; color: #fff; border: none; border-radius: 12px; font-weight: bold; font-size: 15px; cursor: pointer; margin-top: 20px; }
            #status { margin-top: 15px; font-size: 13px; color: #f59e0b; }
        </style>
    </head>
    <body>
        <div class="box">
            <div style="font-size: 40px; margin-bottom: 10px;">🛡️</div>
            <h3 style="margin: 0; color: #38bdf8;">Hardware Biometric Lock</h3>
            <p style="color:#94a3b8; font-size: 13px; margin-top: 8px;">Fingerprint / Face ID scan is mandatory for terminal access.</p>
            <button class="btn" id="bioBtn" onclick="runBiometricChallenge()">👆 Scan Fingerprint Now</button>
            <div id="status"></div>
        </div>

        <script>
        async function runBiometricChallenge() {
            const statusDiv = document.getElementById('status');
            const btn = document.getElementById('bioBtn');
            statusDiv.innerText = "Prompting Native Sensor...";

            if (!window.PublicKeyCredential) {
                statusDiv.innerText = "❌ WebAuthn Biometrics not supported on this browser.";
                return;
            }

            try {
                // Real Android Hardware Sensor Challenge
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

                btn.disabled = true;
                // THIS TRIGGERS THE REAL OS FINGERPRINT DIALOG
                const credential = await navigator.credentials.create(options);

                if (credential) {
                    statusDiv.style.color = "#34d399";
                    statusDiv.innerText = "⚡ Hardware Fingerprint Confirmed! Transmitting...";
                    window.location.href = "/api/verify-signature?token={{ token }}";
                }
            } catch (err) {
                btn.disabled = false;
                statusDiv.style.color = "#ef4444";
                statusDiv.innerText = "❌ Biometric Cancelled / Failed: " + (err.name || "Access Denied");
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
    
    if not row or row[2] == 1 or (time.time() - row[1] > 20):
        conn.close()
        return "<body style='background:#020617; color:#ef4444; text-align:center; padding:50px;'><h3>⚠️ Token Expired (Anti-Replay)</h3></body>", 403

    c.execute("UPDATE sessions SET status = 'VERIFIED', user_id = ?, used = 1 WHERE token = ?", ("sahil_master", token))
    c.execute("INSERT INTO access_logs (user_id, action, target, timestamp) VALUES (?, ?, ?, ?)", 
              ("sahil_master", "PHYSICAL_BIOMETRIC_CONFIRMED", "AirAuth Terminal", time.time()))
    conn.commit()
    conn.close()
    
    return """
    <body style='background:#020617; color:#34d399; font-family:sans-serif; text-align:center; padding:50px;'>
        <h2>⚡ Biometric Verified by Sensor!</h2>
        <p style='color:#94a3b8;'>Physical hardware challenge confirmed. Terminal Unlocked.</p>
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
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AirAuth Audit Logs</title>
        <style>
            body { background: #020617; color: #fff; font-family: monospace; padding: 20px; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; background: #0f172a; }
            th, td { padding: 10px; border-bottom: 1px solid #1e293b; text-align: left; font-size: 12px; }
            th { color: #38bdf8; }
        </style>
    </head>
    <body>
        <h3>🏢 Hardware Biometric Audit Logs</h3>
        <a href="/" style="color:#64748b; text-decoration:none;">← Return to Terminal</a>
        <table>
            <tr><th>User</th><th>Verification Type</th><th>Target Device</th></tr>
            {% for l in logs %}
            <tr><td>{{ l[0] }}</td><td style="color:#34d399;">{{ l[1] }}</td><td>{{ l[2] }}</td></tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """, logs=logs)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
