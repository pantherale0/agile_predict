"""OAuth2 OIDC authentication with external providers (Authentik, Azure Entra, Google, etc.)."""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import logging
import httpx

from core.config import settings

logger = logging.getLogger(__name__)

# OAuth2 scheme for token-based authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Token data payload."""
    username: Optional[str] = None
    sub: Optional[str] = None
    groups: Optional[list] = None


class User(BaseModel):
    """User model from OIDC provider."""
    username: str
    email: Optional[str] = None
    groups: list = []
    is_admin: bool = False

    @property
    def has_admin_access(self) -> bool:
        """Check if user has admin access based on group membership."""
        return settings.OAUTH2_ADMIN_GROUP in self.groups or self.is_admin


class OIDCProvider:
    """OIDC Provider client for external authentication."""
    
    def __init__(self):
        self.discovery_url = settings.OAUTH2_DISCOVERY_URL
        self.client_id = settings.OAUTH2_CLIENT_ID
        self.client_secret = settings.OAUTH2_CLIENT_SECRET
        self.redirect_uri = settings.OAUTH2_REDIRECT_URI
        self._jwks_cache: Optional[Dict[str, Any]] = None
        self._discovery_cache: Optional[Dict[str, Any]] = None
        self._cache_time: Dict[str, datetime] = {}
        self._cache_ttl = 3600  # Cache for 1 hour
    
    async def get_discovery_config(self) -> Dict[str, Any]:
        """Fetch OIDC discovery configuration from provider (with caching).
        
        Returns:
            OIDC discovery configuration
        """
        # Check if cache is valid
        cache_key = "discovery"
        if (self._discovery_cache and 
            cache_key in self._cache_time and 
            datetime.now(timezone.utc) - self._cache_time[cache_key] < timedelta(seconds=self._cache_ttl)):
            logger.debug("Using cached OIDC discovery config")
            return self._discovery_cache
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.discovery_url}/.well-known/openid-configuration",
                    timeout=10.0
                )
                response.raise_for_status()
                self._discovery_cache = response.json()
                self._cache_time[cache_key] = datetime.now(timezone.utc)
                logger.debug("Fetched and cached OIDC discovery config")
                return self._discovery_cache
        except Exception as e:
            logger.error(f"Failed to fetch OIDC discovery config: {e}")
            raise
    
    async def get_jwks(self, jwks_uri: str) -> Dict[str, Any]:
        """Fetch JWKS from provider (with caching).
        
        Args:
            jwks_uri: The JWKS URI from discovery config
            
        Returns:
            JWKS data
        """
        # Check if cache is valid
        cache_key = "jwks"
        if (self._jwks_cache and 
            cache_key in self._cache_time and 
            datetime.now(timezone.utc) - self._cache_time[cache_key] < timedelta(seconds=self._cache_ttl)):
            logger.debug("Using cached JWKS")
            return self._jwks_cache
        
        try:
            async with httpx.AsyncClient() as client:
                jwks_response = await client.get(jwks_uri, timeout=10.0)
                jwks_response.raise_for_status()
                self._jwks_cache = jwks_response.json()
                self._cache_time[cache_key] = datetime.now(timezone.utc)
                logger.debug("Fetched and cached JWKS")
                return self._jwks_cache
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            raise
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate and decode OIDC token.
        
        Args:
            token: The ID token from the provider
            
        Returns:
            Decoded token claims
            
        Raises:
            HTTPException: If token is invalid
        """
        try:
            # Get JWKS from provider (cached)
            config = await self.get_discovery_config()
            jwks_uri = config.get("jwks_uri")
            
            jwks = await self.get_jwks(jwks_uri)
            
            # Decode and validate token with JWKS
            payload = jwt.get_unverified_claims(token)
            
            # Verify token signature and claims
            decoded = jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                audience=self.client_id,
            )
            return decoded
        except JWTError as e:
            # Handle specific JWT errors
            error_msg = str(e)
            if "expired" in error_msg.lower():
                logger.warning(f"Token has expired: {e}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired. Please log in again.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                logger.error(f"Token validation failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate token",
                headers={"WWW-Authenticate": "Bearer"},
            )


# Global OIDC provider instance
oidc_provider = OIDCProvider() if settings.OAUTH2_ENABLED else None


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Validate OIDC token and return current user.
    
    Args:
        token: The access/ID token from the Authorization header
        
    Returns:
        The authenticated user
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    if not settings.OAUTH2_ENABLED or not oidc_provider:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OAuth2 is not configured"
        )
    
    try:
        # Validate token with OIDC provider
        claims = await oidc_provider.validate_token(token)
        
        # Extract user information from token claims
        username = claims.get("preferred_username") or claims.get("email", "unknown")
        email = claims.get("email")
        
        # Get groups/roles from token (varies by provider)
        # Authentik: groups claim
        # Azure: roles claim or group membership
        groups = claims.get("groups", [])
        if isinstance(groups, str):
            groups = [groups]
        
        user = User(
            username=username,
            email=email,
            groups=groups or [],
            is_admin=settings.OAUTH2_ADMIN_GROUP in (groups or [])
        )
        return user
    except Exception as e:
        logger.error(f"User authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
