"""
Clerk JWT Authentication for FastAPI

This module provides JWT verification for Clerk authentication tokens.
It uses PyJWT with Clerk's JWKS endpoint to verify tokens.
"""

import os
import jwt
from jwt import PyJWKClient
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from functools import lru_cache

# Clerk JWKS URL for token verification
CLERK_JWKS_URL = os.getenv(
    "CLERK_JWKS_URL",
    "https://awaited-prawn-51.clerk.accounts.dev/.well-known/jwks.json"
)

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


@lru_cache()
def get_jwks_client():
    """
    Get a cached JWKS client for Clerk token verification.
    Uses LRU cache to avoid creating new clients for each request.
    """
    return PyJWKClient(CLERK_JWKS_URL)


def verify_clerk_token(token: str) -> dict:
    """
    Verify a Clerk JWT token and return the decoded payload.
    
    Args:
        token: The JWT token string to verify
        
    Returns:
        dict: The decoded JWT payload containing user info
        
    Raises:
        HTTPException: If the token is invalid or expired
    """
    try:
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={
                "verify_aud": False,  # Clerk doesn't always set audience
                "verify_exp": True,
                "verify_iat": True,
            }
        )
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    FastAPI dependency to get the current authenticated user.
    
    Usage:
        @app.get("/api/protected")
        def protected_route(user: dict = Depends(get_current_user)):
            clerk_user_id = user["sub"]
            return {"user_id": clerk_user_id}
    
    Args:
        credentials: The HTTP Bearer credentials from the request
        
    Returns:
        dict: The decoded JWT payload with user information
        
    Raises:
        HTTPException: If no credentials provided or token is invalid
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return verify_clerk_token(credentials.credentials)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    FastAPI dependency to optionally get the current user.
    Returns None if no valid token is provided (does not raise error).
    
    Usage:
        @app.get("/api/public")
        def public_route(user: Optional[dict] = Depends(get_optional_user)):
            if user:
                return {"message": f"Hello, {user['sub']}"}
            return {"message": "Hello, guest"}
    """
    if credentials is None:
        return None
    
    try:
        return verify_clerk_token(credentials.credentials)
    except HTTPException:
        return None
