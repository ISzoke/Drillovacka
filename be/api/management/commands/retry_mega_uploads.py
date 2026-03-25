"""
Management command: retry MEGA uploads for attempts that previously failed.
Usage:
    python manage.py retry_mega_uploads
    python manage.py retry_mega_uploads --limit 200
    python manage.py retry_mega_uploads --source speech
    python manage.py retry_mega_uploads --source text
"""
from django.core.management.base import BaseCommand
from api.models import ExampleAttempt
from api.attempt_cloud_sync import sync_attempt_to_mega, sync_write_attempt_to_mega


class Command(BaseCommand):
    help = "Retry MEGA uploads for attempts that previously failed or were never uploaded."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=500)
        parser.add_argument("--source", choices=["speech", "text", "all"], default="all")

    def handle(self, *args, **options):
        limit = options["limit"]
        source = options["source"]

        sources = ["speech", "text"] if source == "all" else [source]

        total_processed = 0
        total_uploaded = 0
        total_skipped = 0

        for src in sources:
            self.stdout.write(f"--- source: {src} ---")

            if src == "speech":
                candidates = ExampleAttempt.objects.filter(
                    source="speech",
                    audio_file_path__isnull=False,
                ).exclude(audio_file_path="").order_by("-created_at")[:limit]

                def needs_upload(a):
                    m = a.meta or {}
                    return not (m.get("mega_uploaded") and m.get("mega_json_uploaded"))

                sync_fn = sync_attempt_to_mega

            else:
                candidates = ExampleAttempt.objects.filter(
                    source="text",
                ).order_by("-created_at")[:limit]

                def needs_upload(a):
                    m = a.meta or {}
                    return not m.get("mega_json_uploaded")

                sync_fn = sync_write_attempt_to_mega

            for attempt in candidates:
                if not needs_upload(attempt):
                    total_skipped += 1
                    continue

                result = sync_fn(attempt)
                total_processed += 1

                if result.get("uploaded"):
                    total_uploaded += 1
                    self.stdout.write(f"  [OK]  attempt {attempt.id}")
                else:
                    reason = result.get("audio_error") or result.get("json_error") or result.get("reason", "?")
                    self.stdout.write(f"  [ERR] attempt {attempt.id}: {reason}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. processed={total_processed}, uploaded={total_uploaded}, skipped(already done)={total_skipped}"
            )
        )
