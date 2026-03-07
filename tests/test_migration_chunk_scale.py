"""
Tests for Django migration 0102_add_chunk_scale.py

These tests verify the migration structure and field definitions without requiring
an actual database connection by mocking Django's migration framework.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add the src directory to the path for importing the migration
khoj_repo_path = Path(__file__).parent.parent / "khoj-repo" / "src"
sys.path.insert(0, str(khoj_repo_path))


class TestMigration0102AddChunkScale:
    """Test suite for migration 0102_add_chunk_scale.py"""

    @pytest.fixture
    def migration_path(self):
        """Return the path to the migration file."""
        return (
            Path(__file__).parent.parent
            / "khoj-repo"
            / "src"
            / "khoj"
            / "database"
            / "migrations"
            / "0102_add_chunk_scale.py"
        )

    @pytest.fixture
    def migration_module(self):
        """Load and return the migration module with mocked Django."""
        # Mock Django's migrations and models modules
        mock_migrations = MagicMock()
        mock_models = MagicMock()
        mock_migrations.Migration = object

        # Create mock CharField that captures its parameters
        def mock_char_field(**kwargs):
            field_mock = MagicMock()
            field_mock.__dict__.update(kwargs)
            field_mock.max_length = kwargs.get("max_length")
            field_mock.default = kwargs.get("default")
            field_mock.blank = kwargs.get("blank")
            field_mock.null = kwargs.get("null")
            field_mock.help_text = kwargs.get("help_text")
            return field_mock

        mock_models.CharField = mock_char_field

        with patch.dict(
            "sys.modules",
            {
                "django": MagicMock(),
                "django.db": MagicMock(),
                "django.db.migrations": mock_migrations,
                "django.db.models": mock_models,
            },
        ):
            # Import the migration module fresh
            if "khoj.database.migrations.0102_add_chunk_scale" in sys.modules:
                del sys.modules["khoj.database.migrations.0102_add_chunk_scale"]

            # We need to mock the khoj module structure too
            mock_khoj = MagicMock()
            mock_database = MagicMock()
            mock_migrations_pkg = MagicMock()

            with patch.dict(
                "sys.modules",
                {
                    "khoj": mock_khoj,
                    "khoj.database": mock_database,
                    "khoj.database.migrations": mock_migrations_pkg,
                },
            ):
                # Read and execute the migration file directly
                migration_file_path = (
                    Path(__file__).parent.parent
                    / "khoj-repo"
                    / "src"
                    / "khoj"
                    / "database"
                    / "migrations"
                    / "0102_add_chunk_scale.py"
                )

                # Read the file content
                with open(migration_file_path, "r") as f:
                    source = f.read()

                # Create a module namespace with mocked dependencies
                module_namespace = {
                    "migrations": mock_migrations,
                    "models": mock_models,
                    "__name__": "test_migration",
                }

                # Execute the migration code
                exec(source, module_namespace)

                return module_namespace

    def test_migration_exists(self, migration_path):
        """Test that the migration file exists and has correct dependencies."""
        # Verify file exists
        assert migration_path.exists(), f"Migration file not found at {migration_path}"

        # Read the file content
        with open(migration_path, "r") as f:
            content = f.read()

        # Verify it's a valid Python file with expected imports
        assert "from django.db import migrations, models" in content
        assert "class Migration(migrations.Migration):" in content
        assert "dependencies = [" in content
        assert "operations = [" in content

    def test_chunk_scale_field_definition(self, migration_path):
        """Test that chunk_scale field has correct parameters (CharField, max_length=16, default, etc.)."""
        with open(migration_path, "r") as f:
            content = f.read()

        # Verify AddField operation for chunk_scale
        assert 'migrations.AddField(' in content
        assert 'model_name="entry"' in content
        assert 'name="chunk_scale"' in content

        # Verify CharField with correct parameters
        assert 'models.CharField(' in content
        assert 'max_length=16' in content
        assert 'default="default"' in content
        assert 'blank=True' in content
        assert 'null=True' in content
        assert 'help_text=' in content

        # Verify help text contains expected content
        assert 'Chunk size scale identifier' in content

    def test_migration_dependency_order(self, migration_path):
        """Test that migration depends on 0101_add_context_summary."""
        with open(migration_path, "r") as f:
            content = f.read()

        # Verify dependency on 0101_add_context_summary
        assert '("database", "0101_add_context_summary")' in content

        # Verify the dependency format is correct
        assert 'dependencies = [' in content
        assert '"database"' in content
        assert '"0101_add_context_summary"' in content

    def test_backward_compatibility(self, migration_path):
        """Test that blank=True, null=True allows NULL values for backward compatibility."""
        with open(migration_path, "r") as f:
            content = f.read()

        # Extract the field definition section
        field_start = content.find('field=models.CharField(')
        field_end = content.find(')', field_start)
        field_section = content[field_start:field_end]

        # Verify backward compatibility settings
        assert 'blank=True' in field_section, "Field should have blank=True for backward compatibility"
        assert 'null=True' in field_section, "Field should have null=True for backward compatibility"

        # Verify default value is set
        assert 'default="default"' in field_section, "Field should have a default value"

    def test_migration_file_structure(self, migration_path):
        """Test that migration file has proper structure and syntax."""
        with open(migration_path, "r") as f:
            content = f.read()

        # Verify file is valid Python syntax
        try:
            compile(content, str(migration_path), "exec")
        except SyntaxError as e:
            pytest.fail(f"Migration file has syntax error: {e}")

        # Verify class structure
        assert "class Migration(migrations.Migration):" in content

        # Verify operations list exists and is not empty
        assert "operations = [" in content
        assert "migrations.AddField(" in content

    def test_field_help_text_content(self, migration_path):
        """Test that help text provides meaningful documentation."""
        with open(migration_path, "r") as f:
            content = f.read()

        # Verify help text exists and contains useful information
        assert "help_text=" in content

        # Extract help text value
        import re

        help_text_match = re.search(r'help_text="([^"]*)"', content)
        assert help_text_match is not None, "help_text should be defined"

        help_text = help_text_match.group(1)
        assert len(help_text) > 0, "help_text should not be empty"
        assert "chunk" in help_text.lower() or "scale" in help_text.lower(), \
            "help_text should describe the field purpose"

    def test_model_name_correctness(self, migration_path):
        """Test that the field is being added to the correct model (Entry)."""
        with open(migration_path, "r") as f:
            content = f.read()

        # Verify the model name is 'entry'
        assert 'model_name="entry"' in content, "Field should be added to 'entry' model"

        # Ensure no other model is being modified
        model_name_count = content.count('model_name=')
        assert model_name_count == 1, f"Expected exactly one model_name, found {model_name_count}"


class TestMigrationWithoutMocking:
    """Tests that verify the migration file directly without complex mocking."""

    def test_migration_file_readable(self):
        """Test that the migration file exists and is readable."""
        migration_path = (
            Path(__file__).parent.parent
            / "khoj-repo"
            / "src"
            / "khoj"
            / "database"
            / "migrations"
            / "0102_add_chunk_scale.py"
        )

        assert migration_path.exists()
        assert migration_path.is_file()

        # Should be able to read content
        content = migration_path.read_text()
        assert len(content) > 0

    def test_migration_numbering(self):
        """Test that migration follows Django naming convention."""
        migration_path = (
            Path(__file__).parent.parent
            / "khoj-repo"
            / "src"
            / "khoj"
            / "database"
            / "migrations"
            / "0102_add_chunk_scale.py"
        )

        filename = migration_path.name
        # Should start with 4 digits (migration number)
        assert filename[:4].isdigit(), "Migration filename should start with numeric prefix"
        assert filename[4] == "_", "Migration number should be followed by underscore"
        assert filename.endswith(".py"), "Migration should be a Python file"

    def test_dependencies_format(self):
        """Test that dependencies are properly formatted."""
        migration_path = (
            Path(__file__).parent.parent
            / "khoj-repo"
            / "src"
            / "khoj"
            / "database"
            / "migrations"
            / "0102_add_chunk_scale.py"
        )

        content = migration_path.read_text()

        # Dependencies should be a list
        assert "dependencies = [" in content

        # Should have proper app name and migration name format
        import re

        dep_pattern = r'\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)'
        matches = re.findall(dep_pattern, content)

        assert len(matches) >= 1, "Should have at least one dependency"

        for app_name, migration_name in matches:
            assert app_name == "database", f"Expected app name 'database', got '{app_name}'"
            assert migration_name.startswith("01"), \
                f"Migration name should start with '01', got '{migration_name}'"
