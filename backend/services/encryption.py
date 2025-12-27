"""
Encryption Service

Provides secure hashing and encryption for API keys.
Uses bcrypt for hashing (one-way) and optional AES for encryption (two-way).
"""

from passlib.context import CryptContext
import secrets
import hashlib

# Bcrypt context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using bcrypt.
    This is a one-way hash - the original key cannot be recovered.
    """
    return pwd_context.hash(api_key)


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against its hash.
    Returns True if the key matches.
    """
    return pwd_context.verify(plain_key, hashed_key)


def get_key_prefix(api_key: str, length: int = 8) -> str:
    """
    Get the prefix of an API key for display purposes.
    E.g., "sk-abc12345..." for "sk-abc12345678901234567890"
    """
    if len(api_key) <= length:
        return api_key[:3] + "***"
    return api_key[:length]


def get_key_suffix(api_key: str, length: int = 4) -> str:
    """
    Get the suffix of an API key for display purposes.
    E.g., "...7890" for "sk-abc12345678901234567890"
    """
    if len(api_key) <= length:
        return "***"
    return api_key[-length:]


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token"""
    return secrets.token_urlsafe(length)


def fingerprint_key(api_key: str) -> str:
    """
    Generate a short fingerprint of an API key for logging.
    Uses SHA-256 and returns first 12 characters.
    """
    return hashlib.sha256(api_key.encode()).hexdigest()[:12]
