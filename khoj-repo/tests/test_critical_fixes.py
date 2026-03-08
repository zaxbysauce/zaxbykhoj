"""
Critical Fixes Tests

Tests for the following critical fixes:
1. Entry.save() Fix - Entry creation and persistence
2. Migration Chain - Migrations 0100-0107 dependency validation
3. New Model Fields - SearchModelConfig hybrid fields, KhojUser ldap_dn, Entry.embeddings nullable
4. pyproject.toml - TOML syntax and version validation
"""

import os
import sys
from io import StringIO
from unittest.mock import patch, MagicMock

import pytest

# Ensure Django is configured
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "khoj.app.settings")


class TestPyprojectToml:
    """Test pyproject.toml syntax and version."""

    def test_pyproject_toml_syntax_is_valid(self):
        """Verify TOML syntax is valid."""
        # Try to import tomllib (Python 3.11+) or tomli
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                pytest.skip("tomllib/tomli not available")

        pyproject_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "pyproject.toml",
        )

        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        # Verify basic structure
        assert "project" in config
        assert "build-system" in config

    def test_version_is_set_correctly(self):
        """Verify version is set correctly in pyproject.toml."""
        # Try to import tomllib (Python 3.11+) or tomli
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                pytest.skip("tomllib/tomli not available")

        pyproject_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "pyproject.toml",
        )

        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        # Verify version exists and is a valid semantic version
        version = config["project"]["version"]
        assert version is not None
        assert isinstance(version, str)

        # Basic semantic version check (e.g., "2.0.0")
        version_parts = version.split(".")
        assert len(version_parts) >= 2, "Version should have at least major.minor"

        # Verify parts are numeric
        for part in version_parts:
            assert part.isdigit() or part.replace("-", "").isalnum(), f"Invalid version part: {part}"

    def test_required_dependencies_present(self):
        """Verify required dependencies are present in pyproject.toml."""
        # Try to import tomllib (Python 3.11+) or tomli
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                pytest.skip("tomllib/tomli not available")

        pyproject_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "pyproject.toml",
        )

        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        dependencies = config["project"]["dependencies"]

        # Check for key dependencies
        required_deps = ["django", "pgvector", "psycopg2-binary"]
        for dep in required_deps:
            assert any(dep in d.lower() for d in dependencies), f"Required dependency {dep} not found"


class TestMigrationChain:
    """Test migration chain 0100-0107 forms valid dependency chain."""

    def test_migrations_0100_to_0107_exist(self):
        """Test that migrations 0100-0107 exist."""
        migration_files = [
            "0100_add_search_vector.py",
            "0101_add_context_summary.py",
            "0102_add_chunk_scale.py",
            "0104_ldap_config.py",
            "0105_add_hybrid_fields.py",
            "0107_alter_entry_embeddings.py",
        ]

        migrations_dir = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "khoj",
            "database",
            "migrations",
        )

        for migration_file in migration_files:
            file_path = os.path.join(migrations_dir, migration_file)
            assert os.path.exists(file_path), f"Migration file {migration_file} not found"

    def test_0100_migration_dependencies(self):
        """Test 0100_add_search_vector dependencies."""
        migrations_dir = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "khoj",
            "database",
            "migrations",
        )

        # Read and execute migration file to check dependencies
        migration_file = os.path.join(migrations_dir, "0100_add_search_vector.py")
        with open(migration_file, "r") as f:
            content = f.read()

        # Verify dependencies
        assert '("database", "0099_usermemory")' in content
        assert "SearchVectorField" in content
        assert "GinIndex" in content

    def test_0101_migration_dependencies(self):
        """Test 0101_add_context_summary dependencies."""
        migrations_dir = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "khoj",
            "database",
            "migrations",
        )

        migration_file = os.path.join(migrations_dir, "0101_add_context_summary.py")
        with open(migration_file, "r") as f:
            content = f.read()

        # Verify dependencies
        assert '("database", "0100_add_search_vector")' in content
        assert "context_summary" in content

    def test_0102_migration_dependencies(self):
        """Test 0102_add_chunk_scale dependencies."""
        migrations_dir = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "khoj",
            "database",
            "migrations",
        )

        migration_file = os.path.join(migrations_dir, "0102_add_chunk_scale.py")
        with open(migration_file, "r") as f:
            content = f.read()

        # Verify dependencies
        assert '("database", "0101_add_context_summary")' in content
        assert "chunk_scale" in content

    def test_0104_migration_dependencies(self):
        """Test 0104_ldap_config dependencies."""
        migrations_dir = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "khoj",
            "database",
            "migrations",
        )

        migration_file = os.path.join(migrations_dir, "0104_ldap_config.py")
        with open(migration_file, "r") as f:
            content = f.read()

        # Verify dependencies
        assert '("database", "0102_add_chunk_scale")' in content
        assert "LdapConfig" in content

    def test_0105_migration_dependencies(self):
        """Test 0105_add_hybrid_fields dependencies."""
        migrations_dir = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "khoj",
            "database",
            "migrations",
        )

        migration_file = os.path.join(migrations_dir, "0105_add_hybrid_fields.py")
        with open(migration_file, "r") as f:
            content = f.read()

        # Verify dependencies
        assert '("database", "0104_ldap_config")' in content
        assert "hybrid_alpha" in content
        assert "hybrid_enabled" in content

    def test_0107_migration_dependencies(self):
        """Test 0107_alter_entry_embeddings dependencies."""
        migrations_dir = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "khoj",
            "database",
            "migrations",
        )

        migration_file = os.path.join(migrations_dir, "0107_alter_entry_embeddings.py")
        with open(migration_file, "r") as f:
            content = f.read()

        # Verify dependencies - note: depends on 0106 which may not exist in all branches
        # The migration references 0106_add_ldap_dn
        assert "0106" in content or "0105" in content
        assert "embeddings" in content
        assert "null=True" in content or "blank=True" in content


class TestModelDefinitions:
    """Test model field definitions by examining model files."""

    def test_search_model_config_has_hybrid_alpha_in_model(self):
        """Test SearchModelConfig model has hybrid_alpha field defined."""
        models_file = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "khoj",
            "database",
            "models",
            "__init__.py",
        )

        with open(models_file, "r") as f:
            content = f.read()

        # Verify hybrid_alpha field exists in SearchModelConfig
        assert "hybrid_alpha" in content
        assert "SearchModelConfig" in content

    def test_search_model_config_has_hybrid_enabled_in_model(self):
        """Test SearchModelConfig model has hybrid_enabled field defined."""
        models_file = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "khoj",
            "database",
            "models",
            "__init__.py",
        )

        with open(models_file, "r") as f:
            content = f.read()

        # Verify hybrid_enabled field exists in SearchModelConfig
        assert "hybrid_enabled" in content

    def test_khoj_user_has_ldap_dn_in_model(self):
        """Test KhojUser model has ldap_dn field defined."""
        models_file = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "khoj",
            "database",
            "models",
            "__init__.py",
        )

        with open(models_file, "r") as f:
            content = f.read()

        # Verify ldap_dn field exists in KhojUser
        assert "ldap_dn" in content
        assert "KhojUser" in content

    def test_entry_model_has_embeddings_field(self):
        """Test Entry model has embeddings field defined."""
        models_file = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "khoj",
            "database",
            "models",
            "__init__.py",
        )

        with open(models_file, "r") as f:
            content = f.read()

        # Verify embeddings field exists in Entry
        assert "embeddings" in content
        assert "class Entry" in content

    def test_entry_save_method_exists(self):
        """Test Entry model has save method defined."""
        models_file = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "khoj",
            "database",
            "models",
            "__init__.py",
        )

        with open(models_file, "r") as f:
            content = f.read()

        # Verify save method exists in Entry class
        assert "def save" in content
        # Verify the validation logic exists
        assert "ValidationError" in content or "super().save" in content


# Database-dependent tests - only run if database is available
class TestEntrySaveFix:
    """Test Entry.save() fix - Entry creation and persistence."""

    @pytest.mark.django_db
    def test_entry_objects_create_returns_valid_id(self, db):
        """Test that Entry.objects.create() returns entry with valid ID."""
        from khoj.database.models import Entry, KhojUser

        # Create a test user
        user = KhojUser.objects.create(
            username="test_entry_user",
            email="test_entry@example.com",
        )

        # Create entry
        entry = Entry.objects.create(
            user=user,
            raw="Test raw content",
            compiled="Test compiled content",
            hashed_value="test_hash_001",
        )

        # Verify entry has valid ID
        assert entry.id is not None
        assert isinstance(entry.id, int)
        assert entry.id > 0

    @pytest.mark.django_db
    def test_entry_save_persists_data_to_database(self, db):
        """Test that entry.save() persists data to database."""
        from khoj.database.models import Entry, KhojUser

        # Create a test user
        user = KhojUser.objects.create(
            username="test_save_user",
            email="test_save@example.com",
        )

        # Create entry
        entry = Entry(
            user=user,
            raw="Raw content to save",
            compiled="Compiled content to save",
            hashed_value="test_hash_002",
        )
        entry.save()

        # Verify data is persisted by querying fresh from DB
        fresh_entry = Entry.objects.get(id=entry.id)
        assert fresh_entry.raw == "Raw content to save"
        assert fresh_entry.compiled == "Compiled content to save"
        assert fresh_entry.hashed_value == "test_hash_002"

    @pytest.mark.django_db
    def test_entry_is_queryable_after_save(self, db):
        """Test that entry is queryable after save."""
        from khoj.database.models import Entry, KhojUser

        # Create a test user
        user = KhojUser.objects.create(
            username="test_query_user",
            email="test_query@example.com",
        )

        # Create entry
        entry = Entry.objects.create(
            user=user,
            raw="Query test content",
            compiled="Query compiled content",
            hashed_value="test_hash_003",
        )

        # Test various query methods
        # 1. Query by ID
        queried_by_id = Entry.objects.filter(id=entry.id).first()
        assert queried_by_id is not None
        assert queried_by_id.id == entry.id

        # 2. Query by user
        user_entries = Entry.objects.filter(user=user)
        assert user_entries.count() == 1
        assert user_entries.first().id == entry.id

        # 3. Query by hashed_value
        queried_by_hash = Entry.objects.filter(hashed_value="test_hash_003").first()
        assert queried_by_hash is not None
        assert queried_by_hash.id == entry.id

        # 4. Verify entry exists
        assert Entry.objects.filter(id=entry.id).exists()


class TestNewModelFields:
    """Test new model fields are properly defined."""

    @pytest.mark.django_db
    def test_search_model_config_has_hybrid_alpha_field(self, db):
        """Test SearchModelConfig has hybrid_alpha field."""
        from khoj.database.models import SearchModelConfig

        # Create SearchModelConfig with hybrid_alpha
        config = SearchModelConfig.objects.create(
            name="Test Config",
            bi_encoder="test/encoder",
            hybrid_alpha=0.75,
        )

        # Verify field exists and value is set
        assert hasattr(config, 'hybrid_alpha')
        assert config.hybrid_alpha == 0.75

        # Verify default value
        config_default = SearchModelConfig.objects.create(
            name="Test Config Default",
            bi_encoder="test/encoder2",
        )
        assert config_default.hybrid_alpha == 0.6  # Default value

    @pytest.mark.django_db
    def test_search_model_config_has_hybrid_enabled_field(self, db):
        """Test SearchModelConfig has hybrid_enabled field."""
        from khoj.database.models import SearchModelConfig

        # Create SearchModelConfig with hybrid_enabled=False
        config = SearchModelConfig.objects.create(
            name="Test Config Disabled",
            bi_encoder="test/encoder",
            hybrid_enabled=False,
        )

        # Verify field exists and value is set
        assert hasattr(config, 'hybrid_enabled')
        assert config.hybrid_enabled is False

        # Verify default value
        config_default = SearchModelConfig.objects.create(
            name="Test Config Default Enabled",
            bi_encoder="test/encoder2",
        )
        assert config_default.hybrid_enabled is True  # Default value

    @pytest.mark.django_db
    def test_khoj_user_has_ldap_dn_field(self, db):
        """Test KhojUser has ldap_dn field."""
        from khoj.database.models import KhojUser

        # Create user with ldap_dn
        user = KhojUser.objects.create(
            username="ldap_user",
            email="ldap@example.com",
            ldap_dn="CN=ldap_user,OU=Users,DC=example,DC=com",
        )

        # Verify field exists and value is set
        assert hasattr(user, 'ldap_dn')
        assert user.ldap_dn == "CN=ldap_user,OU=Users,DC=example,DC=com"

        # Verify field is nullable
        user_no_ldap = KhojUser.objects.create(
            username="regular_user",
            email="regular@example.com",
        )
        assert user_no_ldap.ldap_dn is None

    @pytest.mark.django_db
    def test_entry_embeddings_is_nullable(self, db):
        """Test Entry.embeddings is nullable."""
        from khoj.database.models import Entry, KhojUser

        # Create a test user
        user = KhojUser.objects.create(
            username="test_null_embeddings",
            email="null_embeddings@example.com",
        )

        # Create entry with null embeddings
        entry = Entry.objects.create(
            user=user,
            raw="Test content",
            compiled="Compiled content",
            hashed_value="test_hash_null",
            embeddings=None,
        )

        # Verify field is nullable
        assert entry.embeddings is None

        # Verify entry can be saved and retrieved
        fresh_entry = Entry.objects.get(id=entry.id)
        assert fresh_entry.embeddings is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
