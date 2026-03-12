# Add bind_dn and encrypted bind_password fields to LdapConfig so that
# service-account credentials entered via the admin settings page are
# persisted across server restarts.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("database", "0107_alter_entry_embeddings"),
    ]

    operations = [
        migrations.AddField(
            model_name="ldapconfig",
            name="bind_dn",
            field=models.CharField(
                blank=True,
                default=None,
                help_text="Service account DN used to bind and search LDAP (e.g., CN=svc-khoj,DC=corp,DC=com)",
                max_length=500,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="ldapconfig",
            name="bind_password_enc",
            field=models.TextField(
                blank=True,
                default=None,
                help_text="Fernet-encrypted LDAP service account password",
                null=True,
            ),
        ),
    ]
