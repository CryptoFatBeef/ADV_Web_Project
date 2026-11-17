"""
apps/accounts/management/commands/seed_test_users.py

Load test_credentials.csv into the dev DB. Idempotent (update_or_create).
Hard-guarded against prod: raises CommandError if DEBUG is False.

Usage:
    python manage.py seed_test_users --settings=config.settings.dev
    python manage.py seed_test_users --purge --settings=config.settings.dev
"""
import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User

CREDENTIALS_CSV = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "verification" / "fixtures" / "test_credentials.csv"
)


class Command(BaseCommand):
    help = "Seed 7 test users (one per role) from verification/fixtures/test_credentials.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "--purge",
            action="store_true",
            help="Delete all test_* users before seeding (clean-slate option)",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "seed_test_users must only run in DEBUG mode. "
                "Never load test credentials into a production database."
            )

        if not CREDENTIALS_CSV.exists():
            raise CommandError(
                f"Credentials CSV not found: {CREDENTIALS_CSV}\n"
                "Run: python -m verification.scraper.generate_credentials"
            )

        if options["purge"]:
            deleted, _ = User.objects.filter(username__startswith="test_").delete()
            self.stdout.write(f"Purged {deleted} test_* user(s).")

        with open(CREDENTIALS_CSV, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        created_count = 0
        updated_count = 0
        for row in rows:
            user, created = User.objects.update_or_create(
                username=row["username"],
                defaults={
                    "email":     row["email"],
                    "role":      row["role"],
                    "is_active": row["is_active"].upper() == "TRUE",
                },
            )
            user.set_password(row["password"])
            user.save(update_fields=["password"])
            if created:
                created_count += 1
                self.stdout.write(f"  Created  {row['username']} ({row['role']})")
            else:
                updated_count += 1
                self.stdout.write(f"  Updated  {row['username']} ({row['role']})")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone: {created_count} created, {updated_count} updated."
            )
        )
