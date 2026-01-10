"""Security and middleware configuration."""
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi import FastAPI
from core.config import settings


class ProxyHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to handle X-Forwarded-* headers from reverse proxies."""
    
    async def dispatch(self, request: Request, call_next):
        """Process proxy headers to get real client IP, protocol, and host.
        
        Handles:
        - X-Forwarded-For: Client's real IP
        - X-Forwarded-Proto: Original protocol (http/https)
        - X-Forwarded-Host: Original host (with optional port)
        - X-Forwarded-Port: Original port
        """
        # Get the real client IP from X-Forwarded-For header
        # Format is usually: client_ip, proxy_ip1, proxy_ip2
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            # Take the first IP (the original client)
            client_ip = x_forwarded_for.split(",")[0].strip()
            # Store in scope for access in handlers
            request.scope["client"] = (client_ip, request.scope.get("client", ("", 0))[1])
        
        # Get real protocol from X-Forwarded-Proto
        x_forwarded_proto = request.headers.get("x-forwarded-proto")
        if x_forwarded_proto:
            request.scope["scheme"] = x_forwarded_proto
        
        # Get real host from X-Forwarded-Host (may include port)
        x_forwarded_host = request.headers.get("x-forwarded-host")
        if x_forwarded_host:
            # X-Forwarded-Host can be "example.com" or "example.com:8080"
            request.scope["server"] = (x_forwarded_host.split(":")[0], 80)  # Update host
        
        # Alternative: use X-Forwarded-Port if available
        x_forwarded_port = request.headers.get("x-forwarded-port")
        if x_forwarded_port and request.scope.get("server"):
            try:
                port = int(x_forwarded_port)
                host = request.scope["server"][0]
                request.scope["server"] = (host, port)
            except (ValueError, TypeError):
                pass
        
        response = await call_next(request)
        return response



def add_cors_middleware(app: FastAPI) -> None:
    """Add CORS middleware to FastAPI app."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_CREDENTIALS,
        allow_methods=settings.CORS_METHODS,
        allow_headers=settings.CORS_HEADERS,
    )


def add_trusted_host_middleware(app: FastAPI) -> None:
    """Add trusted host middleware to FastAPI app."""
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )


def add_proxy_headers_middleware(app: FastAPI) -> None:
    """Add proxy headers middleware to handle X-Forwarded-* headers.
    
    This should be added after other middleware so it processes headers first.
    """
    app.add_middleware(ProxyHeadersMiddleware)
