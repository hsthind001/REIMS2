"""
Security utilities for authentication

Simple session-based authentication using bcrypt for password hashing
and Starlette session middleware for session management (no JWT)
"""
import bcrypt
from typing import Optional


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against its hash
    
    Args:
        plain_password: Plain text password from user
        hashed_password: Hashed password from database
    
    Returns:
        bool: True if password matches, False otherwise
    """
    # Convert strings to bytes
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Args:
        password: Plain text password
    
    Returns:
        str: Bcrypt hashed password
    """
    # Convert password to bytes, truncate to 72 chars if needed (bcrypt limit)
    password_bytes = password[:72].encode('utf-8')
    
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # Return as string
    return hashed.decode('utf-8')

