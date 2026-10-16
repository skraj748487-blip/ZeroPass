"""
GhostKey Sovereign Node Daemon v1.0
Autonomous P2P cryptographic handshake listener.
"""

import socket
import json
import threading
from core_engine import GhostKeyCore

class SovereignNodeDaemon:
    def __init__(self, host='0.0.0.0', port=9000, node_id="GHOSTKEY-PEER-01"):
        self.host = host
        self.port = port
        self.engine = GhostKeyCore(node_id=node_id)
        self.running = False

    def handle_peer(self, conn, addr):
        try:
            raw_data = conn.recv(4096).decode('utf-8')
            if not raw_data:
                conn.close()
                return

            req = json.loads(raw_data)
            action = req.get('action')

            if action == 'GET_CHALLENGE':
                user_id = req.get('user_id', 'anonymous_peer')
                res = self.engine.generate_hardware_challenge(user_id=user_id)
                conn.sendall(json.dumps(res).encode('utf-8'))

            elif action == 'VERIFY_SIGNATURE':
                token = req.get('session_token')
                payload = req.get('client_data')
                res = self.engine.verify_hardware_signature(token, payload)
                conn.sendall(json.dumps(res).encode('utf-8'))

            else:
                conn.sendall(json.dumps({"error": "UNKNOWN_ACTION"}).encode('utf-8'))

        except Exception as e:
            conn.sendall(json.dumps({"error": str(e)}).encode('utf-8'))
        finally:
            conn.close()

    def start(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen(10)
        self.running = True
        print(f"[⚡] Sovereign P2P Node Listening on {self.host}:{self.port}")

        while self.running:
            try:
                conn, addr = self.server.accept()
                threading.Thread(target=self.handle_peer, args=(conn, addr), daemon=True).start()
            except KeyboardInterrupt:
                break

        self.server.close()

if __name__ == '__main__':
    node = SovereignNodeDaemon()
    node.start()
