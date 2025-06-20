"""
Authentication utilities for Hume AI integration
Handles JWT token creation and validation for secure client-server communication
"""

import jwt
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.config import settings
import logging

logger = logging.getLogger(__name__)

def create_hume_client_token() -> Dict[str, Any]:
    """
    Create a secure JWT token for frontend Hume EVI authentication
    
    Returns:
        Dict containing access_token, token_type, expires_in
    """
    if not settings.HUME_API_KEY:
        raise ValueError("HUME_API_KEY not configured")
    
    if not settings.JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY not configured")
    
    # Create token payload
    now = datetime.utcnow()
    expires_at = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        "iss": "study-buddy",  # Issuer
        "sub": "hume-client",  # Subject
        "aud": "hume-api",     # Audience
        "iat": int(now.timestamp()),  # Issued at
        "exp": int(expires_at.timestamp()),  # Expires at
        "scope": "voice-chat",
        "hume_api_key": settings.HUME_API_KEY[:10] + "...",  # Truncated for security
    }
    
    # Create JWT token
    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    logger.info(f"Created Hume client token (expires: {expires_at})")
    
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "scope": "voice-chat",
        "created_at": int(now.timestamp()),
        "expires_at": int(expires_at.timestamp())
    }

def verify_hume_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a Hume access token
    
    Args:
        token: JWT token to verify
        
    Returns:
        Decoded token payload if valid, None if invalid
    """
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        # Decode and verify token
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience="hume-api",
            issuer="study-buddy"
        )
        
        # Check if token is expired
        if payload.get('exp', 0) < time.time():
            logger.warning("Token expired")
            return None
        
        logger.debug("Token verified successfully")
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return None

def create_hume_api_token() -> str:
    """
    Return the direct Hume API key for server-side operations
    
    This is used for backend API calls to Hume services
    """
    if not settings.HUME_API_KEY:
        raise ValueError("HUME_API_KEY not configured")
    
    return settings.HUME_API_KEY

def validate_hume_config() -> bool:
    """
    Validate that Hume AI configuration is complete
    
    Returns:
        True if configuration is valid, False otherwise
    """
    required_settings = [
        'HUME_API_KEY',
        'JWT_SECRET_KEY'
    ]
    
    missing = []
    for setting in required_settings:
        if not getattr(settings, setting, None):
            missing.append(setting)
    
    if missing:
        logger.error(f"Missing required Hume configuration: {', '.join(missing)}")
        return False
    
    logger.info("Hume AI configuration validated successfully")
    return True

# Middleware helper functions
def extract_token_from_header(authorization_header: str) -> Optional[str]:
    """
    Extract JWT token from Authorization header
    
    Args:
        authorization_header: HTTP Authorization header value
        
    Returns:
        Token string if valid format, None otherwise
    """
    if not authorization_header:
        return None
    
    parts = authorization_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    
    return parts[1]

def get_token_expiry_time(token: str) -> Optional[datetime]:
    """
    Get expiry time from token without full verification
    
    Args:
        token: JWT token
        
    Returns:
        Expiry datetime if parseable, None otherwise
    """
    try:
        # Decode without verification to get expiry
        unverified_payload = jwt.decode(token, options={"verify_signature": False})
        exp_timestamp = unverified_payload.get('exp')
        
        if exp_timestamp:
            return datetime.fromtimestamp(exp_timestamp)
        
    except Exception as e:
        logger.debug(f"Could not parse token expiry: {e}")
    
    return None