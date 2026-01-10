"""Admin dashboard setup and configuration."""
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.authentication import AuthenticationMiddleware
from sqlalchemy.orm import Session
from core.database import engine, SessionLocal
from core.config import settings
from core.auth import oidc_provider
from admin.auth import OAuth2AuthBackend
import logging

logger = logging.getLogger(__name__)


class AdminAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to protect admin routes with OAuth2 authentication."""
    
    async def dispatch(self, request: Request, call_next):
        """Check authentication for /admin routes.
        
        Args:
            request: The incoming request
            call_next: The next middleware/endpoint
            
        Returns:
            Response from next middleware or redirect to login
        """
        # Only check /admin routes (both UI and API)
        if not request.url.path.startswith("/admin"):
            return await call_next(request)
        
        # Check for token in Authorization header or cookie
        auth_header = request.headers.get("Authorization", "")
        token = None
        
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
        else:
            # If no token in header, check cookie
            cookie_token = request.cookies.get("access_token")
            if cookie_token:
                token = cookie_token
                # Modify request scope to add Authorization header for downstream handlers
                request.scope["headers"] = list(request.scope.get("headers", []))
                request.scope["headers"].append((b"authorization", f"Bearer {cookie_token}".encode()))
        
        # If no token found, redirect to login
        if not token:
            return RedirectResponse(url="/api/auth/login?admin=true", status_code=302)
        
        # Validate token with OIDC provider
        if settings.OAUTH2_ENABLED and oidc_provider:
            try:
                await oidc_provider.validate_token(token)
            except Exception as e:
                # Token is invalid/expired, redirect to login
                logger.warning(f"Token validation failed in admin middleware: {e}")
                return RedirectResponse(url="/api/auth/login?admin=true", status_code=302)
        
        return await call_next(request)
        
        return await call_next(request)


def setup_admin(app: FastAPI):
    """Initialize and configure the admin dashboard with OAuth2 protection.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        Admin instance that can register models
    """
    # Import here to avoid circular imports
    from starlette_admin.contrib.sqla import Admin
    from admin.custom_views import SchedulerInfoView
    
    # Add OAuth2 authentication middleware if enabled
    if settings.OAUTH2_ENABLED:
        # Add auth middleware for token validation
        app.add_middleware(AuthenticationMiddleware, backend=OAuth2AuthBackend())
        # Add redirect middleware for unauthenticated access
        app.add_middleware(AdminAuthMiddleware)
    
    # Create admin instance (no login_view parameter)
    admin = Admin(engine=engine, title="AgilePredictAPI Admin")
    
    # Register custom views (non-model views)
    admin.add_view(SchedulerInfoView())
    
    # Mount admin app
    admin.mount_to(app)
    
    logger.info("Admin dashboard configured at /admin with OAuth2 protection")
    
    return admin


def get_admin_session() -> Session:
    """Get a database session for admin operations."""
    return SessionLocal()
