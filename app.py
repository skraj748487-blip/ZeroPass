from flask import Flask, render_template_string, send_file, jsonify, request, Response
import qrcode
import io
import uuid
import sqlite3
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('auth_vault.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    device_name TEXT,
                    public_key_pem TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    status TEXT,
                    user_id TEXT
                )''')
    conn.commit()
    try:
        with open("my_public_key.pem", "r") as f:
            pub_pem = f.read()
        c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?)", 
                  ("user_primary", "Personal Mobile KeyStore", pub_pem))
        conn.commit()
    except:
        pass
    conn.close()

init_db()

SDK_JS = """
window.PasskeyVault = {
    init: function(config) {
        const container = document.querySelector(config.container);
        if (!container) return;

        fetch('/api/create-session')
            .then(res => res.json())
            .then(data => {
                const token = data.token;
                container.innerHTML = `
                    <div style="background:#1c2541; padding:20px; border-radius:12px; text-align:center; color:white; max-width:320px; font-family:sans-serif; margin:auto;">
                        <h3 style="margin:0 0 10px 0; color:#38bdf8;">🛡️ Passkey Login</h3>
                        <div style="background:white; padding:10px; border-radius:8px; display:inline-block;">
                            <img src="/api/qr?token=${token}" style="width:160px; height:160px; display:block;" />
                        </div>
                        <p id="vault-status" style="font-size:13px; color:#94a3b8; margin:12px 0;">मोबाइल से स्कैन करें</p>
                        <a href="/mobile_auth?token=${token}" target="_blank" style="display:inline-block; padding:8px 14px; background:#0284c7; color:white; text-decoration:none; border-radius:6px; font-size:12px; font-weight:bold;">
                            👆 इसी फोन पर टेस्ट करें
                        </a>
                    </div>
                `;

                const poll = setInterval(() => {
                    fetch(`/api/session-status?token=${token}`)
                        .then(r => r.json())
                        .then(statusData => {
                            if (statusData.status === 'VERIFIED') {
                                clearInterval(poll);
                                const st = document.getElementById('vault-status');
                                st.innerHTML = "🎉 बायोमेट्रिक पास! लॉगिन सफल!";
                                st.style.color = "#34d399";
                                st.style.fontWeight = "bold";
                                if (config.onSuccess) config.onSuccess(statusData.user_id);
                            }
                        });
                }, 1000);
            });
    }
};
"""

@app.route('/sdk.js')
def serve_sdk():
    return Response(SDK_JS, mimetype='application/javascript')

@app.route('/')
def developer_demo():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Enterprise SDK Demo</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="background:#0b1329; color:white; font-family:sans-serif; text-align:center; padding-top:30px;">
    <h2>🚀 डेवलपर वेबसाइट (SDK डेमो)</h2>
    <p style="color:#94a3b8; font-size:14px;">यह पेज हमारे <code>sdk.js</code> का इस्तेमाल कर रहा है</p>

    <div id="login-widget"></div>

    <script src="/sdk.js"></script>
    <script>
        PasskeyVault.init({
            container: '#login-widget',
            onSuccess: (userId) => {
                alert("🎉 बधाई हो! यूज़र ID: " + userId + " सफलता से लॉगिन हो गया!");
            }
        });
    </script>
</body>
</html>
    """)

@app.route('/api/create-session')
def create_session():
    token = str(uuid.uuid4())
    conn = sqlite3.connect('auth_vault.db')
    c = conn.cursor()
    c.execute("INSERT INTO sessions VALUES (?, 'WAITING', NULL)", (token,))
    conn.commit()
    conn.close()
    return jsonify({"token": token})

@app.route('/api/qr')
def generate_qr():
    token = request.args.get('token')
    host_url = request.host_url.rstrip('/')
    scan_url = f"{host_url}/mobile_auth?token={token}"
    qr = qrcode.make(scan_url)
    buf = io.BytesIO()
    qr.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/api/session-status')
def session_status():
    token = request.args.get('token')
    conn = sqlite3.connect('auth_vault.db')
    c = conn.cursor()
    c.execute("SELECT status, user_id FROM sessions WHERE token = ?", (token,))
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({"status": row[0], "user_id": row[1]})
    return jsonify({"status": "EXPIRED"}), 404

@app.route('/mobile_auth')
def mobile_auth():
    token = request.args.get('token')
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Biometric Auth</title>
    <style>
        body { font-family: sans-serif; text-align: center; padding: 40px 20px; background: #0b1329; color: white; }
        .card { background: #1c2541; padding: 30px; border-radius: 16px; max-width: 400px; margin: auto; }
        .btn { width: 100%; padding: 14px 0; background: #0284c7; color: white; border: none; border-radius: 8px; font-weight: bold; font-size: 16px; margin-top: 20px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="card">
        <h2 style="color:#38bdf8;">🔐 हार्डवेयर चाबी पुष्टि</h2>
        <p style="color:#94a3b8;">स्क्रीन पर लॉगिन अनुमति के लिए बायोमेट्रिक लगाएं।</p>
        <button class="btn" onclick="authorize()">👆 फिंगरप्रिंट / स्क्रीन लॉक लगाएं</button>
    </div>
    <script>
        function authorize() {
            window.location.href = '/api/verify-signature?token={{ token }}';
        }
    </script>
</body>
</html>
    """, token=token)

@app.route('/api/verify-signature')
def verify_signature():
    token = request.args.get('token')
    conn = sqlite3.connect('auth_vault.db')
    c = conn.cursor()
    c.execute("SELECT public_key_pem FROM users WHERE user_id = 'user_primary'")
    user_row = c.fetchone()

    with open("my_private_key.pem", "rb") as f:
        priv_key = serialization.load_pem_private_key(f.read(), password=None)
    
    raw_data = token.encode('utf-8')
    sig = priv_key.sign(
        raw_data,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256()
    )

    pub_key = serialization.load_pem_public_key(user_row[0].encode('utf-8'))
    try:
        pub_key.verify(
            sig,
            raw_data,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )
        c.execute("UPDATE sessions SET status = 'VERIFIED', user_id = 'user_primary' WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return """
        <body style='background:#0b1329; color:white; text-align:center; padding:50px 20px; font-family:sans-serif;'>
            <div style='background:#1c2541; padding:30px; border-radius:16px; max-width:400px; margin:auto;'>
                <h2 style='color:#34d399;'>✅ हस्ताक्षर सत्यापित!</h2>
                <p style='color:#94a3b8;'>डेटाबेस में सत्यापन पूरा हुआ।</p>
                <p style='color:#38bdf8;'>अब पिछले टैब पर वापस जाइए!</p>
            </div>
        </body>
        """
    except Exception as e:
        conn.close()
        return "सत्यापन विफल!", 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
