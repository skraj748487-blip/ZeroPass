from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# 1. फोन के अंदर एक मजबूत ताला-चाबी (Key Pair) बनाना
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)

# 2. 'प्राइवेट चाबी' को सुरक्षित फाइल में सेव करना (यह सिर्फ आपकी है)
pem_private = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)
with open("my_private_key.pem", "wb") as f:
    f.write(pem_private)

# 3. 'पब्लिक पहचान' (ताला) निकालना जिसे दुनिया को दिखाना है
public_key = private_key.public_key()
pem_public = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)
with open("my_public_key.pem", "wb") as f:
    f.write(pem_public)

print("बधाई हो! आपकी खुद की डिजिटल चाबी और पहचान तैयार हो गई।")
