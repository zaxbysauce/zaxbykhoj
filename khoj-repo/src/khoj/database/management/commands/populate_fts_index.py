"""Django management command to populate FTS index for existing entries."""

from django.contrib.postgres.search import SearchVector
from django.core.management.base import BaseCommand
from django.db import transaction

from khoj.database.models import Entry


class Command(BaseCommand):
    help = "Populate full-text search (FTS) index for existing entries that have null search_vector"

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Number of entries to process in each batch (default: 1000)",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually perform the updates. Without this flag, only shows what would be processed.",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        apply = options["apply"]

        mode = "APPLY" if apply else "DRY RUN"
        self.stdout.write(f"[{mode}] Populating FTS index for existing entries")

        # Get entries with null search_vector
        entries_to_process = Entry.objects.filter(search_vector__isnull=True)
        total_count = entries_to_process.count()

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS("No entries found with null search_vector. Index is up to date."))
            return

        self.stdout.write(f"Found {total_count} entries to process")

        if not apply:
            self.stdout.write(self.style.WARNING("Use --apply to actually perform the updates"))
            return

        # Process entries in batches using queryset update with SearchVector
        processed_count = 0

        while processed_count < total_count:
            # Get IDs of entries in this batch
            batch_ids = list(
                entries_to_process.values_list("id", flat=True)[processed_count : processed_count + batch_size]
            )

            if not batch_ids:
                break

            # Update batch using queryset update with SearchVector
            # This generates proper SQL: UPDATE ... SET search_vector = to_tsvector('compiled' || ' ' || 'raw')
            with transaction.atomic():
                updated = Entry.objects.filter(id__in=batch_ids).update(
                    search_vector=SearchVector("compiled", "raw")
                )

            processed_count += len(batch_ids)

            # Show progress
            progress_pct = (processed_count / total_count) * 100
            self.stdout.write(
                f"  Progress: {processed_count}/{total_count} ({progress_pct:.1f}%) - "
                f"Updated {updated} entries"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully populated FTS index for {processed_count} entries"
            )
        )
