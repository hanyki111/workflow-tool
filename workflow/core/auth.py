import hashlib
import os
import getpass
from typing import Optional

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
    print("=== Workflow Secret Generation ===")
    token = getpass.getpass("Enter plaintext token to hash: ")
    if not token:
        print("Error: Token cannot be empty.")
        return False
    
    confirm = getpass.getpass("Confirm token: ")
    if token != confirm:
        print("Error: Tokens do not match.")
        return False
    
    save_secret_hash(token)
    print(f"Success: SHA-256 hash saved to {SECRET_FILE}")
    return True
