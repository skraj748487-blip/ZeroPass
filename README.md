# GhostKey Protocol
### Pure-Software Hardware-Bound Biometric Sovereign Identity
Engineered by Sahil Ahmad // Chief Architect

## Overview
GhostKey Protocol is a decentralized identity substrate designed to eliminate passwords, SMS OTPs, and credential stuffing attacks entirely.

By anchoring session entropy directly to physical device Hardware Security Modules (Secure Enclave / Android KeyStore) via WebAuthn, GhostKey provides non-repudiable biometric authentication without storing raw biometrics on remote servers.

Technical Whitepaper: WHITEPAPER.md

## Quickstart: Developer Integration

### 1. Client-Side Script Injection
Add the lightweight GhostKey SDK before your closing body tag:

<script src="https://zeropass1.onrender.com/airauth.js"></script>
<button onclick="GhostKeyLogin()">Sign In with GhostKey</button>

<script>
function GhostKeyLogin() {
    AirAuth.login(function(response) {
        if (response.success) {
            console.log("Verified Identity:", response.user);
            console.log("Cryptographic Proof Token:", response.token);
        }
    });
}
</script>

### 2. Server-to-Server Verification (API)
POST https://zeropass1.onrender.com/api/v1/verify-credential
Header: Content-Type: application/json
Header: X-GhostKey-Secret: YOUR_API_KEY
Body: {"token": "VERIFIED_SESSION_TOKEN"}

Response:
{
  "valid": true,
  "user_id": "sahil_master",
  "verification_type": "HARDWARE_SILICON_ENCLAVE"
}

## License
Engineered and maintained by Sahil Ahmad.

---

## 🌐 Autonomous P2P Sovereign Node Setup

Run your own GhostKey verification node and participate in the decentralized ZKP ledger mesh:

### 1. Installation
git clone https://github.com/skraj748487-blip/ZeroPass.git
cd ZeroPass
pip install -e .

### 2. Start Autonomous Node
python ghostkey_cli.py start-node --port 9000

### 3. Verify Hardware Handshake
python ghostkey_cli.py test-handshake --port 9000

### 4. Audit Distributed Ledger Integrity
python ghostkey_cli.py audit-ledger
