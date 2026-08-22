import os
import base64
import hashlib
from cryptography.fernet import Fernet

# Master encryption key from environment variable or default fallback key
MASTER_SECRET = os.getenv("CLOUDFORGE_ENCRYPTION_KEY", "cloudforge_super_secret_master_key_2026")

def _get_fernet_key(secret: str) -> bytes:
    """Metin halindeki secret anahtarını 32-byte URL-safe Fernet anahtarına çevirir."""
    digest = hashlib.sha256(secret.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest)

def encrypt_secret(plain_text: str) -> str:
    """Verilen düz metin şifreyi (ör. API_KEY) Fernet (AES-128) ile şifreler."""
    if not plain_text:
        return ""
    key = _get_fernet_key(MASTER_SECRET)
    fernet = Fernet(key)
    encrypted_bytes = fernet.encrypt(plain_text.encode('utf-8'))
    return encrypted_bytes.decode('utf-8')

def decrypt_secret(cipher_text: str) -> str:
    """Şifreli metni çözer ve orijinal düz metni verir."""
    if not cipher_text:
        return ""
    try:
        key = _get_fernet_key(MASTER_SECRET)
        fernet = Fernet(key)
        decrypted_bytes = fernet.decrypt(cipher_text.encode('utf-8'))
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        print(f"[CryptoService] Şifre çözme hatası: {e}")
        return ""
