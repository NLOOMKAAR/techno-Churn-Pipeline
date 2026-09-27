"""
scheduler.py
------------
Sub-Objective 1, Activity 1.5 - DataOps scheduling requirement:
  "Schedule these workflows to run every 2 minutes, logging all activity
  details and displaying them on a Cloud dashboard."

Uses APScheduler's BackgroundScheduler with an interval trigger of
2 minutes. In a cloud deployment this process runs as a long-lived
background worker (e.g. a Cloud Run service with min-instances=1, an
Azure WebJob, an AWS ECS/Fargate task, or a systemd service on a VM)
alongside the FastAPI app defined in api/main.py, which reads the same
logs/run_history.json file to serve pipeline status over HTTP.
"""
import time
import logging
from apscheduler.schedulers.background import BackgroundScheduler

from pipeline import run_pipeline_once, logger

logging.getLogger("apscheduler").setLevel(logging.WARNING)


def start_scheduler(run_immediately: bool = True):
    """Start the APScheduler interval job.

    NOTE: passing next_run_time=None to add_job() does NOT mean "next run =
    now + interval" - it actually leaves the job PAUSED indefinitely. That
    was a bug in an earlier version of this file (the job never fired on
    its own interval). The fix: let add_job() compute the natural next
    run time (now + interval) by simply not overriding next_run_time.
    """
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        run_pipeline_once,
        trigger="interval",
        minutes=2,
        id="dataops_pipeline_job",
        coalesce=True,
        misfire_grace_time=60,
    )
    scheduler.start()
    job = scheduler.get_job("dataops_pipeline_job")
    logger.info(
        f"Scheduler STARTED: dataops_pipeline_job will run every 2 minutes "
        f"(next fire at {job.next_run_time.isoformat()})"
    )
    if run_immediately:
        # Fire one run right away too, purely so evidence/logs exist immediately
        # without waiting 2 minutes for the very first data point.
        run_pipeline_once()
    return scheduler


if __name__ == "__main__":
    sched = start_scheduler(run_immediately=True)
    try:
        while True:
            time.sleep(5)
    except (KeyboardInterrupt, SystemExit):
        sched.shutdown()
