"""
Authentication Module - JWT-based API Security
Provides token verification for all API endpoints.
"""

import os
import time
import logging
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from dotenv import load_dotenv

load_dotenv(os.path.expanduser('~/.env'))

logger = logging.getLogger(__name__)

# Security configuration
API_SECRET_KEY = os.getenv("KIMI_API_SECRET_KEY", "")
API_KEY_HEADER = os.getenv("KIMI_API_KEY", "")
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRE_SECONDS = int(os.getenv("KIMI_TOKEN_EXPIRE_SECONDS", "3600"))

security_scheme = HTTPBearer(auto_error=False)


def _verify_api_key(token: str) -> bool:
    """Verify a static API key."""
    if not API_KEY_HEADER:
        return False
    return token == API_KEY_HEADER


def _verify_jwt(token: str) -> dict:
    """Verify a JWT token and return its payload."""
    if not API_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server authentication not configured",
        )
    try:
        payload = jwt.decode(token, API_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("exp", 0) < time.time():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
            )
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> dict:
    """
    Dependency that enforces authentication on endpoints.

    Accepts either:
    - A valid JWT in the Authorization: Bearer <token> header
    - A static API key in the Authorization: Bearer <api_key> header

    If neither KIMI_API_SECRET_KEY nor KIMI_API_KEY is set,
    authentication is disabled (development mode) with a warning.
    """
    # If no auth secrets are configured, allow access with warning (dev mode)
    if not API_SECRET_KEY and not API_KEY_HEADER:
        logger.warning(
            "AUTH DISABLED: Set KIMI_API_SECRET_KEY or KIMI_API_KEY to enable authentication"
        )
        return {"sub": "anonymous", "mode": "dev"}

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Try static API key first
    if _verify_api_key(token):
        return {"sub": "api_key_user", "mode": "api_key"}

    # Try JWT
    if API_SECRET_KEY:
        return _verify_jwt(token)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
    )


def generate_token(subject: str, extra_claims: Optional[dict] = None) -> str:
    """Generate a JWT token (utility for admin/setup scripts)."""
    if not API_SECRET_KEY:
        raise ValueError("KIMI_API_SECRET_KEY must be set to generate tokens")

    payload = {
        "sub": subject,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXPIRE_SECONDS,
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, API_SECRET_KEY, algorithm=JWT_ALGORITHM)
