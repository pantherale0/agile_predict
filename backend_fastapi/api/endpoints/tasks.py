"""Task management endpoints for background jobs."""
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import List, Optional
import logging

from tasks.scheduler import get_scheduler_status, trigger_job
from core.auth import User
from api.deps import get_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])



class JobInfo(BaseModel):
    """Information about a scheduled job."""
    id: str
    name: str
    trigger: str
    next_run_time: Optional[str] = None


class SchedulerStatus(BaseModel):
    """Status of the background scheduler."""
    running: bool
    jobs: List[JobInfo]
    job_status: dict


class JobTriggerResult(BaseModel):
    """Result of triggering a job."""
    success: bool
    message: str


@router.get("/scheduler/status", response_model=SchedulerStatus, summary="Get Scheduler Status", include_in_schema=False)
def get_scheduler_status_endpoint(current_user: User = Depends(get_admin_user)):
    """Get the current status of the background scheduler.
    
    **Requires OAuth2 authentication**
    
    Returns:
        SchedulerStatus: Current scheduler status and job information
    """
    logger.info(f"Scheduler status accessed by user: {current_user.username}")
    return get_scheduler_status()


@router.post("/jobs/{job_id}/trigger", response_model=JobTriggerResult, summary="Trigger Job", include_in_schema=False)
def trigger_job_endpoint(job_id: str, current_user: User = Depends(get_admin_user)):
    """Manually trigger a background job.
    
    **Requires OAuth2 authentication**
    
    Args:
        job_id: The ID of the job to trigger (e.g., 'update_latest_agile')
        current_user: The authenticated user
        
    Returns:
        JobTriggerResult: Result of the trigger operation
        
    Example job IDs:
        - update_latest_agile: Update latest Agile prices
        - update_forecasts: Update forecasts
        - update_national_agile: Update national Agile data
        - clean_forecasts: Clean old forecasts
        - sync_local: Sync local data
    """
    logger.info(f"Job {job_id} triggered by user: {current_user.username}")
    result = trigger_job(job_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.get("/jobs", summary="List All Jobs", include_in_schema=False)
def list_jobs(current_user: User = Depends(get_admin_user)):
    """Get a list of all scheduled jobs with their details.
    
    **Requires OAuth2 authentication**
    
    Args:
        current_user: The authenticated user
    
    Returns:
        dict: Scheduler status with jobs list
    """
    logger.info(f"Jobs list accessed by user: {current_user.username}")
    status = get_scheduler_status()
    return {
        "total_jobs": len(status["jobs"]),
        "jobs": status["jobs"],
        "last_status": status["job_status"],
    }


@router.get("/jobs/{job_id}/details", summary="Get Job Details", include_in_schema=False)
def get_job_details(job_id: str, current_user: User = Depends(get_admin_user)):
    """Get detailed information about a specific job.
    
    **Requires OAuth2 authentication**
    
    Args:
        job_id: The ID of the job
        current_user: The authenticated user
        
    Returns:
        dict: Job details and last execution status
    """
    logger.info(f"Job details for {job_id} accessed by user: {current_user.username}")
    status = get_scheduler_status()
    job = next((j for j in status["jobs"] if j["id"] == job_id), None)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    
    # Add last execution status
    job_status = status["job_status"]
    last_error = None
    last_run = None
    
    if "last_" + job_id in job_status:
        last_run = job_status["last_" + job_id]
        last_error = job_status.get("last_" + job_id + "_error")
    
    return {
        **job,
        "last_run": last_run,
        "last_error": last_error,
    }


@router.get("/status/summary", summary="Get Job Status Summary", include_in_schema=False)
def get_status_summary(current_user: User = Depends(get_admin_user)):
    """Get a summary of all job execution statuses.
    
    **Requires OAuth2 authentication**
    
    Args:
        current_user: The authenticated user
    
    Returns:
        dict: Summary of last execution times and errors for all jobs
    """
    logger.info(f"Status summary accessed by user: {current_user.username}")
    status = get_scheduler_status()
    job_status = status["job_status"]
    
    summary = {
        "scheduler_running": status["running"],
        "total_jobs": len(status["jobs"]),
        "job_execution_status": {}
    }
    
    jobs_by_id = {j["id"]: j["name"] for j in status["jobs"]}
    
    for job_id in jobs_by_id:
        last_run = job_status.get(f"last_{job_id}")
        last_error = job_status.get(f"last_{job_id}_error")
        
        summary["job_execution_status"][job_id] = {
            "name": jobs_by_id[job_id],
            "last_run": last_run,
            "status": "error" if last_error else "ok" if last_run else "never_run",
            "last_error": last_error,
        }
    
    return summary
