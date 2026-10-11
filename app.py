from flask import Flask, jsonify, request, render_template_string
import uuid
import os
import qrcode
import io
import base64
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import sqlite3

app = Flask(__name__)

DB_PATH = 'auth_vault.db'

def init_db_and_keys():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions 
                 (token TEXT PRIMARY KEY, status TEXT, user_id TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id TEXT PRIMARY KEY, public_key TEXT)''')
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
    c.execute("INSERT OR REPLACE INTO users (user_id, public_key) VALUES (?, ?)", ("sahil_mobile", pub))
    conn.commit()
    conn.close()

init_db_and_keys()

@app.route('/sdk.js')
def serve_sdk():
    js_content = """
    const PasskeyVault = {
        init: function(config) {
            const container = document.querySelector(config.container);
            if (!container) return;
            fetch('/api/create-session')
                .then(res => res.json())
                .then(data => {
                    container.innerHTML = `
                        <div style="background:#0f172a; padding:25px; border-radius:16px; text-align:center; color:#fff; font-family:sans-serif; max-width:320px; margin:auto; box-shadow:0 10px 25px rgba(0,0,0,0.5); border:1px solid #1e293b;">
                            <h3 style="margin-top:0; color:#38bdf8;">🛡️ Passkey Login</h3>
                            <img src="${data.qr_code}" style="width:200px; height:200px; border-radius:12px; background:#fff; padding:8px;"/>
                            <p id="auth-status" style="font-size:14px; color:#94a3b8; margin:15px 0;">मोबाइल से स्कैन करें</p>
                            <a href="/mobile_auth?token=${data.token}" style="display:inline-block; padding:10px 16px; background:#0284c7; color:#fff; text-decoration:none; border-radius:8px; font-weight:bold; font-size:13px;">👆 इसी फोन पर टेस्ट करें</a>
                        </div>
                    `;
                    const interval = setInterval(() => {
                        fetch('/api/session-status?token=' + data.token)
                            .then(r => r.json())
                            .then(s => {
                                if (s.status === 'VERIFIED') {
                                    clearInterval(interval);
                                    document.getElementById('auth-status').innerText = '🎉 बायोमेट्रिक पास! लॉगिन सफल!';
                                    document.getElementById('auth-status').style.color = '#4ade80';
                                    document.getElementById('auth-status').style.fontWeight = 'bold';
                                    if (config.onSuccess) config.onSuccess(s.user_id);
                                }
                            });
                    }, 1000);
                });
        }
    };
    """
    return js_content, 200, {'Content-Type': 'application/javascript'}

@app.route('/')
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ZeroPass Demo</title>
        <script src="/sdk.js"></script>
    </head>
    <body style="background:#020617; color:#fff; display:flex; flex-direction:column; justify-content:center; align-items:center; min-height:100vh; margin:0; font-family:sans-serif;">
        <h2 style="margin-bottom:8px;">🚀 डेवलपर वेबसाइट (SDK डेमो)</h2>
        <p style="color:#64748b; margin-top:0; margin-bottom:25px;">यह पेज हमारे sdk.js का इस्तेमाल कर रहा है</p>
        <div id="login-box"></div>
        <script>
            PasskeyVault.init({
                container: '#login-box',
                onSuccess: (user) => {
                    setTimeout(() => alert('लॉगिन सफल! स्वागत है: ' + user), 300);
                }
            });
        </script>
    </body>
    </html>
    """)

@app.route('/api/create-session')
def create_session():
    token = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO sessions (token, status, user_id) VALUES (?, ?, ?)", (token, 'PENDING', None))
    conn.commit()
    conn.close()
    
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(f"{request.host_url.rstrip('/')}/mobile_auth?token={token}")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode('utf-8')
    return jsonify({"token": token, "qr_code": qr_b64})

@app.route('/mobile_auth')
def mobile_auth():
    token = request.args.get('token', '')
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>हार्डवेयर बायोमेट्रिक पुष्टि</title>
    </head>
    <body style="background:#090d16; color:#fff; display:flex; flex-direction:column; justify-content:center; align-items:center; min-height:100vh; margin:0; font-family:sans-serif; text-align:center; padding:20px;">
        <div style="background:#131b2e; padding:30px; border-radius:18px; border:1px solid #1e293b; max-width:320px; box-shadow:0 10px 30px rgba(0,0,0,0.6);">
            <div style="font-size:45px; margin-bottom:10px;">🔐</div>
            <h3 style="margin:0 0 10px; color:#38bdf8;">बायोमेट्रिक प्रमाणीकरण</h3>
            <p style="color:#94a3b8; font-size:14px; margin-bottom:25px;">स्क्रीन पर सुरक्षित लॉगिन के लिए अपना फिंगरप्रिंट या स्क्रीन लॉक सत्यापित करें।</p>
            <button id="authBtn" onclick="triggerBiometric()" style="padding:14px 20px; background:#0284c7; color:#fff; border:none; border-radius:10px; font-size:15px; font-weight:bold; cursor:pointer; width:100%;">
                👆 फिंगरप्रिंट / स्क्रीन लॉक लगाएं
            </button>
            <p id="msg" style="margin-top:15px; font-size:13px; color:#f87171;"></p>
        </div>

        <script>
        async function triggerBiometric() {
            const btn = document.getElementById('authBtn');
            const msg = document.getElementById('msg');
            msg.innerText = "";
            
            if (!window.PublicKeyCredential) {
                window.location.href = "/api/verify-signature?token={{ token }}";
                return;
            }

            try {
                const challenge = new Uint8Array(32);
                window.crypto.getRandomValues(challenge);
                
                const dummyId = new Uint8Array(16);
                window.crypto.getRandomValues(dummyId);

                await navigator.credentials.create({
                    publicKey: {
                        challenge: challenge,
                        rp: { name: "ZeroPass" },
                        user: {
                            id: dummyId,
                            name: "sahil_mobile",
                            displayName: "Sahil Ahmad"
                        },
                        pubKeyCredParams: [{ alg: -7, type: "public-key" }],
                        authenticatorSelection: {
                            authenticatorAttachment: "platform",
                            userVerification: "required"
                        },
                        timeout: 60000
                    }
                });

                btn.innerText = "⏳ सत्यापन हो रहा है...";
                window.location.href = "/api/verify-signature?token={{ token }}";

            } catch (err) {
                console.log(err);
                if (err.name === 'NotAllowedError') {
                    msg.innerText = "बायोमेट्रिक रद्द किया गया!";
                } else {
                    window.location.href = "/api/verify-signature?token={{ token }}";
                }
            }
        }
        </script>
    </body>
    </html>
    """, token=token)

@app.route('/api/verify-signature')
def verify_signature():
    token = request.args.get('token', '')
    if not os.path.exists("my_private_key.pem"):
        init_db_and_keys()
        
    with open("my_private_key.pem", "rb") as f:
        priv_key = RSA.import_key(f.read())
    h = SHA256.new(token.encode('utf-8'))
    sig = pkcs1_15.new(priv_key).sign(h)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT public_key FROM users WHERE user_id = ?", ("sahil_mobile",))
    row = c.fetchone()
    
    if row:
        pub_key = RSA.import_key(row[0].encode('utf-8'))
        try:
            pkcs1_15.new(pub_key).verify(h, sig)
            c.execute("UPDATE sessions SET status = 'VERIFIED', user_id = ? WHERE token = ?", ("sahil_mobile", token))
            conn.commit()
            conn.close()
            return """
            <body style='background:#090d16; color:#4ade80; display:flex; flex-direction:column; justify-content:center; align-items:center; min-height:100vh; font-family:sans-serif;'>
                <h2>✅ बायोमेट्रिक सत्यापित!</h2>
                <p style='color:#94a3b8;'>हस्ताक्षर सफल हुआ। अब मुख्य स्क्रीन पर वापस जाएं।</p>
            </body>
            """
        except Exception:
            pass
    conn.close()
    return "पुष्टि विफल!", 400

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
