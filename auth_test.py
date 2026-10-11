from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

# 1. फोन के अंदर से अपनी 'प्राइवेट चाबी' उठाना
with open("my_private_key.pem", "rb") as f:
    private_key = serialization.load_pem_private_key(f.read(), password=None)

# 2. वेबसाइट का गुप्त सवाल (वेबसाइट ने कहा: "साबित करो तुम ही हो")
website_challenge = b"Login-Request-Token-98471"

# 3. फोन ने लगाई अपनी डिजिटल मोहर (Digital Signature)
digital_signature = private_key.sign(
    website_challenge,
    padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.MAX_LENGTH
    ),
    hashes.SHA256()
)

print("1. फोन ने सवाल पर अपनी डिजिटल मोहर लगा दी!")

# -------------------------------------------------------------
# अब वेबसाइट की तरफ का काम (सत्यापन):
# -------------------------------------------------------------

# 4. वेबसाइट ने आपकी 'पब्लिक पहचान' (ताला) से चेक किया
with open("my_public_key.pem", "rb") as f:
    public_key = serialization.load_pem_public_key(f.read())

try:
    public_key.verify(
        digital_signature,
        website_challenge,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    print("2. वेबसाइट ने मोहर चेक की: पहचान 100% असली है!")
    print("3. नतीजा: बिना पासवर्ड और बिना OTP के लॉगिन सफल!")
except Exception:
    print("पहचान गलत है! लॉगिन रद्द।")
