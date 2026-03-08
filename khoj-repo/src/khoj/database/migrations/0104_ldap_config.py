# Generated manually for LDAP authentication enhancement

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("database", "0102_add_chunk_scale"),
    ]

    operations = [
        migrations.CreateModel(
            name="LdapConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("server_url", models.CharField(help_text="LDAP server URL (e.g., ldaps://ldap.example.com:636)", max_length=200)),
                ("user_search_base", models.CharField(help_text="Base DN for user searches (e.g., OU=Users,DC=example,DC=com)", max_length=200)),
                ("user_search_filter", models.CharField(default="(sAMAccountName={username})", help_text="LDAP filter template for finding users", max_length=200)),
                ("use_tls", models.BooleanField(default=True, help_text="Use TLS/SSL for LDAP connections")),
                ("tls_verify", models.BooleanField(default=True, help_text="Verify TLS certificates")),
                ("tls_ca_bundle_path", models.CharField(blank=True, default=None, help_text="Path to custom CA bundle for TLS verification (optional)", max_length=500, null=True)),
                ("enabled", models.BooleanField(default=False, help_text="Enable LDAP authentication")),
            ],
            options={
                "verbose_name": "LDAP Configuration",
                "verbose_name_plural": "LDAP Configurations",
            },
        ),
    ]
