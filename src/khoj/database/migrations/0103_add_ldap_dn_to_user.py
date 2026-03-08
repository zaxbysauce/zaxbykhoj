# Generated manually for LDAP authentication enhancement

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("database", "0102_add_chunk_scale"),
    ]

    operations = [
        migrations.AddField(
            model_name="khojuser",
            name="ldap_dn",
            field=models.CharField(
                max_length=200,
                null=True,
                blank=True,
                default=None,
                help_text="LDAP Distinguished Name for users authenticated via LDAP",
            ),
        ),
    ]
