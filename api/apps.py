import logging
import os
import sys

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"
    verbose_name = "API"

    def ready(self) -> None:
        if not getattr(settings, "RUN_SCHEDULER", False):
            return
        if not _running_under_server():
            return

        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        from django_apscheduler.jobstores import DjangoJobStore

        from api.jobs import daily_refresh

        scheduler = BackgroundScheduler(timezone="UTC")
        scheduler.add_jobstore(DjangoJobStore(), "default")
        scheduler.add_job(
            daily_refresh,
            trigger=CronTrigger(
                hour=settings.DAILY_REFRESH_HOUR,
                minute=settings.DAILY_REFRESH_MINUTE,
            ),
            id="daily_refresh",
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=3600,
        )
        scheduler.start()
        logger.info(
            "APScheduler started (daily_refresh at %02d:%02d UTC)",
            settings.DAILY_REFRESH_HOUR,
            settings.DAILY_REFRESH_MINUTE,
        )


def _running_under_server() -> bool:
    """Skip scheduler during management commands (migrate, makemigrations, test, ...)."""
    argv0 = os.path.basename(sys.argv[0]) if sys.argv else ""
    if "gunicorn" in argv0 or "uwsgi" in argv0:
        return True
    if len(sys.argv) >= 2 and sys.argv[1] == "runserver":
        return os.environ.get("RUN_MAIN") == "true"
    return False
