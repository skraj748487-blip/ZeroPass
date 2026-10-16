"""
GhostKey Sovereign Gossip & Ledger Substrate v1.0
Cryptographically linked distributed state synchronization.
"""

import hashlib
import json
import time

class SovereignBlock:
    def __init__(self, index, previous_hash, timestamp, verification_data):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.verification_data = verification_data
        self.block_hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps({
            "index": self.index,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "data": self.verification_data
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode('utf-8')).hexdigest()

class GhostKeyLedger:
    def __init__(self, node_id="PEER-NODE-01"):
        self.node_id = node_id
        self.chain = [self.create_genesis_block()]

    def create_genesis_block(self):
        return SovereignBlock(0, "0" * 64, time.time(), {"genesis": "GhostKey Genesis Protocol Anchored by Sahil Ahmad"})

    def get_latest_block(self):
        return self.chain[-1]

    def record_verification(self, user_id, handshake_hash, origin_node):
        prev_block = self.get_latest_block()
        payload = {
            "user_id": user_id,
            "handshake_hash": handshake_hash,
            "origin_node": origin_node,
            "witness": self.node_id
        }
        new_block = SovereignBlock(len(self.chain), prev_block.block_hash, time.time(), payload)
        self.chain.append(new_block)
        return new_block

    def verify_chain_integrity(self):
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            prev = self.chain[i - 1]

            if current.block_hash != current.calculate_hash():
                return False, f"Block {i} hash corruption"
            if current.previous_hash != prev.block_hash:
                return False, f"Block {i} chain link broken"
        return True, "LEDGER_INTEGRITY_VERIFIED"

if __name__ == '__main__':
    print("=" * 60)
    print("⚡ GHOSTKEY DISTRIBUTED LEDGER & GOSSIP ENGINE TEST ⚡")
    print("=" * 60)

    ledger = GhostKeyLedger(node_id="NODE-ALPHA")
    print(f"[+] Genesis Hash: {ledger.get_latest_block().block_hash[:20]}...")

    # Record Handshake Verification Block
    block1 = ledger.record_verification(
        user_id="sahil_master",
        handshake_hash="26a1ece20f120d3a03fb1aee8b0ee5b01ca856c99a7d304c302229fa681d7e21",
        origin_node="GHOSTKEY-PEER-01"
    )
    print(f"[✓] Block {block1.index} Minted: Hash={block1.block_hash[:20]}... Prev={block1.previous_hash[:16]}...")

    # Check Integrity
    valid, msg = ledger.verify_chain_integrity()
    print(f"[✓] Integrity Audit: {valid} ({msg})")
    print("=" * 60)
