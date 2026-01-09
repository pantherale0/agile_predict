"""Scheduler configuration for background tasks."""
from apscheduler.schedulers.background import BackgroundScheduler
from core.config import settings
import logging

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def start_scheduler():
    """Start the background scheduler."""
    if not scheduler.running:
        # Configure all scheduled jobs
        from tasks.background_jobs import configure_scheduled_jobs
        configure_scheduled_jobs(scheduler)
        
        scheduler.start()
        logger.info("Scheduler started with all jobs configured")


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")


def get_scheduler_status():
    """Get the current status of the scheduler.
    
    Returns:
        dict: Scheduler status information
    """
    from tasks.background_jobs import job_status
    
    jobs = []
    if scheduler.running:
        for job in scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "trigger": str(job.trigger),
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            })
    
    return {
        "running": scheduler.running,
        "jobs": jobs,
        "job_status": job_status,
    }


def trigger_job(job_id: str):
    """Manually trigger a scheduled job.
    
    Args:
        job_id: The ID of the job to trigger
        
    Returns:
        dict: Result of the trigger operation
    """
    try:
        job = scheduler.get_job(job_id)
        if not job:
            return {"success": False, "message": f"Job '{job_id}' not found"}
        
        # Execute the job function directly
        job.func()
        return {"success": True, "message": f"Job '{job_id}' triggered successfully"}
    except Exception as e:
        return {"success": False, "message": f"Error triggering job: {str(e)}"}
