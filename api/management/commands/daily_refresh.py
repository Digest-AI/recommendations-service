from django.core.management.base import BaseCommand

from api.jobs import daily_refresh


class Command(BaseCommand):
    help = "Run the daily parser fetch + recommendation refresh once."

    def handle(self, *args, **options):
        stats = daily_refresh()
        self.stdout.write(self.style.SUCCESS(f"Done: {stats}"))
