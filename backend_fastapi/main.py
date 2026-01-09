"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from contextlib import asynccontextmanager
import logging

from core.config import settings
from core.security import add_cors_middleware, add_trusted_host_middleware
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
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse({"status": "healthy", "version": settings.PROJECT_VERSION})


# Scheduler Status Page
@app.get("/scheduler-status", response_class=HTMLResponse)
async def scheduler_status_page():
    """Display scheduler status page with trigger buttons."""
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
        <div class="container">
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
        
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@4.6.0/dist/js/bootstrap.min.js"></script>
        <script>
            function triggerJob(jobId) {{
                const btn = event.target;
                const originalText = btn.textContent;
                btn.disabled = true;
                btn.textContent = '⏳ Triggering...';
                
                fetch(`/api/tasks/jobs/${{jobId}}/trigger`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}}
                }})
                .then(r => {{
                    if (!r.ok) throw new Error(`HTTP ${{r.status}}`);
                    return r.json();
                }})
                .then(data => {{
                    if (data.success) {{
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
                        throw new Error(data.message);
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



# Include routers
app.include_router(forecasts.router, prefix=settings.API_V1_STR)
app.include_router(price_history.router, prefix=settings.API_V1_STR)
app.include_router(tasks.router)


# Root endpoint
@app.get("/")
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
