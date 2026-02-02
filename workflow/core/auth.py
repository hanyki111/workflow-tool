import hashlib
import os
import getpass
from typing import Optional

from workflow.i18n import t

SECRET_FILE = ".workflow/secret"

def hash_token(token: str) -> str:
    """Returns the SHA-256 hash of a string."""
    return hashlib.sha256(token.encode()).hexdigest()

def save_secret_hash(token: str):
    """Saves the hash of the token to the secret file."""
    os.makedirs(os.path.dirname(SECRET_FILE), exist_ok=True)
    hashed = hash_token(token)
    with open(SECRET_FILE, "w") as f:
        f.write(hashed)
    # Set restrictive permissions (600)
    os.chmod(SECRET_FILE, 0o600)

def verify_token(input_token: str) -> bool:
    """Verifies input token against the stored hash."""
    if not os.path.exists(SECRET_FILE):
        return False
    
    with open(SECRET_FILE, "r") as f:
        stored_hash = f.read().strip()
    
    return hash_token(input_token) == stored_hash

def generate_secret_interactive():
    """Prompts for token and saves hash."""
    print(t('auth.title'))
    token = getpass.getpass(t('auth.prompt'))
    if not token:
        print(t('auth.empty_error'))
        return False

    confirm = getpass.getpass(t('auth.confirm'))
    if token != confirm:
        print(t('auth.mismatch_error'))
        return False

    save_secret_hash(token)
    print(t('auth.success', path=SECRET_FILE))
    return True
