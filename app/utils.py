import hashlib
import secrets

def generate_etag(content: bytes):
    return hashlib.sha256(content).hexdigest()

def generate_token():
    return secrets.token_urlsafe(48)