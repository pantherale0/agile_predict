"""Custom admin views and utilities for task management."""
from starlette_admin import CustomView
from starlette.requests import Request
from starlette.responses import HTMLResponse
from tasks.scheduler import get_scheduler_status, trigger_job
import logging

logger = logging.getLogger(__name__)


class SchedulerInfoView(CustomView):
    """Custom admin view displaying scheduler information."""
    
    def __init__(self):
        super().__init__(label="Scheduler Status", icon="fa fa-clock", name="scheduler_status")
    
    async def render_page(self, request: Request, response_class=HTMLResponse):
        """Render the scheduler status page."""
        try:
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
                            Trigger Now
                        </button>
                    </td>
                </tr>
                """
            
            scheduler_status = "🟢 Running" if status.get("running") else "🔴 Stopped"
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Scheduler Status</title>
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.6.0/dist/css/bootstrap.min.css">
                <style>
                    body {{ padding: 20px; background: #f5f5f5; }}
                    .container {{ background: white; border-radius: 8px; padding: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                    .status-badge {{ font-size: 1.2em; padding: 10px 20px; border-radius: 5px; }}
                    table {{ margin-top: 20px; }}
                    th {{ background: #343a40; color: white; }}
                    code {{ background: #f8f9fa; padding: 2px 6px; border-radius: 3px; }}
                    .btn-primary {{ background: #007bff; }}
                    .btn-primary:hover {{ background: #0056b3; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>⏰ Scheduler Status</h1>
                    <p>Status: <span class="status-badge">{scheduler_status}</span></p>
                    
                    <h3 style="margin-top: 30px;">📋 Scheduled Jobs</h3>
                    <table class="table table-striped table-hover">
                        <thead class="table-dark">
                            <tr>
                                <th style="width: 150px;">Job ID</th>
                                <th style="width: 200px;">Job Name</th>
                                <th>Trigger</th>
                                <th>Next Run</th>
                                <th style="width: 150px;">Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {jobs_html}
                        </tbody>
                    </table>
                    
                    <hr>
                    <p class="text-muted"><small>💡 Click "Trigger Now" to manually execute a job immediately.</small></p>
                </div>
                
                <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
                <script src="https://cdn.jsdelivr.net/npm/bootstrap@4.6.0/dist/js/bootstrap.min.js"></script>
                <script>
                    function triggerJob(jobId) {{
                        if (!confirm(`Trigger job: ${{jobId}}?`)) return;
                        
                        fetch(`/api/tasks/jobs/${{jobId}}/trigger`, {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}}
                        }})
                        .then(r => {{
                            if (!r.ok) throw new Error(`HTTP ${{r.status}}`);
                            return r.json();
                        }})
                        .then(data => {{
                            const msg = data.success 
                                ? `✅ Success: ${{data.message}}`
                                : `❌ Error: ${{data.message}}`;
                            alert(msg);
                            setTimeout(() => location.reload(), 1000);
                        }})
                        .catch(e => {{
                            alert(`❌ Error: ${{e.message}}`);
                        }});
                    }}
                </script>
            </body>
            </html>
            """
            return response_class(html)
        except Exception as e:
            logger.error(f"Error rendering scheduler status: {e}")
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Error</title>
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.6.0/dist/css/bootstrap.min.css">
            </head>
            <body>
                <div class="container mt-5">
                    <div class="alert alert-danger">
                        <h4>Error Loading Scheduler Status</h4>
                        <p>{str(e)}</p>
                    </div>
                </div>
            </body>
            </html>
            """
            return response_class(error_html)
