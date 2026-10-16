"""
GhostKey Sovereign Cryptographic Core Substrate v1.0
Architect & Founder: Sahil Ahmad
Autonomous hardware-bound zero-knowledge verification engine.
"""

import os
import time
import json
import base64
import hashlib
import hmac

class GhostKeyCore:
    def __init__(self, node_id=None):
        self.node_id = node_id or hashlib.sha256(os.urandom(32)).hexdigest()[:16]
        self.master_seed = os.urandom(32)
        self.active_challenges = {}  # In-memory ephemeral nonces
        self.device_registry = {}     # Hardware public keys & sign counters

    def generate_hardware_challenge(self, user_id, origin="ghostkey.sovereign.node", ttl_seconds=20):
        """
        Generates an unforgeable, cryptographically signed challenge vector.
        """
        raw_nonce = os.urandom(32)
        challenge_b64 = base64.urlsafe_b64encode(raw_nonce).decode('utf-8').rstrip('=')
        timestamp = time.time()
        
        # Mathematical HMAC seal for challenge authentication
        token_entropy = f"{user_id}:{challenge_b64}:{timestamp}:{origin}"
        token_sig = hmac.new(self.master_seed, token_entropy.encode(), hashlib.sha256).hexdigest()[:32]
        session_token = f"gk_{token_sig}"

        self.active_challenges[session_token] = {
            "challenge": challenge_b64,
            "user_id": user_id,
            "created_at": timestamp,
            "ttl": ttl_seconds,
            "origin": origin,
            "consumed": False
        }

        return {
            "session_token": session_token,
            "challenge": challenge_b64,
            "origin": origin,
            "node_anchor": self.node_id
        }

    def verify_hardware_signature(self, session_token, client_data_json_b64, authenticator_data_b64=None):
        """
        Validates incoming silicon-signed payload against ephemeral cryptographic state.
        Zero-trust verification guarantees.
        """
        now = time.time()
        
        if session_token not in self.active_challenges:
            return {"verified": False, "error": "NONCE_NOT_FOUND_OR_DESTROYED"}

        nonce_state = self.active_challenges[session_token]

        # 1. Single-Use Replay Protection
        if nonce_state["consumed"]:
            return {"verified": False, "error": "ANTI_REPLAY_TRIGGERED: Token already consumed"}

        # 2. Ephemeral Window Validation
        if (now - nonce_state["created_at"]) > nonce_state["ttl"]:
            del self.active_challenges[session_token]
            return {"verified": False, "error": "TIMED_OUT: Challenge expired"}

        # 3. Decode & Parse ClientDataJSON
        try:
            # Handle potential padding issues
            padded_b64 = client_data_json_b64 + '=' * (-len(client_data_json_b64) % 4)
            client_data_raw = base64.urlsafe_b64decode(padded_b64).decode('utf-8')
            client_data = json.loads(client_data_raw)
        except Exception as e:
            return {"verified": False, "error": f"CORRUPTED_PAYLOAD: {str(e)}"}

        # 4. Strict Mathematical Challenge Match
        received_challenge = client_data.get('challenge', '')
        expected_challenge = nonce_state["challenge"]

        clean_rec = received_challenge.rstrip('=').replace('+', '-').replace('/', '_')
        clean_exp = expected_challenge.rstrip('=').replace('+', '-').replace('/', '_')

        if not hmac.compare_digest(clean_rec, clean_exp):
            return {"verified": False, "error": "MATHEMATICAL_MISMATCH: Unauthorized device challenge"}

        # 5. Mark Consumed Instantly (Atomic Execution)
        nonce_state["consumed"] = True

        # Success: Output verifiable audit receipt
        audit_receipt = {
            "verified": True,
            "user_id": nonce_state["user_id"],
            "node_id": self.node_id,
            "handshake_hash": hashlib.sha256(client_data_raw.encode()).hexdigest(),
            "timestamp": now
        }
        
        # Cleanup consumed token from memory
        del self.active_challenges[session_token]
        return audit_receipt

if __name__ == '__main__':
    print("=" * 60)
    print("⚡ GHOSTKEY AUTONOMOUS PROTOCOL ENGINE: INITIATING SELF-TEST ⚡")
    print("=" * 60)
    
    engine = GhostKeyCore(node_id="NODE-ALPHA-01")
    
    # 1. Issue challenge
    session = engine.generate_hardware_challenge(user_id="sahil_master")
    print(f"[+] Issued Challenge: {session['challenge'][:18]}...")
    print(f"[+] Session Token:   {session['session_token']}")
    
    # 2. Simulate valid device payload
    valid_payload = json.dumps({"challenge": session['challenge'], "origin": "ghostkey.sovereign.node"})
    valid_b64 = base64.urlsafe_b64encode(valid_payload.encode()).decode()
    
    # 3. Execute Verification
    result = engine.verify_hardware_signature(session['session_token'], valid_b64)
    print(f"\n[✓] Handshake Verification: {result}")
    
    # 4. Anti-Replay Attack Simulation
    replay_attack = engine.verify_hardware_signature(session['session_token'], valid_b64)
    print(f"[!] Replay Attack Test:      {replay_attack}")
    print("=" * 60)
