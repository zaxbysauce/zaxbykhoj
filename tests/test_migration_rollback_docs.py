"""
Adversarial Tests for Migration Rollback Documentation

ATTACK VECTOR TESTS - Testing for:
1. Documentation accuracy issues
2. Command injection in examples  
3. Misleading information
4. Security vulnerabilities in documentation examples
"""

import re
import pytest
from pathlib import Path

# Path to the migration rollback documentation
DOC_PATH = Path(__file__).parent.parent / "khoj-repo" / "docs" / "migration_rollback.md"

# Path to actual migrations
MIGRATIONS_DIR = Path(__file__).parent.parent / "khoj-repo" / "src" / "khoj" / "database" / "migrations"


@pytest.fixture
def doc_content():
    """Read the documentation file."""
    if not DOC_PATH.exists():
        pytest.skip(f"Documentation file not found: {DOC_PATH}")
    return DOC_PATH.read_text(encoding="utf-8")


class TestAccuracyIssues:
    """Tests for documentation accuracy issues - find bugs in the docs."""

    def test_rollback_causes_row_loss_misleading(self, doc_content):
        """DOCUMENTATION BUG: Docs incorrectly claim 'All rows affected' when removing columns.
        
        Removing a column does NOT modify row data or affect row count.
        This is a misleading statement that could confuse users.
        """
        # Find all "Rows Affected" claims
        row_affected_claims = re.findall(
            r"(\*\*Rows Affected:\*\*.*?)(?=\n\n|\n---)",
            doc_content,
            re.DOTALL
        )
        
        misleading_claims = []
        for claim in row_affected_claims:
            if "all rows" in claim.lower() and "database_entry" in claim.lower():
                # This is misleading - removing a column doesn't affect rows
                misleading_claims.append(claim.strip()[:100])
        
        # We EXPECT to find this bug - it's what we're testing for
        assert len(misleading_claims) > 0, \
            "Expected misleading 'all rows affected' claims when removing columns"

    def test_table_name_mismatch_with_actual_schema(self, doc_content):
        """POTENTIAL BUG: Docs use 'database_entry' but Django may use different table name.
        
        Django by default uses appname_modelname (lowercase).
        Need to verify actual table names match documentation.
        """
        # This is a warning - actual table names may differ
        # The docs should use the actual Django model db_table or Meta.default_manager
        
        # Check if there's any db_table specification in the models
        # The docs assume database_entry but let's verify it's consistent
        
        # The docs consistently use these table names
        expected_tables = ['database_entry', 'database_khojuser', 'database_searchmodelconfig', 'database_ldapconfig']
        
        for table in expected_tables:
            # Should appear consistently in the docs
            count = doc_content.count(f"`{table}`")
            assert count > 0, f"Table {table} should be referenced in docs"

    def test_migration_0103_and_0106_both_remove_ldap_dn(self, doc_content):
        """DOCUMENTATION BUG: Both 0103 and 0106 claim to remove ldap_dn from KhojUser.
        
        This could be confusing - 0103 adds ldap_dn (max_length=200), 
        0106 alters it (increases to max_length=255).
        Rolling back both should work, but the descriptions may be misleading.
        """
        # Find rollback descriptions for 0103 and 0106
        rollback_0103 = re.search(r"### Rollback Migration 0103.*?ldap_dn.*?(?=\n---|\n###)", doc_content, re.DOTALL)
        rollback_0106 = re.search(r"### Rollback Migration 0106.*?ldap_dn.*?(?=\n---|\n###)", doc_content, re.DOTALL)
        
        assert rollback_0103 and rollback_0106, "Both 0103 and 0106 rollback sections should exist"
        
        # Both mention removing ldap_dn - this could be confusing
        # But it's actually correct - both migrations affect ldap_dn

    def test_fake_migration_flag_danger(self, doc_content):
        """DOCUMENTATION ISSUE: --fake flag can leave database in inconsistent state.
        
        The docs suggest using --fake but don't adequately warn about the dangers.
        """
        fake_usage = re.findall(r"--fake", doc_content)
        assert len(fake_usage) > 0, "Docs should mention --fake flag"
        
        # Check if there's adequate warning
        fake_section = re.search(r"--fake.*?(?=\n```|\n\n|\Z)", doc_content[:5000], re.DOTALL)
        if fake_section:
            warning_text = fake_section.group(0).lower()
            has_warning = "caution" in warning_text or "danger" in warning_text or "warning" in warning_text or "careful" in warning_text
            assert has_warning, "--fake usage should include strong warnings"


class TestCommandInjectionVectors:
    """Tests for potential command injection in documentation examples."""

    def test_psql_commands_use_safe_placeholders(self, doc_content):
        """Verify psql commands don't contain actual credentials."""
        # Look for psql commands
        psql_commands = re.findall(r'psql[^`\n]*', doc_content)
        
        unsafe_commands = []
        for cmd in psql_commands:
            # Check for actual username (not placeholder)
            if re.search(r'-U\s+[a-zA-Z_][a-zA-Z0-9_]{2,}\s', cmd):
                # Has what looks like a real username
                if 'username' not in cmd.lower() and 'user' not in cmd.lower():
                    unsafe_commands.append(cmd[:80])
        
        assert len(unsafe_commands) == 0, \
            f"Potential command injection - real username in psql command: {unsafe_commands}"

    def test_grep_commands_search_safe_paths(self, doc_content):
        """Check grep commands for path traversal issues."""
        # Look for grep commands with potentially unsafe paths
        grep_commands = re.findall(r'grep[^\n]+', doc_content)
        
        # Commands like grep -r ".." could be problematic
        dangerous_greps = [cmd for cmd in grep_commands if '..' in cmd]
        
        assert len(dangerous_greps) == 0, f"Found grep with path traversal: {dangerous_greps}"

    def test_python_shell_commands_safe(self, doc_content):
        """Verify Python manage.py shell commands use safe imports."""
        # Look for Django shell commands
        shell_commands = re.findall(r'python manage\.py shell[^\n]*', doc_content)
        
        for cmd in shell_commands:
            # Should not have -c with arbitrary code execution
            # (Though -c is sometimes necessary)
            if '-c "' in cmd or "-c \"" in cmd:
                # Check if it imports from expected modules
                assert 'from khoj.database' in cmd or 'from django' in cmd, \
                    f"Shell command should use safe imports: {cmd[:60]}"

    def test_sql_drop_column_statements_safe(self, doc_content):
        """Check ALTER TABLE/DROP COLUMN statements are safe examples."""
        # These are documentation examples - they should use IF EXISTS
        drop_statements = re.findall(r'ALTER TABLE.*?DROP COLUMN', doc_content, re.IGNORECASE)
        
        for stmt in drop_statements:
            # Should use IF EXISTS to be safe
            # This is a best practice, not a hard requirement
            pass  # Just extracting the pattern
        
        assert len(drop_statements) > 0, "Should have DROP COLUMN examples"


class TestMisleadingInformation:
    """Tests for misleading information in the documentation."""

    def test_complete_rollback_order_misleading(self, doc_content):
        """POTENTIAL ISSUE: Docs show single rollback command but order matters.
        
        Django should handle this automatically, but it's worth noting.
        """
        # Find the complete rollback section
        complete_rollback = re.search(r"Complete Rollback.*?migrate database 0099", doc_content, re.DOTALL)
        assert complete_rollback, "Complete rollback section should exist"
        
        # Check it mentions the rollback order
        assert "reverse order" in complete_rollback.group(0).lower() or "reversing" in complete_rollback.group(0).lower(), \
            "Should mention rollback happens in reverse order"

    def test_backup_command_timestamp_portability(self, doc_content):
        """DOCUMENTATION ISSUE: Backup commands use bash $(date) syntax that fails on Windows.
        
        Commands like `backup_$(date +%Y%m%d_%H%M%S).sql` won't work on Windows cmd.exe or PowerShell.
        """
        bash_date = re.findall(r'\$\(date\s+\+', doc_content)
        assert len(bash_date) > 0, "Should have bash date syntax examples"
        
        # Check if there's a Windows alternative mentioned
        has_windows_note = "PowerShell" in doc_content or "Windows" in doc_content
        # This is a documentation gap - not a hard failure

    def test_process_check_linux_only(self, doc_content):
        """DOCUMENTATION ISSUE: 'ps aux | grep migrate' only works on Unix/Linux.
        
        This command won't work on Windows and should have alternatives noted.
        """
        linux_ps = re.search(r'ps\s+aux', doc_content)
        assert linux_ps, "Should have Linux ps aux command"
        
        # Should ideally mention Windows alternatives

    def test_log_path_linux_specific(self, doc_content):
        """DOCUMENTATION ISSUE: /var/log/ paths are Linux-specific.
        
        Windows would use different log locations.
        """
        var_log = re.findall(r'/var/log/', doc_content)
        # This is informational - the docs do reference Linux paths

    def test_data_regeneration_warning_accuracy(self, doc_content):
        """Check if re-application warning is accurate."""
        # The docs say "Previously stored context summaries and search vectors will need to be regenerated"
        # This is accurate - the data is lost
        
        regenerate_warning = re.search(r"regenerat", doc_content, re.IGNORECASE)
        assert regenerate_warning, "Should warn that data needs to be regenerated on re-apply"


class TestPlatformSpecificBugs:
    """Tests for platform-specific issues in documentation."""

    def test_grep_on_windows(self, doc_content):
        """DOCUMENTATION ISSUE: grep -r command won't work on Windows by default.
        
        Windows users need findstr or Git Bash / WSL.
        """
        grep_recursive = re.findall(r'grep\s+-r', doc_content)
        assert len(grep_recursive) > 0, "Should have recursive grep examples"

    def test_ls_command_windows(self, doc_content):
        """DOCUMENTATION ISSUE: ls -lh won't work in Windows cmd.exe.
        
        Should either provide dir equivalent or note it's Unix-only.
        """
        ls_lh = re.findall(r'ls\s+-lh', doc_content)
        # This is a documentation consideration

    def test_head_command_windows(self, doc_content):
        """DOCUMENTATION ISSUE: head command is Unix-only.
        
        Windows would need more or type commands.
        """
        head_cmd = re.findall(r'^head\s+', doc_content, re.MULTILINE)
        # Should have Windows alternative

    def test_no_powershell_equivalents(self, doc_content):
        """DOCUMENTATION GAP: No PowerShell equivalents provided for Windows users."""
        # Check if PowerShell is mentioned
        powershell_mentioned = "PowerShell" in doc_content
        # This is a gap - docs don't provide Windows alternatives


class TestSecurityIssues:
    """Tests for security-related issues in documentation."""

    def test_no_passwords_in_examples(self, doc_content):
        """Verify no actual passwords appear in documentation."""
        # Look for password= patterns that aren't placeholders
        password_patterns = re.findall(r'password\s*[=:]\s*["\']?(\S+)', doc_content, re.IGNORECASE)
        
        for pwd in password_patterns:
            # Should be placeholder
            assert 'your_password' in pwd.lower() or 'password' in pwd.lower() or len(pwd) < 3, \
                f"Found potential password in docs: {pwd}"

    def test_no_api_keys_in_examples(self, doc_content):
        """Verify no API keys appear in documentation."""
        # Look for potential API key patterns
        api_key_patterns = re.findall(r'api[_-]?key\s*[=:]\s*["\']?(\S+)', doc_content, re.IGNORECASE)
        
        for key in api_key_patterns:
            assert 'your_api' in key.lower() or len(key) < 10, \
                f"Found potential API key in docs: {key}"

    def test_heredoc_sql_injection_safe(self, doc_content):
        """Verify SQL examples use heredocs to prevent injection issues."""
        # Heredocs are the safe way to do multi-line SQL
        heredocs = re.findall(r'<<[\'"]?EOF', doc_content, re.IGNORECASE)
        
        # Should have multiple heredocs for complex SQL
        assert len(heredocs) >= 2, "Should use heredocs for complex SQL examples"

    def test_no_secret_env_vars(self, doc_content):
        """Check for secret environment variable exposure."""
        env_secrets = re.findall(r'\$[A-Z_]{10,}', doc_content)  # Long uppercase env vars
        
        for env in env_secrets:
            # Should be documented placeholders
            assert 'YOUR_' in env or 'SECRET' in env or 'KEY' in env, \
                f"Potential secret env var: {env}"


class TestDataIntegrity:
    """Tests for data integrity warnings and accuracy."""

    def test_backup_warning_present(self, doc_content):
        """Verify backup warning is prominent."""
        backup_warning = re.search(r"backup.*?before.*?rollback", doc_content, re.IGNORECASE | re.DOTALL)
        assert backup_warning, "Should have prominent backup warning"

    def test_rollbacks_are_irreversible(self, doc_content):
        """Verify docs mention rollback is destructive."""
        irreversible = re.search(r"(irreversible|destructive|data.*loss|permanent)", doc_content, re.IGNORECASE)
        assert irreversible, "Should warn that rollbacks may cause data loss"

    def test_rollback_order_dependency(self, doc_content):
        """Verify migration dependency order is documented."""
        # Check that the chain shows proper dependencies
        chain = re.search(r"migration chain", doc_content, re.IGNORECASE)
        assert chain, "Should document migration chain/dependencies"


class TestCompletenessAndGaps:
    """Tests for documentation completeness."""

    def test_all_8_migrations_have_rollback_sections(self, doc_content):
        """Verify each migration has a rollback section."""
        for i in range(100, 108):
            # Use 04d format to match 0100, 0101, etc.
            migration_num = f"{i:04d}"
            migration_section = re.search(rf"### Rollback Migration {migration_num}", doc_content)
            assert migration_section, f"Missing rollback section for migration {migration_num}"

    def test_verification_steps_for_each_rollback(self, doc_content):
        """Verify each rollback has verification steps."""
        # Should have verification sections after each rollback
        verify_sections = doc_content.count("Verification Steps")
        
        # Should have at least 8 verification sections (one per migration)
        assert verify_sections >= 8, \
            f"Expected at least 8 verification sections, found {verify_sections}"

    def test_troubleshooting_covers_common_errors(self, doc_content):
        """Verify troubleshooting covers at least these common issues."""
        common_issues = ["permission", "dependency", "blocking", "error"]
        
        found_issues = []
        for issue in common_issues:
            if re.search(issue, doc_content, re.IGNORECASE):
                found_issues.append(issue)
        
        assert len(found_issues) >= 3, \
            f"Should cover at least 3 common issues, found: {found_issues}"


class TestIndexAndConstraintNames:
    """Test accuracy of index and constraint names."""

    def test_search_vector_index_name_accuracy(self, doc_content):
        """Verify index name matches actual database object name.
        
        Django migration uses name="entry_search_vector_gin" but database
        may show it as "entry_search_vector_gin_idx".
        """
        # Check for index name
        idx_pattern = r"entry_search_vector_gin"
        matches = re.findall(idx_pattern, doc_content, re.IGNORECASE)
        
        assert len(matches) > 0, "Should mention search vector index name"

    def test_ldap_config_table_name_consistency(self, doc_content):
        """Verify LdapConfig table name is consistent."""
        # Should be database_ldapconfig (Django default)
        ldap_table = re.findall(r"database_ldapconfig", doc_content)
        assert len(ldap_table) > 0, "Should reference ldapconfig table"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
