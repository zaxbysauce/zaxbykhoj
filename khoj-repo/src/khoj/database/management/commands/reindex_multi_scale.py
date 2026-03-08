"""Django management command for multi-scale reindexing of entries."""

from typing import List

from django.core.management.base import BaseCommand
from django.db import transaction

from khoj.database.adapters import EntryAdapters, FileObjectAdapters
from khoj.database.models import Entry, KhojUser
from khoj.processor.content.text_to_entries import TextToEntries
from khoj.utils.rawconfig import Entry as EntryConfig


class Command(BaseCommand):
    help = "Reindex entries with multi-scale chunking (default: 512, 1024, 2048)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--scales",
            type=str,
            default="512,1024,2048",
            help="Comma-separated list of chunk sizes (default: 512,1024,2048)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of files to process per batch (default: 100)",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually perform the reindexing. Without this flag, only shows what would be done.",
        )
        parser.add_argument(
            "--user",
            type=str,
            default=None,
            help="Reindex entries for a specific user (email). If not specified, reindexes for all users.",
        )

    def handle(self, *args, **options):
        # Parse scales argument into List[int]
        scales_str = options["scales"]
        try:
            chunk_sizes = [int(s.strip()) for s in scales_str.split(",")]
        except ValueError:
            self.stderr.write(self.style.ERROR(f"Invalid scales format: {scales_str}"))
            self.stderr.write(self.style.ERROR("Expected comma-separated integers, e.g., '512,1024,2048'"))
            return

        batch_size = options["batch_size"]
        apply = options["apply"]
        user_email = options["user"]
        user = None

        mode = "APPLY" if apply else "DRY RUN"
        self.stdout.write(f"[{mode}] Multi-scale reindexing with chunk sizes: {chunk_sizes}")

        # Get entries to process
        entries_query = Entry.objects.all()

        # Filter by user if specified
        if user_email:
            try:
                user = KhojUser.objects.get(email=user_email)
                entries_query = entries_query.filter(user=user)
                self.stdout.write(f"Filtering by user: {user_email}")
            except KhojUser.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"User not found: {user_email}"))
                return

        # Get unique files that have entries
        file_paths = (
            entries_query.exclude(file_path__isnull=True)
            .exclude(file_path="")
            .values_list("file_path", flat=True)
            .distinct()
        )

        total_files = len(list(file_paths))

        if total_files == 0:
            self.stdout.write(self.style.SUCCESS("No files found to reindex. Nothing to do."))
            return

        self.stdout.write(f"Found {total_files} unique files to process")

        if not apply:
            # In dry-run mode: Show counts
            entries_count = entries_query.count()
            self.stdout.write(f"  - Total entries to reindex: {entries_count}")
            self.stdout.write(f"  - Chunk sizes: {chunk_sizes}")
            self.stdout.write(self.style.WARNING("Use --apply to actually perform the reindexing"))
            return

        # In apply mode: Perform the reindexing
        processed_files = 0
        total_created = 0
        total_deleted = 0

        # Process files in batches
        file_path_list = list(file_paths)

        while processed_files < total_files:
            batch_file_paths = file_path_list[processed_files : processed_files + batch_size]

            if not batch_file_paths:
                break

            try:
                with transaction.atomic():
                    # Process each file in the batch
                    for file_path in batch_file_paths:
                        # Get the user and file_type for this file
                        file_entries = Entry.objects.filter(file_path=file_path)
                        if user_email:
                            file_entries = file_entries.filter(user=user)

                        if not file_entries.exists():
                            continue

                        first_entry = file_entries.first()
                        file_user = first_entry.user
                        file_type = first_entry.file_type
                        file_source = first_entry.file_source

                        # Delete existing entries with the specified scales for this file
                        scale_labels = [str(size) for size in chunk_sizes]
                        deleted_count = file_entries.filter(chunk_scale__in=scale_labels).delete()[0]
                        total_deleted += deleted_count

                        # Get raw text from FileObject
                        file_object = FileObjectAdapters.get_file_object_by_name(file_user, file_path)
                        if not file_object:
                            self.stdout.write(
                                self.style.WARNING(f"  Warning: No FileObject found for {file_path}, skipping")
                            )
                            continue

                        raw_text = file_object.raw_text

                        # Create EntryConfig to process
                        entry_config = EntryConfig(
                            raw=raw_text,
                            file=file_path,
                            compiled=f"{file_path}\n{raw_text}",
                            heading=file_path,
                        )

                        # Split entries with multi-scale chunking
                        chunked_entries = TextToEntries.split_entries_by_max_tokens(
                            [entry_config],
                            chunk_sizes=chunk_sizes,
                            raw_is_compiled=True,
                        )

                        # Prepare entries for bulk creation
                        entries_to_create = []
                        for entry in chunked_entries:
                            entries_to_create.append(
                                Entry(
                                    user=file_user,
                                    raw=entry.raw,
                                    compiled=entry.compiled,
                                    heading=entry.heading[:1000],
                                    file_path=entry.file,
                                    file_source=file_source,
                                    file_type=file_type,
                                    chunk_scale=entry.chunk_scale,
                                    corpus_id=entry.corpus_id,
                                    url=entry.uri if entry.uri and entry.uri.startswith(("http://", "https://")) else None,
                                )
                            )

                        # Bulk create entries (will need embeddings generated separately)
                        if entries_to_create:
                            Entry.objects.bulk_create(entries_to_create)
                            total_created += len(entries_to_create)

                processed_files += len(batch_file_paths)

                # Show progress
                progress_pct = (processed_files / total_files) * 100
                self.stdout.write(
                    f"  Progress: {processed_files}/{total_files} ({progress_pct:.1f}%) - "
                    f"Created {total_created} entries, Deleted {total_deleted} entries"
                )

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error processing batch: {e}"))
                raise

        # Show completion summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\nMulti-scale reindexing complete!\n"
                f"  Files processed: {processed_files}\n"
                f"  Entries created: {total_created}\n"
                f"  Entries deleted: {total_deleted}\n"
                f"  Chunk sizes: {chunk_sizes}"
            )
        )
        self.stdout.write(
            self.style.WARNING(
                "Note: New entries have been created but embeddings have not been generated yet. "
                "Run 'python manage.py generate_embeddings' or wait for background indexing to complete."
            )
        )
