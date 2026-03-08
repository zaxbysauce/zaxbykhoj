# Generated migration to add chunk_scale field to Entry model
#
# REVERSIBILITY:
# This migration is explicitly reversible. When reversed:
#   - RemoveField: Removes the 'chunk_scale' field from Entry model
#
# Reverse command: python manage.py migrate database 0101

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("database", "0101_add_context_summary"),
    ]

    operations = [
        # FORWARD: Add chunk_scale field for multi-scale chunking support
        # REVERSE: RemoveField operation is automatically generated
        migrations.AddField(
            model_name="entry",
            name="chunk_scale",
            field=models.CharField(
                max_length=16,
                default="default",
                blank=True,
                null=True,
                help_text="Chunk size scale identifier (e.g., '512', '1024', '2048', 'default')",
            ),
        ),
    ]

    reversible = True
