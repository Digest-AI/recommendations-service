import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings
from django.core.management.base import BaseCommand
from django_apscheduler.jobstores import DjangoJobStore

from api.jobs import daily_refresh, notify_telegram_bot

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the APScheduler in the foreground (e.g. as a worker process)."

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone="UTC")
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
        scheduler.add_job(
            notify_telegram_bot,
            trigger=CronTrigger(
                hour=settings.TG_NOTIFY_HOUR,
                minute=settings.TG_NOTIFY_MINUTE,
            ),
            id="notify_telegram_bot",
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=3600,
        )

        self.stdout.write(
            f"Scheduler started: "
            f"daily_refresh @ {settings.DAILY_REFRESH_HOUR:02d}:{settings.DAILY_REFRESH_MINUTE:02d} UTC, "
            f"notify_telegram_bot @ {settings.TG_NOTIFY_HOUR:02d}:{settings.TG_NOTIFY_MINUTE:02d} UTC"
        )
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()
