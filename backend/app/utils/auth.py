"""
Authentication utilities for Hume AI integration
Handles JWT token creation and validation for secure client-server communication
"""

import jwt
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.config import settings
from app.services.evi_config import get_or_create_study_buddy_config
import logging
import httpx

logger = logging.getLogger(__name__)

async def create_hume_client_token() -> Dict[str, Any]:
    """
    Create a secure JWT token and get EVI config for frontend Hume EVI authentication.
    
    Returns:
        Dict containing access_token, config_id, and other connection details.
    """
    if not settings.HUME_API_KEY or not settings.JWT_SECRET_KEY:
        raise ValueError("HUME_API_KEY and JWT_SECRET_KEY must be configured")

    # 1. Get or create the EVI configuration
    config_id = await get_or_create_study_buddy_config()
    
    # If config creation fails, we cannot proceed with voice chat.
    if not config_id:
        logger.error("Failed to obtain Hume EVI Config ID. Cannot create client token for voice.")
        # Return a structure that indicates failure to the frontend.
        return {
            "error": "EVI Configuration Failed",
            "message": "The backend could not create a configuration for the voice assistant."
        }

    # 2. Exchange API key + secret key for an access token via Hume OAuth2-CC endpoint
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                "https://api.hume.ai/oauth2-cc/token",
                auth=(settings.HUME_API_KEY, settings.HUME_SECRET_KEY),
                data={"grant_type": "client_credentials"},
                headers={"Accept": "application/json"}
            )
            response.raise_for_status()
            token_data = response.json()
            access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in")
            token_type = token_data.get("token_type", "Bearer")

            if not access_token:
                raise ValueError("Hume token response missing 'access_token'")

    except Exception as e:
        logger.error(f"Failed to obtain Hume access token: {e}")
        return {
            "error": "Token Generation Failed",
            "message": "Could not obtain access token from Hume API."
        }

    expires_at = datetime.utcnow() + timedelta(seconds=expires_in or 0)
    logger.info(f"Obtained Hume access token (expires: {expires_at}) for config_id: {config_id}")

    return {
        "access_token": access_token,
        "token_type": token_type,
        "expires_in": expires_in,
        "scope": "voice-chat",
        "created_at": int(datetime.utcnow().timestamp()),
        "expires_at": int(expires_at.timestamp()),
        "config_id": config_id,
        "hostname": "api.hume.ai"
    }

def verify_hume_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a Hume access token.
    
    Args:
        token: JWT token to verify
        
    Returns:
        Decoded token payload if valid, None if invalid
    """
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        # Decode and verify token using the Hume Secret Key
        payload = jwt.decode(
            token,
            settings.HUME_SECRET_KEY,
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