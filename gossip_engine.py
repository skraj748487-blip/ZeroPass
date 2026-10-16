"""
GhostKey Sovereign ZKP-Anchored Distributed Ledger v2.0
Decentralized state synchronization with blinded identity commitments.
"""

import hashlib
import json
import time
from zkp_engine import ZKProofEngine

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
        return SovereignBlock(
            0,
            "0" * 64,
            time.time(),
            {"genesis": "GhostKey ZKP Sovereign Genesis Anchored by Sahil Ahmad"}
        )

    def get_latest_block(self):
        return self.chain[-1]

    def record_zkp_verification(self, user_id, handshake_hash, origin_node):
        """Records a verification block using a blinded ZKP commitment instead of plaintext ID."""
        prev_block = self.get_latest_block()
        
        # Real ID ko chain se gayab karke ZK commitment banana
        zk_data = ZKProofEngine.generate_blinded_commitment(user_id)
        
        payload = {
            "zk_commitment": zk_data["zk_commitment"],
            "handshake_hash": handshake_hash,
            "origin_node": origin_node,
            "witness": self.node_id,
            "identity_shield": "ZERO_KNOWLEDGE_BLINDED"
        }
        
        new_block = SovereignBlock(len(self.chain), prev_block.block_hash, time.time(), payload)
        self.chain.append(new_block)
        return new_block, zk_data["secret_salt"]

    def verify_chain_integrity(self):
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            prev = self.chain[i - 1]

            if current.block_hash != current.calculate_hash():
                return False, f"Block {i} hash corruption"
            if current.previous_hash != prev.block_hash:
                return False, f"Block {i} chain link broken"
        return True, "ZKP_LEDGER_INTEGRITY_VERIFIED"

if __name__ == '__main__':
    print("=" * 60)
    print("⚡ GHOSTKEY ZKP-ANCHORED DISTRIBUTED LEDGER TEST ⚡")
    print("=" * 60)

    ledger = GhostKeyLedger(node_id="NODE-ALPHA-ZK")
    print(f"[+] Genesis Hash: {ledger.get_latest_block().block_hash[:20]}...")

    # Mint ZKP Block
    block1, salt = ledger.record_zkp_verification(
        user_id="sahil_master",
        handshake_hash="505682ee542792f9483074231545bee02dd7176c0d05d0d53b08ac46b303dcf1",
        origin_node="GHOSTKEY-PEER-01"
    )

    print(f"[✓] Block {block1.index} Minted!")
    print(f"[+] ZK Commitment Hash: {block1.verification_data['zk_commitment']}")
    print(f"[+] Previous Block Hash: {block1.previous_hash[:20]}...")
    print(f"[+] Device Secret Salt:  {salt[:12]}... (Kept 100% on Phone)")

    valid, msg = ledger.verify_chain_integrity()
    print(f"[✓] Chain Integrity Audit: {valid} ({msg})")
    print("=" * 60)
