"""OAuth2 authentication backend for starlette-admin."""
from starlette.authentication import (
    AuthenticationBackend, AuthenticationError, SimpleUser, AuthCredentials
)
from starlette.requests import Request
import logging

from core.auth import oidc_provider
from core.config import settings

logger = logging.getLogger(__name__)


class OAuth2AuthBackend(AuthenticationBackend):
    """Custom authentication backend for starlette-admin using OAuth2/OIDC."""
    
    async def authenticate(self, request: Request):
        """Authenticate request using OAuth2 token from Authorization header or localStorage.
        
        Args:
            request: The incoming request
            
        Returns:
            Tuple of (AuthCredentials, User) if authenticated, None otherwise
        """
        if not settings.OAUTH2_ENABLED or not oidc_provider:
            # OAuth2 not enabled - starlette-admin will show login view
            return None
        
        # Check for token in Authorization header
        auth_header = request.headers.get("Authorization", "")
        token = None
        
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
        
        if not token:
            # No token found - starlette-admin will redirect to login_view
            return None
        
        try:
            # Validate token with OIDC provider
            claims = await oidc_provider.validate_token(token)
            
            # Extract user info
            username = claims.get("preferred_username") or claims.get("email", "unknown")
            
            # Get groups/roles from token
            groups = claims.get("groups", [])
            if isinstance(groups, str):
                groups = [groups]
            
            # Check admin access
            is_admin = settings.OAUTH2_ADMIN_GROUP in (groups or [])
            if not is_admin:
                logger.warning(f"Non-admin user {username} attempted admin access")
                return None
            
            # Return authenticated user with admin scope
            logger.info(f"Admin user {username} authenticated")
            return AuthCredentials(["authenticated", "admin"]), SimpleUser(username)
            
        except Exception as e:
            logger.error(f"OAuth2 admin authentication error: {e}")
            return None

