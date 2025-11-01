"""
Data Security & Encryption (Story 4-5)

Provides optional symmetric encryption using cryptography. If the package is
not installed, gracefully degrades to a no-op encrypt/decrypt.
"""

from typing import Optional

try:
    from cryptography.fernet import Fernet  # type: ignore
except Exception:  # pragma: no cover
    Fernet = None  # type: ignore


def generate_key() -> Optional[bytes]:
    if Fernet is None:
        return None
    return Fernet.generate_key()


def encrypt(data: bytes, key: Optional[bytes]) -> bytes:
    if Fernet is None or not key:
        return data  # no-op
    f = Fernet(key)
    return f.encrypt(data)


def decrypt(token: bytes, key: Optional[bytes]) -> bytes:
    if Fernet is None or not key:
        return token  # no-op
    f = Fernet(key)
    return f.decrypt(token)
