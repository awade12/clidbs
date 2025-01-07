"""Security-related utility functions."""
import secrets
import string

def generate_password(length: int = 16) -> str:
    """Generate a secure password with letters, numbers, and special characters."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length)) 

## TODO: add more security (rotating passwords, etc)