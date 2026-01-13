"""Main FastAPI application."""
from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from contextlib import asynccontextmanager
import logging

from core.config import settings
from core.security import add_cors_middleware, add_trusted_host_middleware, add_proxy_headers_middleware
from core.auth import get_current_user, User, oidc_provider
from core.database import engine, SessionLocal
from models import Base
from api.endpoints import forecasts, price_history, tasks
from tasks.scheduler import start_scheduler, stop_scheduler, get_scheduler_status
from admin.setup import setup_admin
from admin.resources import register_admin_models

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Create tables
Base.metadata.create_all(bind=engine)

# Apply database migrations
def run_migrations():
    """Apply any pending database migrations."""
    db = SessionLocal()
    try:
        from sqlalchemy import text, inspect
        
        # Migration 1: Add region column to forecasting_pricehistory if it doesn't exist
        inspector = inspect(engine)
        columns = [c['name'] for c in inspector.get_columns('forecasting_pricehistory')]
        
        if 'region' not in columns:
            logger.info("Applying migration: Adding region column to forecasting_pricehistory")
            db.execute(text("""
                ALTER TABLE forecasting_pricehistory
                ADD COLUMN region VARCHAR(1)
            """))
            db.commit()
            logger.info("✓ Migration applied: region column added to forecasting_pricehistory")
    except Exception as e:
        db.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        db.close()

try:
    run_migrations()
except Exception as e:
    logger.error(f"Failed to run migrations during startup: {e}")
    raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    # Startup
    logger.info("Starting up FastAPI application")
    start_scheduler()
    
    yield
    
    # Shutdown
    logger.info("Shutting down FastAPI application")
    stop_scheduler()


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    lifespan=lifespan,
)

# Add middleware
add_cors_middleware(app)
add_trusted_host_middleware(app)
add_proxy_headers_middleware(app)

# Setup admin dashboard
admin = setup_admin(app)
register_admin_models(admin)

# Health check endpoint
@app.get("/health", include_in_schema=False)
async def health_check():
    """Health check endpoint - Public endpoint."""
    return JSONResponse({"status": "healthy", "version": settings.PROJECT_VERSION})

# OAuth2 / OIDC Endpoints
@app.get("/api/auth/login", summary="Initiate OAuth2 Login", include_in_schema=False)
async def oauth2_login(request: Request, admin: str = None):
    """Redirect to OIDC provider for authentication.
    
    Args:
        request: The incoming request (used for proper host detection)
        admin: Optional flag indicating admin login (e.g., ?admin=true)
    """
    if not settings.OAUTH2_ENABLED or not oidc_provider:
        return JSONResponse(
            {"error": "OAuth2 is not configured"},
            status_code=501
        )
    
    try:
        config = await oidc_provider.get_discovery_config()
        auth_endpoint = config.get("authorization_endpoint")
        
        if not auth_endpoint:
            raise ValueError("authorization_endpoint not found in discovery config")
        
        # Generate state for CSRF protection
        import secrets
        
        state = secrets.token_urlsafe(32)
        
        # Build redirect_uri from request for proper host detection (handles reverse proxies)
        # This ensures the callback URL matches what was registered in the OAuth2 provider
        redirect_uri = str(request.url_for("oauth2_callback"))
        
        # Build authorization URL without PKCE (simplify for now)
        auth_url = (
            f"{auth_endpoint}?"
            f"client_id={settings.OAUTH2_CLIENT_ID}&"
            f"redirect_uri={redirect_uri}&"
            f"response_type=code&"
            f"scope=openid%20profile%20email&"
            f"state={state}"
        )
        
        logger.info(f"Redirecting to OAuth2 provider: {settings.OAUTH2_PROVIDER_NAME}")
        logger.debug(f"Redirect URI: {redirect_uri}")
        return RedirectResponse(url=auth_url)
    except Exception as e:
        logger.error(f"OAuth2 login error: {e}")
        return JSONResponse(
            {"error": "Failed to initiate login"},
            status_code=500
        )


@app.get("/api/auth/callback", summary="OAuth2 Callback", include_in_schema=False, name="oauth2_callback")
async def oauth2_callback(request: Request, code: str, state: str):
    """Handle OAuth2 provider callback.
    
    Args:
        request: The incoming request
        code: Authorization code from provider
        state: State parameter for CSRF protection
        
    Returns:
        Token response with access_token and redirect
    """
    if not settings.OAUTH2_ENABLED or not oidc_provider:
        return JSONResponse(
            {"error": "OAuth2 is not configured"},
            status_code=501
        )
    
    try:
        import httpx
        
        config = await oidc_provider.get_discovery_config()
        token_endpoint = config.get("token_endpoint")
        
        if not token_endpoint:
            raise ValueError("token_endpoint not found in discovery config")
        
        # Exchange authorization code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": settings.OAUTH2_CLIENT_ID,
                    "client_secret": settings.OAUTH2_CLIENT_SECRET,
                    "redirect_uri": settings.OAUTH2_REDIRECT_URI,
                },
                headers={"Accept": "application/json"},
                timeout=10.0
            )
            
            if token_response.status_code != 200:
                error_detail = token_response.text
                logger.error(f"Token exchange failed: {error_detail}")
                raise ValueError(f"Token endpoint returned {token_response.status_code}: {error_detail}")
            
            tokens = token_response.json()
        
        # Get the token (try access_token first, then id_token)
        access_token = tokens.get("access_token") or tokens.get("id_token")
        
        if not access_token:
            raise ValueError("No access token in response")
        
        # Return HTML that stores token in both localStorage and cookie
        html = f"""
        <html>
        <head><title>Login Success</title></head>
        <body>
            <p>Authenticating...</p>
            <script>
                localStorage.setItem('access_token', '{access_token}');
                window.location.href = '/admin/';
            </script>
        </body>
        </html>
        """
        
        response = HTMLResponse(html)
        # Set secure cookie so server middleware can read the token
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=False,  # Allow JavaScript to read it
            secure=not settings.DEBUG,  # HTTPS only if not in debug mode
            samesite="lax",
            max_age=3600  # 1 hour
        )
        return response
    except Exception as e:
        logger.error(f"OAuth2 callback error: {e}")
        return HTMLResponse(
            f"<h1>Authentication Failed</h1><p>{str(e)}</p>",
            status_code=400
        )


@app.get("/api/auth/validate-token", summary="Validate OAuth2 Token", include_in_schema=False)
async def validate_token(current_user: User = Depends(get_current_user)):
    """Validate the OAuth2 token.
    
    Returns the authenticated user info if token is valid.
    Returns 401 Unauthorized if token is invalid or missing.
    
    This endpoint is used by the frontend to verify tokens before showing protected content.
    """
    return {
        "valid": True,
        "user": {
            "username": current_user.username,
            "email": current_user.email,
            "is_admin": current_user.is_admin,
            "groups": current_user.groups
        }
    }


# Include routers
app.include_router(forecasts.router, prefix=settings.API_V1_STR)
app.include_router(price_history.router, prefix=settings.API_V1_STR)
app.include_router(tasks.router)


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint."""
    return {
        "message": "AgilePredictAPI",
        "version": settings.PROJECT_VERSION,
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
