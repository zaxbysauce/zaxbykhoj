# Generated to make Entry.embeddings nullable for RAG Enhancement

from django.db import migrations
import pgvector.django


class Migration(migrations.Migration):
    dependencies = [
        ("database", "0106_add_ldap_dn"),
    ]

    operations = [
        migrations.AlterField(
            model_name="entry",
            name="embeddings",
            field=pgvector.django.VectorField(
                dimensions=None,
                null=True,
                blank=True,
                help_text="Vector embeddings for semantic search",
            ),
        ),
    ]
