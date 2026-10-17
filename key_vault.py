"""
GhostKey Sovereign Commercial Key Vault
Generates and signs cryptographically verifiable developer license keys.
"""

import os
import hmac
import hashlib
import time
import base64

class CommercialKeyVault:
    def __init__(self, master_secret=None):
        self.master_secret = master_secret or os.urandom(32)

    def issue_license_key(self, client_email, plan="PRO_TIER"):
        issued_at = int(time.time())
        expiry = issued_at + (30 * 86400) # 30 Days active
        payload = f"{client_email}:{plan}:{issued_at}:{expiry}"
        
        signature = hmac.new(self.master_secret, payload.encode(), hashlib.sha256).hexdigest()[:24]
        raw_key = f"gk_live_{base64.urlsafe_b64encode(payload.encode()).decode().rstrip('=')}_{signature}"
        
        return {
            "api_key": raw_key,
            "email": client_email,
            "plan": plan,
            "expires_at": expiry
        }

    def verify_license_key(self, api_key):
        try:
            parts = api_key.split('_')
            if len(parts) != 4 or parts[0] != 'gk' or parts[1] != 'live':
                return False, "INVALID_KEY_FORMAT"
            
            b64_payload = parts[2] + '=' * (-len(parts[2]) % 4)
            payload = base64.urlsafe_b64decode(b64_payload).decode()
            received_sig = parts[3]
            
            expected_sig = hmac.new(self.master_secret, payload.encode(), hashlib.sha256).hexdigest()[:24]
            if not hmac.compare_digest(received_sig, expected_sig):
                return False, "CRYPTOGRAPHIC_TAMPER_DETECTED"
            
            email, plan, issued_at, expiry = payload.split(':')
            if time.time() > int(expiry):
                return False, "LICENSE_EXPIRED"
                
            return True, {"email": email, "plan": plan, "status": "ACTIVE"}
        except Exception as e:
            return False, f"VERIFICATION_ERROR: {str(e)}"

if __name__ == '__main__':
    vault = CommercialKeyVault()
    key = vault.issue_license_key("enterprise@client.com", plan="SCALE_100K")
    print(f"[+] Issued Key: {key['api_key'][:35]}...")
    valid, details = vault.verify_license_key(key['api_key'])
    print(f"[✓] Validation: {valid} -> {details}")
