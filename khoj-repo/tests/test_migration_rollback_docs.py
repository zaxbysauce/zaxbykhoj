"""
Test migration rollback documentation verification.

This module tests the migration_rollback.md documentation for:
1. All required sections exist
2. Example commands are syntactically correct
3. Migration numbers match actual files
4. Rollback commands would work
"""

import os
import re
from pathlib import Path

import pytest

# Path to the documentation file
DOCS_PATH = Path(__file__).parent.parent / "docs" / "migration_rollback.md"
MIGRATIONS_DIR = Path(__file__).parent.parent / "src" / "khoj" / "database" / "migrations"


class TestMigrationRollbackDocs:
    """Test cases for migration rollback documentation verification."""

    @pytest.fixture(scope="class")
    def doc_content(self):
        """Load the documentation content."""
        if not DOCS_PATH.exists():
            pytest.skip(f"Documentation file not found: {DOCS_PATH}")
        return DOCS_PATH.read_text(encoding="utf-8")

    @pytest.fixture(scope="class")
    def migration_files(self):
        """Get list of actual migration files."""
        if not MIGRATIONS_DIR.exists():
            pytest.skip(f"Migrations directory not found: {MIGRATIONS_DIR}")
        return list(MIGRATIONS_DIR.glob("*.py"))

    # ==========================================================================
    # Test 1: All Required Sections Present
    # ==========================================================================
    def test_all_sections_present(self, doc_content):
        """Verify all required sections exist in the documentation."""
        required_sections = [
            "## Overview",
            "## Pre-Rollback Checklist",
            "## Rollback Procedures",
            "## Complete Rollback (All 3 Migrations)",
            "## Post-Rollback Verification",
            "## Troubleshooting",
            "## Appendix: Migration Chain",
        ]

        missing_sections = []
        for section in required_sections:
            if section not in doc_content:
                missing_sections.append(section)

        assert not missing_sections, f"Missing required sections: {missing_sections}"

    # ==========================================================================
    # Test 2: Migration Numbers Match Actual Files
    # ==========================================================================
    def test_migration_numbers_correct(self, doc_content, migration_files):
        """Verify migration numbers in docs match actual migration files."""
        # Expected migrations based on documentation
        expected_migrations = {
            "0100": "0100_add_search_vector.py",
            "0101": "0101_add_context_summary.py",
            "0102": "0102_add_chunk_scale.py",
            "0099": "0099_usermemory.py",
        }

        # Check that documented migrations exist as files
        migration_file_names = {f.name for f in migration_files}

        for migration_num, expected_file in expected_migrations.items():
            assert expected_file in migration_file_names, (
                f"Migration {migration_num} file '{expected_file}' not found in migrations directory. "
                f"Found files: {migration_file_names}"
            )

        # Verify migration numbers are mentioned in documentation
        for migration_num in expected_migrations.keys():
            assert migration_num in doc_content, (
                f"Migration number {migration_num} not found in documentation"
            )

    # ==========================================================================
    # Test 3: Rollback Commands Valid
    # ==========================================================================
    def test_rollback_commands_valid(self, doc_content):
        """Verify rollback commands follow valid Django migration syntax."""
        # Pattern to match migration commands: python manage.py migrate database <number>
        migrate_pattern = r'python manage\.py migrate database (\d+)'
        matches = re.findall(migrate_pattern, doc_content)

        assert matches, "No rollback migration commands found in documentation"

        # Valid migration numbers mentioned in docs
        valid_numbers = {"0099", "0100", "0101", "0102"}

        invalid_commands = []
        for match in matches:
            if match not in valid_numbers:
                invalid_commands.append(match)

        assert not invalid_commands, (
            f"Invalid migration numbers in commands: {invalid_commands}. "
            f"Valid numbers are: {valid_numbers}"
        )

    # ==========================================================================
    # Test 4: Example Commands Complete
    # ==========================================================================
    def test_example_commands_complete(self, doc_content):
        """Verify all example commands are complete and well-formed."""
        # Check for backup commands
        backup_patterns = [
            r'pg_dump.*backup_.*\.sql',
            r'pg_dump.*\.sql\.gz',
        ]

        has_backup_command = any(
            re.search(pattern, doc_content) for pattern in backup_patterns
        )
        assert has_backup_command, "No database backup command found in documentation"

        # Check for showmigrations command
        assert "python manage.py showmigrations" in doc_content, (
            "showmigrations command not found in documentation"
        )

        # Check for dbshell commands
        assert "python manage.py dbshell" in doc_content, (
            "dbshell command not found in documentation"
        )

        # Check for verification commands
        verification_patterns = [
            r'grep.*search_vector',
            r'grep.*context_summary',
            r'grep.*chunk_scale',
        ]

        has_verification_commands = sum(
            1 for pattern in verification_patterns
            if re.search(pattern, doc_content)
        )
        assert has_verification_commands >= 2, (
            f"Insufficient verification commands found. Expected at least 2, found {has_verification_commands}"
        )

    # ==========================================================================
    # Test 5: Migration Dependencies Correct
    # ==========================================================================
    def test_migration_dependencies_correct(self, doc_content, migration_files):
        """Verify migration dependencies match actual file dependencies."""
        # Read actual migration files to check dependencies
        dependencies = {}

        for migration_file in migration_files:
            if migration_file.name in [
                "0100_add_search_vector.py",
                "0101_add_context_summary.py",
                "0102_add_chunk_scale.py",
                "0099_usermemory.py",
            ]:
                content = migration_file.read_text(encoding="utf-8")
                # Extract dependencies from the file
                dep_match = re.search(r'dependencies\s*=\s*\[\s*\(\s*"database"\s*,\s*"(\d+_[^"]+)"\s*\)', content)
                if dep_match:
                    dependencies[migration_file.name] = dep_match.group(1)

        # Verify documented dependencies match actual dependencies
        # 0100 depends on 0099
        if "0100_add_search_vector.py" in dependencies:
            assert "0099_usermemory" in dependencies["0100_add_search_vector.py"], (
                "Migration 0100 dependency mismatch: should depend on 0099_usermemory"
            )

        # 0101 depends on 0100
        if "0101_add_context_summary.py" in dependencies:
            assert "0100_add_search_vector" in dependencies["0101_add_context_summary.py"], (
                "Migration 0101 dependency mismatch: should depend on 0100_add_search_vector"
            )

        # 0102 depends on 0101
        if "0102_add_chunk_scale.py" in dependencies:
            assert "0101_add_context_summary" in dependencies["0102_add_chunk_scale.py"], (
                "Migration 0102 dependency mismatch: should depend on 0101_add_context_summary"
            )

    # ==========================================================================
    # Test 6: Rollback Paths Table Complete
    # ==========================================================================
    def test_rollback_paths_table_complete(self, doc_content):
        """Verify rollback paths table includes all valid rollback combinations."""
        # Expected rollback paths based on migration chain
        expected_paths = [
            ("0102", "0101"),
            ("0102", "0100"),
            ("0102", "0099"),
            ("0101", "0100"),
            ("0101", "0099"),
            ("0100", "0099"),
        ]

        for from_ver, to_ver in expected_paths:
            pattern = rf'\|\s*{from_ver}\s*\|\s*{to_ver}\s*\|'
            assert re.search(pattern, doc_content), (
                f"Rollback path from {from_ver} to {to_ver} not found in documentation table"
            )

    # ==========================================================================
    # Test 7: Field Documentation Matches Migration
    # ==========================================================================
    def test_field_documentation_matches_migration(self, doc_content, migration_files):
        """Verify field documentation matches actual migration definitions."""
        # Check documented fields exist in migrations
        fields_to_check = {
            "0100": ["search_vector", "entry_search_vector_gin_idx"],
            "0101": ["context_summary"],
            "0102": ["chunk_scale"],
        }

        for migration_num, fields in fields_to_check.items():
            for field in fields:
                assert field in doc_content, (
                    f"Field '{field}' from migration {migration_num} not documented"
                )

    # ==========================================================================
    # Test 8: Troubleshooting Section Complete
    # ==========================================================================
    def test_troubleshooting_section_complete(self, doc_content):
        """Verify troubleshooting section covers common rollback issues."""
        required_issues = [
            "Migration Dependency Error",
            "Active Queries Blocking Migration",
            "Permission Denied",
            "Column Still Exists After Rollback",
        ]

        for issue in required_issues:
            assert issue in doc_content, (
                f"Troubleshooting issue '{issue}' not found in documentation"
            )

    # ==========================================================================
    # Test 9: Recovery Procedures Documented
    # ==========================================================================
    def test_recovery_procedures_documented(self, doc_content):
        """Verify recovery procedures are documented for failure scenarios."""
        recovery_scenarios = [
            "Partial Rollback Failure",
            "Data Corruption During Rollback",
            "Application Code Still References Rolled-Back Fields",
        ]

        for scenario in recovery_scenarios:
            assert scenario in doc_content, (
                f"Recovery scenario '{scenario}' not found in documentation"
            )

    # ==========================================================================
    # Test 10: Document Metadata Present
    # ==========================================================================
    def test_document_metadata_present(self, doc_content):
        """Verify document has version metadata."""
        assert "Document Version:" in doc_content, "Document version not found"
        assert "Last Updated:" in doc_content, "Last updated date not found"
        assert "Applicable Migrations:" in doc_content, "Applicable migrations not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
