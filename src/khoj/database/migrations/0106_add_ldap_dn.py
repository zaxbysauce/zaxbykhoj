# Generated for LDAP Authentication - Add ldap_dn field to KhojUser

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("database", "0105_add_hybrid_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="khojuser",
            name="ldap_dn",
            field=models.CharField(
                max_length=255,
                null=True,
                blank=True,
                default=None,
                help_text="LDAP Distinguished Name for users authenticated via LDAP",
            ),
        ),
    ]
