"""Custom login view for starlette-admin with OAuth2 redirect."""
from starlette.responses import HTMLResponse
from core.config import settings


async def admin_login_view() -> HTMLResponse:
    """Custom login page that redirects to OAuth2 provider.
    
    Returns:
        HTML page with redirect to OAuth2 login
    """
    if not settings.OAUTH2_ENABLED:
        return HTMLResponse(
            "<h1>OAuth2 Not Configured</h1><p>Admin access requires OAuth2 to be enabled.</p>",
            status_code=503
        )
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AgilePredictAPI Admin Login</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css">
        <style>
            body {{
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }}
            .login-container {{
                background: white;
                border-radius: 10px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.2);
                padding: 40px;
                width: 100%;
                max-width: 400px;
            }}
            .login-header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .login-header h1 {{
                font-size: 28px;
                color: #333;
                margin-bottom: 10px;
            }}
            .login-header p {{
                color: #666;
                font-size: 14px;
            }}
            .btn-oauth {{
                width: 100%;
                padding: 12px;
                font-size: 16px;
                border-radius: 5px;
                border: none;
                cursor: pointer;
                transition: all 0.3s ease;
            }}
            .btn-oauth:hover {{
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }}
            .loading-spinner {{
                display: none;
                text-align: center;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="login-header">
                <h1>🔐 Admin Panel</h1>
                <p>AgilePredictAPI Administration</p>
            </div>
            
            <button class="btn btn-primary btn-oauth" onclick="redirectToLogin()">
                🔑 Login with {settings.OAUTH2_PROVIDER_NAME.capitalize()}
            </button>
            
            <div class="loading-spinner" id="spinner">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-3">Redirecting to login...</p>
            </div>
            
            <hr style="margin: 20px 0;">
            
            <p style="text-align: center; color: #999; font-size: 12px;">
                This admin area is protected by OAuth2 authentication.<br>
                Only users with admin group membership can access this.
            </p>
        </div>
        
        <script>
            function redirectToLogin() {{
                document.getElementById('spinner').style.display = 'block';
                // Redirect to OAuth2 login with admin flag
                window.location.href = '/api/auth/login?admin=true';
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)
