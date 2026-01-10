"""Main FastAPI application."""
from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from contextlib import asynccontextmanager
import logging

from core.config import settings
from core.security import add_cors_middleware, add_trusted_host_middleware
from core.auth import get_current_user, User, oidc_provider
from core.database import engine
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

# Setup admin dashboard
admin = setup_admin(app)
register_admin_models(admin)

# Health check endpoint
@app.get("/health", include_in_schema=False)
async def health_check():
    """Health check endpoint - Public endpoint."""
    return JSONResponse({"status": "healthy", "version": settings.PROJECT_VERSION})


# Scheduler Status Page
@app.get("/scheduler-status", response_class=HTMLResponse, include_in_schema=False)
async def scheduler_status_page():
    """Display scheduler status page with trigger buttons.
    
    Client-side OAuth2 authentication via localStorage token.
    """
    # Return HTML with client-side auth check
    return _get_scheduler_status_html()


def _get_scheduler_status_html():
    """Generate HTML with client-side OAuth2 auth check."""
    status = get_scheduler_status()
    
    # Build HTML table with jobs
    jobs_html = ""
    for job in status.get("jobs", []):
        trigger_str = str(job.get('trigger', 'N/A')).replace('<', '&lt;').replace('>', '&gt;')
        next_run = str(job.get('next_run_time', 'N/A'))
        jobs_html += f"""
        <tr>
            <td><code>{job.get('id')}</code></td>
            <td><strong>{job.get('name')}</strong></td>
            <td><small>{trigger_str}</small></td>
            <td><small>{next_run}</small></td>
            <td>
                <button type="button" onclick="triggerJob('{job.get('id')}')" class="btn btn-sm btn-primary">
                    ⚡ Trigger Now
                </button>
            </td>
        </tr>
        """
    
    scheduler_status_text = "🟢 Running" if status.get("running") else "🔴 Stopped"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Scheduler Status - AgilePredictAPI</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.6.0/dist/css/bootstrap.min.css">
        <style>
            body {{ padding: 20px; background: #f5f5f5; }}
            .container {{ background: white; border-radius: 8px; padding: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .status-badge {{ font-size: 1.2em; padding: 10px 20px; border-radius: 5px; display: inline-block; }}
            table {{ margin-top: 20px; }}
            th {{ background: #343a40; color: white; font-weight: 600; }}
            code {{ background: #f8f9fa; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }}
            .btn-primary {{ background: #007bff; border: none; }}
            .btn-primary:hover {{ background: #0056b3; }}
            .header-section {{ margin-bottom: 30px; border-bottom: 2px solid #007bff; padding-bottom: 15px; }}
            .info-text {{ color: #666; margin-top: 10px; }}
        </style>
    </head>
    <body>
        <div id="auth-check" class="container" style="margin-top: 50px; text-align: center; display: none;">
            <h2>🔐 Authentication Required</h2>
            <p class="text-muted">You need to log in to access this page.</p>
            <p id="auth-message" class="text-warning" style="display: none;"></p>
            <a href="/api/auth/login?admin=true" class="btn btn-primary btn-lg">Login with Authentik</a>
        </div>
        
        <div id="content" class="container" style="display: none;">
            <div class="header-section">
                <h1>⏰ Scheduler Status</h1>
                <p class="info-text">Manage and monitor scheduled background jobs</p>
            </div>
            
            <div class="alert alert-info">
                <strong>Status:</strong> <span class="status-badge">{scheduler_status_text}</span>
            </div>
            
            <h3>📋 Scheduled Jobs ({len(status.get('jobs', []))} total)</h3>
            <table class="table table-striped table-hover">
                <thead class="table-dark">
                    <tr>
                        <th style="width: 150px;">Job ID</th>
                        <th style="width: 220px;">Job Name</th>
                        <th>Trigger Schedule</th>
                        <th>Next Run Time</th>
                        <th style="width: 150px;">Action</th>
                    </tr>
                </thead>
                <tbody>
                    {jobs_html}
                </tbody>
            </table>
            
            <hr>
            <p class="text-muted"><small>💡 Click "⚡ Trigger Now" to manually execute a job immediately. Results will be logged to the Task Logs in the admin panel.</small></p>
            
            <div style="margin-top: 20px;">
                <a href="/admin/task-log/list" class="btn btn-secondary">📖 View Task Logs</a>
                <a href="/docs" class="btn btn-secondary">📚 API Documentation</a>
                <a href="/admin/" class="btn btn-secondary">🎛️ Admin Dashboard</a>
            </div>
        </div>
        </div>
        
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@4.6.0/dist/js/bootstrap.min.js"></script>
        <script>
            // Validate token with server before showing content
            window.addEventListener('DOMContentLoaded', async function() {{
                const token = localStorage.getItem('access_token');
                if (!token) {{
                    showAuthCheck();
                    return;
                }}
                
                // Validate token with server
                try {{
                    const response = await fetch('/api/auth/validate-token', {{
                        headers: {{
                            'Authorization': `Bearer ${{token}}`
                        }}
                    }});
                    
                    if (response.ok) {{
                        showContent();
                    }} else if (response.status === 401) {{
                        // Token expired or invalid - clear it and show login
                        localStorage.removeItem('access_token');
                        showAuthCheck("Token expired. Please log in again.");
                    }} else {{
                        localStorage.removeItem('access_token');
                        showAuthCheck();
                    }}
                }} catch (error) {{
                    console.error('Token validation failed:', error);
                    showAuthCheck();
                }}
            }});
            
            function showAuthCheck(message = null) {{
                document.getElementById('auth-check').style.display = 'block';
                document.getElementById('content').style.display = 'none';
                if (message) {{
                    const msgEl = document.getElementById('auth-message');
                    if (msgEl) {{
                        msgEl.textContent = message;
                        msgEl.style.display = 'block';
                    }}
                }}
            }}
            
            function showContent() {{
                document.getElementById('auth-check').style.display = 'none';
                document.getElementById('content').style.display = 'block';
            }}
            
            function triggerJob(jobId) {{
                const btn = event.target;
                const originalText = btn.textContent;
                btn.disabled = true;
                btn.textContent = '⏳ Triggering...';
                const token = localStorage.getItem('access_token');
                
                fetch(`/api/tasks/jobs/${{jobId}}/trigger`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json', 'Authorization': token ? `Bearer ${{token}}` : ''}}
                }})
                .then(r => {{
                    if (r.status === 401) {{
                        window.location.href = '/api/auth/login';
                        return;
                    }}
                    if (!r.ok) throw new Error(`HTTP ${{r.status}}`);
                    return r.json();
                }})
                .then(data => {{
                    if (data && data.success) {{
                        btn.textContent = '✅ Success!';
                        btn.classList.remove('btn-primary');
                        btn.classList.add('btn-success');
                        setTimeout(() => {{
                            btn.textContent = originalText;
                            btn.classList.remove('btn-success');
                            btn.classList.add('btn-primary');
                            btn.disabled = false;
                        }}, 2000);
                    }} else {{
                        throw new Error(data?.message || 'Unknown error');
                    }}
                }})
                .catch(e => {{
                    btn.textContent = '❌ Error';
                    btn.classList.remove('btn-primary');
                    btn.classList.add('btn-danger');
                    setTimeout(() => {{
                        btn.textContent = originalText;
                        btn.classList.remove('btn-danger');
                        btn.classList.add('btn-primary');
                        btn.disabled = false;
                    }}, 3000);
                    console.error('Error:', e);
                }});
            }}
            
            // Auto-refresh every 30 seconds
            setInterval(() => {{
                location.reload();
            }}, 30000);
        </script>
    </body>
    </html>
    """
    return html


# OAuth2 / OIDC Endpoints
@app.get("/api/auth/login", summary="Initiate OAuth2 Login", include_in_schema=False)
async def oauth2_login(admin: str = None):
    """Redirect to OIDC provider for authentication.
    
    Args:
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
        
        # Build authorization URL without PKCE (simplify for now)
        auth_url = (
            f"{auth_endpoint}?"
            f"client_id={settings.OAUTH2_CLIENT_ID}&"
            f"redirect_uri={settings.OAUTH2_REDIRECT_URI}&"
            f"response_type=code&"
            f"scope=openid%20profile%20email&"
            f"state={state}"
        )
        
        logger.info(f"Redirecting to OAuth2 provider: {settings.OAUTH2_PROVIDER_NAME}")
        return RedirectResponse(url=auth_url)
    except Exception as e:
        logger.error(f"OAuth2 login error: {e}")
        return JSONResponse(
            {"error": "Failed to initiate login"},
            status_code=500
        )


@app.get("/api/auth/callback", summary="OAuth2 Callback", include_in_schema=False)
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
        
        # Check if this was an admin login
        redirect_to = "/admin/" if request.query_params.get("admin") else "/scheduler-status"
        
        # Return HTML that stores token in both localStorage and cookie
        html = f"""
        <html>
        <head><title>Login Success</title></head>
        <body>
            <p>Authenticating...</p>
            <script>
                localStorage.setItem('access_token', '{access_token}');
                window.location.href = '{redirect_to}';
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
