from django.core.management.base import BaseCommand

from api.jobs import notify_telegram_bot


class Command(BaseCommand):
    help = "Push today's new recommendations to the Telegram bot service."

    def handle(self, *args, **options):
        stats = notify_telegram_bot()
        self.stdout.write(self.style.SUCCESS(f"Done: {stats}"))
