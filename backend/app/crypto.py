"""Symmetric encryption for sensitive settings (API keys, passwords)."""
import base64
import hashlib
import os

from cryptography.fernet import Fernet

_ENCRYPTION_KEY: bytes | None = None
_PREFIX = "enc:"


def _get_key() -> bytes:
    global _ENCRYPTION_KEY
    if _ENCRYPTION_KEY is None:
        raw = os.environ.get("SETTINGS_ENCRYPTION_KEY", "")
        if not raw:
            # Derive from JWT secret file or fallback
            data_dir = os.path.dirname(os.environ.get("DB_PATH", "/app/data/paperpulse.db"))
            key_file = os.path.join(data_dir, ".encryption_key")
            if os.path.isfile(key_file):
                raw = open(key_file).read().strip()
            else:
                raw = Fernet.generate_key().decode()
                os.makedirs(data_dir, exist_ok=True)
                with open(key_file, "w") as f:
                    f.write(raw)
        # Ensure it's a valid Fernet key (url-safe base64, 32 bytes)
        try:
            Fernet(raw.encode() if isinstance(raw, str) else raw)
            _ENCRYPTION_KEY = raw.encode() if isinstance(raw, str) else raw
        except Exception:
            # Derive a valid key from the raw value
            derived = base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest())
            _ENCRYPTION_KEY = derived
    return _ENCRYPTION_KEY


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value. Returns prefixed ciphertext."""
    if not plaintext or plaintext.startswith(_PREFIX):
        return plaintext
    f = Fernet(_get_key())
    return _PREFIX + f.encrypt(plaintext.encode()).decode()


def decrypt_value(stored: str) -> str:
    """Decrypt a stored value. Returns plaintext. Passes through unencrypted values."""
    if not stored or not stored.startswith(_PREFIX):
        return stored
    f = Fernet(_get_key())
    return f.decrypt(stored[len(_PREFIX):].encode()).decode()
