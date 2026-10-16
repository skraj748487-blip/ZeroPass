"""
GhostKey Sovereign Node Client Test
Simulates peer-to-peer challenge generation and validation.
"""

import socket
import json
import base64

def run_peer_handshake(host='127.0.0.1', port=9000):
    # 1. Request Challenge from Node
    s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s1.connect((host, port))
    req_challenge = json.dumps({"action": "GET_CHALLENGE", "user_id": "sahil_master"})
    s1.sendall(req_challenge.encode('utf-8'))
    res_challenge = json.loads(s1.recv(4096).decode('utf-8'))
    s1.close()

    print(f"[+] Received Challenge: {res_challenge.get('challenge')}")
    session_token = res_challenge.get('session_token')

    # 2. Simulate Signed Hardware Payload
    client_data = json.dumps({
        "challenge": res_challenge.get('challenge'),
        "origin": "ghostkey.sovereign.node"
    })
    client_data_b64 = base64.urlsafe_b64encode(client_data.encode()).decode()

    # 3. Send Verification to Node
    s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s2.connect((host, port))
    req_verify = json.dumps({
        "action": "VERIFY_SIGNATURE",
        "session_token": session_token,
        "client_data": client_data_b64
    })
    s2.sendall(req_verify.encode('utf-8'))
    res_verify = json.loads(s2.recv(4096).decode('utf-8'))
    s2.close()

    print(f"[✓] Verification Result: {res_verify}")

if __name__ == '__main__':
    run_peer_handshake()
