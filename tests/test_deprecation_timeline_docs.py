"""
Tests to verify deprecation timeline documentation is complete and accurate.

This test validates that the deprecation.md file contains all required sections
and documented features follow proper deprecation practices.
"""

import os
import pytest
from pathlib import Path


# Path to deprecation documentation
DEPRECATION_DOC_PATH = os.path.join(
    os.path.dirname(__file__), "..", "khoj-repo", "docs", "deprecation.md"
)


def read_deprecation_doc():
    """Read the deprecation documentation file."""
    with open(DEPRECATION_DOC_PATH, "r", encoding="utf-8") as f:
        return f.read()


class TestDeprecationTimelineDocumentation:
    """Test class for deprecation timeline documentation verification."""

    def test_deprecation_doc_exists(self):
        """Test that the deprecation documentation file exists."""
        assert os.path.exists(DEPRECATION_DOC_PATH), \
            f"Deprecation documentation not found at {DEPRECATION_DOC_PATH}"

    def test_deprecation_doc_has_title(self):
        """Test that deprecation doc has a proper title."""
        content = read_deprecation_doc()
        assert "# Deprecation Timeline" in content, \
            "Deprecation doc must have '# Deprecation Timeline' heading"

    def test_max_tokens_deprecation_documented(self):
        """Test that max_tokens parameter deprecation is documented."""
        content = read_deprecation_doc()
        
        # Check for max_tokens parameter mention
        assert "max_tokens" in content, \
            "max_tokens parameter deprecation must be documented"
        
        # Check for deprecation version
        assert "v2.0.0" in content, \
            "Deprecation version (v2.0.0) must be documented"
        
        # Check for removal version
        assert "v2.2.0" in content, \
            "Removal version (v2.2.0) must be documented"

    def test_replacement_parameter_documented(self):
        """Test that the replacement parameter (chunk_sizes) is documented."""
        content = read_deprecation_doc()
        
        assert "chunk_sizes" in content, \
            "Replacement parameter 'chunk_sizes' must be documented"

    def test_migration_path_documented(self):
        """Test that migration path is documented with before/after examples."""
        content = read_deprecation_doc()
        
        # Check for "Before" and "After" examples
        assert "Before" in content or "before" in content.lower(), \
            "Migration path must include 'before' example"
        assert "After" in content or "after" in content.lower(), \
            "Migration path must include 'after' example"
        
        # Check for code blocks
        assert "```python" in content, \
            "Migration examples must include code blocks"

    def test_affected_files_documented(self):
        """Test that affected files are listed."""
        content = read_deprecation_doc()
        
        # Check that affected files section exists
        assert "Affected Files" in content or "affected" in content.lower(), \
            "Affected files section must be documented"
        
        # Check for at least one processor file
        assert "processor" in content.lower(), \
            "Processor files must be listed as affected"

    def test_deprecation_status_included(self):
        """Test that status section includes version info."""
        content = read_deprecation_doc()
        
        # Check for status section
        assert "Status" in content, \
            "Status section must be included"
        
        # Check for Deprecated label
        assert "Deprecated" in content, \
            "Must include 'Deprecated' label with version"

    def test_removal_date_estimated(self):
        """Test that removal date is estimated."""
        content = read_deprecation_doc()
        
        assert "Removal" in content, \
            "Removal date/version must be documented"
        
        # Check for Q2 2025 or similar timeframe
        assert "Q2" in content or "2025" in content or "estimated" in content.lower(), \
            "Removal date should include estimated timeframe"

    def test_backward_compatibility_mentioned(self):
        """Test that backward compatibility is documented."""
        content = read_deprecation_doc()
        
        assert "Backward Compatible" in content or "backward compatible" in content.lower(), \
            "Backward compatibility information must be documented"

    def test_deprecation_warning_mentioned(self):
        """Test that deprecation warning is mentioned."""
        content = read_deprecation_doc()
        
        assert "DeprecationWarning" in content or "deprecation warning" in content.lower(), \
            "Users should be warned about deprecation warning"

    def test_key_differences_table_exists(self):
        """Test that key differences table is included."""
        content = read_deprecation_doc()
        
        # Check for table or comparison
        assert "|" in content or "table" in content.lower(), \
            "Key differences should be shown in table format"


class TestDeprecationTimelineCompleteness:
    """Additional tests for deprecation timeline completeness."""

    def test_documents_tracks_deprecated_features(self):
        """Test that doc tracks deprecated features."""
        content = read_deprecation_doc()
        
        # Must mention deprecated features tracking
        assert "deprecated" in content.lower(), \
            "Document must track deprecated features"

    def test_has_description_section(self):
        """Test that there's a description section."""
        content = read_deprecation_doc()
        
        assert "Description" in content, \
            "Must have Description section"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
