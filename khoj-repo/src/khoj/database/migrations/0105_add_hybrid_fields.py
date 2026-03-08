# Generated for RAG Enhancement - Add hybrid search fields to SearchModelConfig

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("database", "0104_ldap_config"),
    ]

    operations = [
        migrations.AddField(
            model_name="searchmodelconfig",
            name="hybrid_alpha",
            field=models.FloatField(default=0.6, help_text="Weight for hybrid search (0.0 = all sparse, 1.0 = all dense)"),
        ),
        migrations.AddField(
            model_name="searchmodelconfig",
            name="hybrid_enabled",
            field=models.BooleanField(default=True, help_text="Enable hybrid search (dense + sparse)"),
        ),
    ]
