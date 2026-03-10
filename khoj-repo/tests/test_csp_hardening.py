"""
Test Content Security Policy (CSP) headers are hardened in base_config.html

This test verifies:
1. unsafe-eval is NOT in the CSP
2. unsafe-inline is NOT in style-src
3. CSP is valid (has required directives)
"""

import os
import re
import pytest


# Required CSP directives for a valid, hardened policy
REQUIRED_DIRECTIVES = ["default-src", "script-src", "style-src", "img-src", "font-src"]


def get_csp_content(html_file_path: str) -> str:
    """Extract CSP meta tag content from the HTML file."""
    with open(html_file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the CSP meta tag - it spans multiple lines
    # Look for the meta tag with http-equiv="Content-Security-Policy"
    csp_start = content.find('Content-Security-Policy')
    if csp_start < 0:
        raise ValueError("Could not find CSP meta tag in HTML file")

    # Find the content attribute value - starts after content="
    content_attr = content.find('content="', csp_start)
    if content_attr < 0:
        content_attr = content.find("content='", csp_start)
        if content_attr < 0:
            raise ValueError("Could not find content attribute in CSP meta tag")

    # Extract from after content=" to the closing > of the meta tag
    content_start = content_attr + 9  # len('content="')
    # Find the closing > of the meta tag
    meta_end = content.find('>', content_start)
    if meta_end < 0:
        raise ValueError("Could not find end of CSP meta tag")

    return content[content_start:meta_end].strip()


def strip_csp_comments(csp_content: str) -> str:
    """Remove HTML comments from CSP content for accurate checking."""
    # Remove /* ... */ style comments
    return re.sub(r'/\*.*?\*/', '', csp_content, flags=re.DOTALL)


def get_style_src(csp_content: str) -> str:
    """Extract the style-src directive from CSP content."""
    # Find style-src directive
    match = re.search(r'style-src\s+([^;]+)', csp_content, re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).strip()


def get_script_src(csp_content: str) -> str:
    """Extract the script-src directive from CSP content."""
    # Find script-src directive
    match = re.search(r'script-src\s+([^;]+)', csp_content, re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).strip()


class TestCSPHardening:
    """Test class for CSP hardening verification."""

    @pytest.fixture
    def base_config_path(self):
        """Path to the base_config.html file."""
        # Navigate from tests directory to the source file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up to khoj-repo root, then to the interface/web directory
        return os.path.join(current_dir, "..", "src", "khoj", "interface", "web", "base_config.html")

    @pytest.fixture
    def csp_content(self, base_config_path):
        """Extract CSP content from base_config.html."""
        return get_csp_content(base_config_path)

    def test_csp_does_not_contain_unsafe_eval(self, csp_content):
        """
        Verify that 'unsafe-eval' is NOT present in the CSP.

        'unsafe-eval' allows eval() and similar dynamic code execution,
        which is a security risk. It should not be present in CSP.
        """
        # Strip comments to avoid false positives from comment text
        csp_no_comments = strip_csp_comments(csp_content)
        csp_lower = csp_no_comments.lower()
        assert "unsafe-eval" not in csp_lower, (
            f"CSP contains 'unsafe-eval' which allows dynamic code execution. "
            f"This is a security risk. Found in CSP: {csp_content}"
        )

    def test_style_src_does_not_contain_unsafe_inline(self, csp_content):
        """
        Verify that 'unsafe-inline' is NOT present in style-src.

        'unsafe-inline' in style-src allows inline styles, which could
        enable CSS injection attacks. It should be removed for hardening.
        """
        style_src = get_style_src(csp_content)
        style_src_lower = style_src.lower()

        assert "unsafe-inline" not in style_src_lower, (
            f"style-src contains 'unsafe-inline' which allows inline styles. "
            f"This is a security risk. Found in style-src: {style_src}"
        )

    def test_csp_is_valid(self, csp_content):
        """
        Verify that CSP is valid and contains required directives.

        A valid CSP should have core directives like default-src,
        script-src, style-src, img-src, and font-src.
        """
        csp_lower = csp_content.lower()

        # Check all required directives are present
        missing_directives = []
        for directive in REQUIRED_DIRECTIVES:
            if directive not in csp_lower:
                missing_directives.append(directive)

        assert len(missing_directives) == 0, (
            f"CSP is missing required directives: {missing_directives}. "
            f"Found in CSP: {csp_content}"
        )

        # Verify CSP is not empty
        assert len(csp_content.strip()) > 0, "CSP content is empty"


if __name__ == "__main__":
    # Allow running the test directly
    pytest.main([__file__, "-v"])
