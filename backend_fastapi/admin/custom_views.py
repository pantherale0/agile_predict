"""Custom admin views and utilities for task management."""
from starlette_admin import CustomView
from starlette.requests import Request
from starlette.responses import Response
from starlette.templating import Jinja2Templates
from tasks.scheduler import get_scheduler_status
import logging

logger = logging.getLogger(__name__)


class SchedulerInfoView(CustomView):
    """Custom admin view displaying scheduler information."""

    def __init__(self):
        super().__init__(label="Scheduler Status", icon="fa fa-clock", path="/scheduler")
    
    async def render(self, request: Request, templates: Jinja2Templates) -> Response:
        """Render the scheduler status page."""
        try:
            status = get_scheduler_status()
            return templates.TemplateResponse(
                request,
                name="scheduler_status.html",
                context={
                    "jobs": status.get("jobs", []),
                    "running": status.get("running", False),
                },
            )
        except Exception as e:
            logger.exception("Error rendering scheduler status")
            return templates.TemplateResponse(
                request,
                name="scheduler_error.html",
                context={
                    "error": str(e),
                },
            )
