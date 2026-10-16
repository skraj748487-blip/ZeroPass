"""
GhostKey Sovereign Multi-Node Daemon v2.1
Autonomous P2P handshake & decentralized ZKP ledger broadcast.
"""

import socket
import json
import threading
from core_engine import GhostKeyCore
from gossip_engine import GhostKeyLedger

class SovereignNodeDaemon:
    def __init__(self, host='0.0.0.0', port=9000, node_id="PEER-NODE-01", peers=None):
        self.host = host
        self.port = port
        self.node_id = node_id
        self.peers = peers or []
        self.engine = GhostKeyCore(node_id=node_id)
        self.ledger = GhostKeyLedger(node_id=node_id)
        self.running = False

    def broadcast_block(self, block_data):
        for peer_ip, peer_port in self.peers:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2.0)
                s.connect((peer_ip, peer_port))
                msg = json.dumps({"action": "GOSSIP_BLOCK", "block": block_data})
                s.sendall(msg.encode('utf-8'))
                s.close()
            except Exception:
                pass

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
                
                # ZKP Ledger integration
                if res.get('verified'):
                    new_block, salt = self.ledger.record_zkp_verification(
                        user_id=res.get('user_id'),
                        handshake_hash=res.get('handshake_hash'),
                        origin_node=self.node_id
                    )
                    res["block_index"] = new_block.index
                    res["block_hash"] = new_block.block_hash
                    res["zk_commitment"] = new_block.verification_data.get("zk_commitment")
                    
                    threading.Thread(target=self.broadcast_block, args=({
                        "index": new_block.index,
                        "hash": new_block.block_hash,
                        "prev_hash": new_block.previous_hash,
                        "data": new_block.verification_data
                    },), daemon=True).start()

                conn.sendall(json.dumps(res).encode('utf-8'))

            elif action == 'GOSSIP_BLOCK':
                incoming_block = req.get('block', {})
                print(f"[🔗] Received Block {incoming_block.get('index')} from network: {incoming_block.get('hash')[:16]}...")
                conn.sendall(json.dumps({"status": "BLOCK_ACKNOWLEDGED"}).encode('utf-8'))

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
        print(f"[⚡] Sovereign P2P Mesh Node Online: {self.host}:{self.port} (ID: {self.node_id})")

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
