"""
Celery Application Configuration

This module configures Celery for distributed task queue processing.
It handles job execution, worker management, and task routing.
"""

import os
import ssl
from urllib.parse import urlparse
from backend.env_loader import load_environment
from celery import Celery
from celery.signals import worker_ready
from kombu import Queue, Exchange
from backend.logging_config import get_logger, configure_logging

# Load environment variables
load_environment()

# Configure logging for Celery worker
configure_logging(log_level="INFO")
logger = get_logger(__name__)

# Check if running in sync mode (no Redis/Celery required)
SYNC_MODE = os.getenv("SYNC_MODE", "false").lower() in ("true", "1", "yes")

# Get Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def _mask_redis_url(url: str) -> str:
    """Return the Redis URL with the password replaced by ***."""
    parsed = urlparse(url)
    if parsed.password:
        host = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port else ""
        return f"{parsed.scheme}://{parsed.username}:***@{host}{port}"
    return url

# In sync mode, we don't need Redis/Celery
if SYNC_MODE:
    print("⚠️  SYNC MODE ENABLED - Running without Celery/Redis", flush=True)
    logger.info("⚠️  SYNC MODE ENABLED - Running without Celery/Redis")
    app = None  # Celery app will be None in sync mode
else:
    # Validate Redis URL exists (critical for Railway)
    if not REDIS_URL:
        raise ValueError(
            "❌ CRITICAL: REDIS_URL environment variable is not set!\n"
            "   Options:\n"
            "   1. Set REDIS_URL to a Redis connection string (e.g., redis://localhost:6379/0)\n"
            "   2. Set SYNC_MODE=true to run without Redis (tasks run synchronously in-process)\n"
            "   3. Use a free cloud Redis service (Upstash, Redis Cloud, Railway)"
        )

    # Log startup message with Redis URL (masked)
    print(f"🚀 CELERY APP MODULE LOADED", flush=True)
    print(f"📡 Broker URL: {_mask_redis_url(REDIS_URL)}", flush=True)
    logger.info("🚀 CELERY APP MODULE LOADED")
    logger.info(f"Broker URL: {_mask_redis_url(REDIS_URL)}")

    # Initialize Celery app
    # Note: result_backend=None because we store results in database, not Redis
    app = Celery(
        "scholar_source",
        broker=REDIS_URL,
        backend=None,  # Results stored in database, not Redis
        include=["backend.tasks"]  # Module where tasks are defined
    )

# Celery Configuration (only if not in sync mode)
if app is not None:
    app.conf.update(
    # Broker connection settings (CRITICAL for Railway)
    broker_connection_retry_on_startup=True,  # Retry on startup
    broker_connection_retry=True,  # Retry on connection loss
    broker_connection_max_retries=5,  # Max retries before giving up
    broker_pool_limit=3,  # Connection pool size

    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Result backend settings
    # result_backend=None - Results stored in database, not Redis
    # This saves Redis memory since we don't retrieve results from Celery

    # Task execution settings
    task_track_started=True,  # Track when tasks start
    task_time_limit=1800,  # Hard time limit: 30 min (kills task)
    task_soft_time_limit=1500,  # Soft time limit: 25 minutes (raises exception)
    task_acks_late=True,  # Acknowledge task after completion (important for reliability)
    task_reject_on_worker_lost=True,  # Reject task if worker dies

    # Worker settings
    worker_prefetch_multiplier=1,  # Only fetch one task at a time (important for long-running tasks)
    worker_max_tasks_per_child=50,  # Restart worker after 100 tasks (prevents memory leaks)
    worker_disable_rate_limits=False,
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",

    # Retry settings (default for all tasks, can be overridden per task)
    task_default_retry_delay=60,  # Wait 60 seconds before retrying
    task_max_retries=3,  # Maximum 3 retries

    # Task routing
    task_routes={
        "backend.tasks.run_crew_task": {
            "queue": "crew_jobs",
            "routing_key": "crew.jobs",
        },
    },

    # Queue definitions
    task_queues=(
        Queue(
            "crew_jobs",
            Exchange("crew", type="direct"),
            routing_key="crew.jobs",
            queue_arguments={"x-max-priority": 10},  # Enable priority queue
        ),
        Queue(
            "default",
            Exchange("default", type="direct"),
            routing_key="default",
        ),
    ),

    # Task priority settings
    task_default_priority=5,  # Default priority (0-10, higher is more important)

    # Monitoring
    worker_send_task_events=True,  # Send task events for monitoring
    task_send_sent_event=True,
    
    # Error handling
    task_ignore_result=True,  # Don't store results in Redis - we use database instead
    task_store_errors_even_if_ignored=True,  # Still store errors for debugging

    # Security (in production, consider message signing)
    # task_serializer='json' already set above

    # Beat schedule (for periodic tasks - optional for now)
    beat_schedule={
        # Example: Clean up old results every hour
        # "cleanup-old-results": {
        #     "task": "backend.tasks.cleanup_old_results",
        #     "schedule": 3600.0,  # Every hour
        # },
    },
    )

# app.conf.update(
#     broker_use_ssl={
#         'ssl_cert_reqs': ssl.CERT_NONE  # Railway's Redis uses self-signed certs
#     },
#     redis_backend_use_ssl={
#         'ssl_cert_reqs': ssl.CERT_NONE
#     }
# )

# Task error handler (only if Celery is available)
if app is not None:
    @app.task(bind=True)
    def error_handler(self, uuid):
        """
        Error handler for failed tasks.
        This will be called when a task fails after all retries.
        """
        from backend.logging_config import get_logger
        logger = get_logger(__name__)

        result = self.app.AsyncResult(uuid)
        logger.error(
            f"Task {uuid} failed: {result.result}",
            exc_info=result.traceback
        )

    # Configure task base class for automatic retry on common exceptions
    class BaseTask(app.Task):
        """
        Base task class with automatic retry logic for common exceptions.
        """
        autoretry_for = (
            Exception,  # Retry on any exception (can be more specific)
        )
        retry_kwargs = {
            "max_retries": 3,
            "countdown": 60,  # Wait 60 seconds before retry
        }
        retry_backoff = True  # Exponential backoff
        retry_backoff_max = 600  # Max 10 minutes backoff
        retry_jitter = True  # Add random jitter to backoff

    # Update default task class
    app.Task = BaseTask

    # Signal handler for when worker is ready
    @worker_ready.connect
    def on_worker_ready(sender, **kwargs):
        """Called when the Celery worker is ready to accept tasks."""
        # Log a single concise message instead of multiple lines
        # This reduces log noise in Railway
        worker_name = getattr(sender, 'hostname', str(sender))
        logger.info(f"🚀 Celery worker ready: {worker_name} (Redis: {_mask_redis_url(REDIS_URL)})")


if __name__ == "__main__":
    # For testing: Start a worker with
    # celery -A backend.celery_app worker --loglevel=info
    if app is not None:
        app.start()
    else:
        print("⚠️  Cannot start Celery worker in SYNC_MODE. Set SYNC_MODE=false and provide REDIS_URL.")
