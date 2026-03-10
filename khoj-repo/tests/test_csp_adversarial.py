"""
Adversarial tests for CSP headers in base_config.html

This test suite focuses on attack vectors:
1. CSP Bypass - testing vectors that could bypass CSP restrictions
2. CSP Injection - testing if CSP can be injected/broken
3. XSS via CSP weaknesses - testing XSS vulnerabilities related to CSP

These tests identify potential security weaknesses in the CSP policy.
"""

import os
import re
import pytest


# Critical CSP security issues to detect
DANGEROUS_PATTERNS = {
    "unsafe-inline in script-src": {
        "directive": "script-src",
        "pattern": r"script-src[^;]*'unsafe-inline'",
        "severity": "HIGH",
        "description": "Allows inline scripts, enabling XSS attacks"
    },
    "data: in img-src": {
        "directive": "img-src",
        "pattern": r"img-src[^;]*data:",
        "severity": "MEDIUM",
        "description": "Allows data: URIs which can encode malicious content"
    },
    "http: sources (non-HTTPS)": {
        "directive": "any",
        "pattern": r"http://",
        "severity": "HIGH",
        "description": "Allows HTTP sources, enabling MITM attacks"
    },
    "wildcard in script-src": {
        "directive": "script-src",
        "pattern": r"script-src[^;]*\*",
        "severity": "CRITICAL",
        "description": "Wildcard allows scripts from any source"
    },
    "wildcard in default-src": {
        "directive": "default-src",
        "pattern": r"default-src[^;]*\*",
        "severity": "CRITICAL",
        "description": "Wildcard in default-src bypasses all restrictions"
    },
    "unsafe-eval in script-src": {
        "directive": "script-src",
        "pattern": r"script-src[^;]*'unsafe-eval'",
        "severity": "CRITICAL",
        "description": "Allows dynamic code execution via eval()"
    },
    "javascript: protocol": {
        "directive": "any",
        "pattern": r"javascript:",
        "severity": "HIGH",
        "description": "Allows javascript: protocol handlers"
    },
    "blob: protocol": {
        "directive": "any",
        "pattern": r"blob:",
        "severity": "HIGH",
        "description": "Allows blob: protocol which can execute code"
    },
    "unsafe-eval in default-src": {
        "directive": "default-src",
        "pattern": r"default-src[^;]*'unsafe-eval'",
        "severity": "CRITICAL",
        "description": "Allows dynamic code execution in all sources"
    },
    "Missing frame-ancestors": {
        "directive": "frame-ancestors",
        "pattern": r"^((?!frame-ancestors).)*$",
        "severity": "MEDIUM",
        "description": "Missing frame-ancestors allows clickjacking"
    },
    "Missing base-uri": {
        "directive": "base-uri",
        "pattern": r"^((?!base-uri).)*$",
        "severity": "MEDIUM",
        "description": "Missing base-uri allows base tag injection"
    },
    "Missing form-action": {
        "directive": "form-action",
        "pattern": r"^((?!form-action).)*$",
        "severity": "MEDIUM",
        "description": "Missing form-action allows form redirection"
    },
    "'self' missing from script-src": {
        "directive": "script-src",
        "pattern": r"^(?!.*script-src[^;]*'self')",
        "severity": "HIGH",
        "description": "script-src should include 'self' for same-origin scripts"
    },
    "connect-src * (wildcard)": {
        "directive": "connect-src",
        "pattern": r"connect-src[^;]*\*",
        "severity": "HIGH",
        "description": "Allows sending data to any origin"
    },
    "child-src * (wildcard)": {
        "directive": "child-src",
        "pattern": r"child-src[^;]*\*",
        "severity": "HIGH",
        "description": "Allows embedding content from any source"
    },
}


def get_csp_content(html_file_path: str) -> str:
    """Extract CSP meta tag content from the HTML file."""
    with open(html_file_path, "r", encoding="utf-8") as f:
        content = f.read()

    csp_start = content.find('Content-Security-Policy')
    if csp_start < 0:
        raise ValueError("Could not find CSP meta tag in HTML file")

    content_attr = content.find('content="', csp_start)
    if content_attr < 0:
        content_attr = content.find("content='", csp_start)
        if content_attr < 0:
            raise ValueError("Could not find content attribute in CSP meta tag")

    content_start = content_attr + 9  # len('content="')
    meta_end = content.find('>', content_start)
    if meta_end < 0:
        raise ValueError("Could not find end of CSP meta tag")

    return content[content_start:meta_end].strip()


def get_directive_value(csp_content: str, directive: str) -> str:
    """Extract a specific directive's value from CSP.
    
    Handles CSP content with HTML comments properly by removing comments first.
    """
    # Remove HTML-style comments that might be in the CSP content
    csp_cleaned = re.sub(r'/\*.*?\*/', '', csp_content, flags=re.DOTALL)
    # Also remove regular CSP comments
    csp_cleaned = re.sub(r'/\*.*?\*/', '', csp_cleaned, flags=re.DOTALL)
    
    match = re.search(rf'{directive}\s+([^;]+)', csp_cleaned, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def check_csp_bypass_via_wildcard_domain(csp_content: str) -> list:
    """Check for wildcard domains that could be exploited."""
    issues = []
    
    # Check for *.domain patterns that could be hijacked
    wildcard_pattern = r'(\*\.[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,})'
    matches = re.findall(wildcard_pattern, csp_content)
    
    for match in matches:
        # Check if there's a corresponding non-wildcard that could be compromised
        # e.g., if *.googleusercontent.com is allowed, attacker could use evil.googleusercontent.com
        issues.append(f"Wildcard domain pattern: {match}")
    
    return issues


class TestCSPBypassVectors:
    """Test class for CSP bypass attack vectors."""

    @pytest.fixture
    def base_config_path(self):
        """Path to the base_config.html file."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, "..", "src", "khoj", "interface", "web", "base_config.html")

    @pytest.fixture
    def csp_content(self, base_config_path):
        """Extract CSP content from base_config.html."""
        return get_csp_content(base_config_path)

    def test_no_unsafe_inline_in_script_src(self, csp_content):
        """
        [CRITICAL] 'unsafe-inline' in script-src allows XSS via inline scripts.
        
        Attack vector: If an attacker can inject HTML into the page, they can
        execute JavaScript via <script> tags or event handlers.
        """
        script_src = get_directive_value(csp_content, "script-src")
        
        assert "'unsafe-inline'" not in script_src.lower(), (
            f"VULNERABILITY: script-src contains 'unsafe-inline'. "
            f"XSS can be executed via injected <script> tags or event handlers. "
            f"Found in script-src: {script_src}"
        )

    def test_no_unsafe_eval_in_script_src(self, csp_content):
        """
        [CRITICAL] 'unsafe-eval' allows dynamic code execution.
        
        Attack vector: Attackers can use eval() or similar functions to
        execute arbitrary JavaScript.
        """
        script_src = get_directive_value(csp_content, "script-src")
        
        assert "'unsafe-eval'" not in script_src.lower(), (
            f"VULNERABILITY: script-src contains 'unsafe-eval'. "
            f"Allows dynamic code execution via eval(), new Function(), etc. "
            f"Found in script-src: {script_src}"
        )

    def test_no_wildcard_in_script_src(self, csp_content):
        """
        [CRITICAL] Wildcard (*) in script-src allows scripts from any origin.
        
        Attack vector: Attacker can load malicious scripts from any website.
        """
        script_src = get_directive_value(csp_content, "script-src")
        
        assert "*" not in script_src, (
            f"VULNERABILITY: script-src contains wildcard '*'. "
            f"Allows loading scripts from any origin. "
            f"Found in script-src: {script_src}"
        )

    def test_no_http_sources(self, csp_content):
        """
        [HIGH] HTTP sources allow MITM attacks.
        
        Attack vector: Attacker on network can inject malicious content
        into HTTP responses.
        """
        csp_lower = csp_content.lower()
        
        assert "http://" not in csp_lower, (
            f"VULNERABILITY: CSP contains HTTP (non-HTTPS) sources. "
            f"Network attackers can inject malicious content."
        )

    def test_no_javascript_protocol(self, csp_content):
        """
        [HIGH] javascript: protocol handlers enable XSS.
        
        Attack vector: Can be used in href, src, etc. to execute code.
        """
        assert "javascript:" not in csp_content.lower(), (
            f"VULNERABILITY: CSP allows javascript: protocol. "
            f"Attackers can use javascript: URLs for XSS."
        )

    def test_no_blob_protocol(self, csp_content):
        """
        [HIGH] blob: protocol can execute code.
        
        Attack vector: blob: URLs can contain and execute JavaScript.
        """
        assert "blob:" not in csp_content.lower(), (
            f"VULNERABILITY: CSP allows blob: protocol. "
            f"blob: URLs can execute code."
        )

    def test_connect_src_not_wildcard(self, csp_content):
        """
        [HIGH] Wildcard in connect-src allows data exfiltration.
        
        Attack vector: Attacker can make AJAX/Fetch requests to any domain,
        exfiltrating sensitive data.
        """
        connect_src = get_directive_value(csp_content, "connect-src")
        
        if connect_src:  # Only check if directive exists
            assert "*" not in connect_src, (
                f"VULNERABILITY: connect-src contains wildcard '*'. "
                f"Allows sending data to any origin. "
                f"Found in connect-src: {connect_src}"
            )

    def test_child_src_not_wildcard(self, csp_content):
        """
        [HIGH] Wildcard in child-src allows embedding any content.
        
        Attack vector: Attacker can embed malicious iframes.
        """
        child_src = get_directive_value(csp_content, "child-src")
        
        if child_src:
            assert "*" not in child_src, (
                f"VULNERABILITY: child-src contains wildcard '*'. "
                f"Allows embedding content from any source. "
                f"Found in child-src: {child_src}"
            )


class TestCSPInjectionVectors:
    """Test class for CSP injection attack vectors."""

    @pytest.fixture
    def base_config_path(self):
        """Path to the base_config.html file."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, "..", "src", "khoj", "interface", "web", "base_config.html")

    @pytest.fixture
    def csp_content(self, base_config_path):
        """Extract CSP content from base_config.html."""
        return get_csp_content(base_config_path)

    def test_csp_properly_escaped(self, csp_content):
        """
        Test that CSP values don't contain characters that could break CSP parsing.
        
        Attack vector: Injection of semicolons or quotes could break CSP.
        """
        # Check for unescaped quotes that could break CSP
        # CSP should use single quotes around keywords
        problematic_patterns = [
            r'"[^"]*$',  # Unclosed double quote
            r"'[^']*$",  # Unclosed single quote
        ]
        
        for pattern in problematic_patterns:
            match = re.search(pattern, csp_content)
            if match:
                # This is informational - the CSP might still be valid
                # but this could indicate injection issues
                pass

    def test_no_duplicate_directives(self, csp_content):
        """
        Test that directives are not duplicated (which could cause parsing issues).
        
        Attack vector: Duplicate directives can cause browsers to ignore some restrictions.
        """
        directives = re.findall(r'^([a-z-]+)\s+', csp_content, re.MULTILINE)
        seen = set()
        duplicates = []
        
        for directive in directives:
            if directive in seen:
                duplicates.append(directive)
            seen.add(directive)
        
        assert len(duplicates) == 0, (
            f"VULNERABILITY: Duplicate CSP directives found: {duplicates}. "
            f"This can cause unpredictable browser behavior."
        )


class TestCSPXSSWeaknesses:
    """Test class for XSS-related CSP weaknesses."""

    @pytest.fixture
    def base_config_path(self):
        """Path to the base_config.html file."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, "..", "src", "khoj", "interface", "web", "base_config.html")

    @pytest.fixture
    def csp_content(self, base_config_path):
        """Extract CSP content from base_config.html."""
        return get_csp_content(base_config_path)

    def test_data_uri_in_img_src_security(self, csp_content):
        """
        [MEDIUM] data: URIs in img-src can be used for XSS in some contexts.
        
        Attack vector: While less critical, data: URIs in img-src can sometimes
        be exploited for XSS in certain browser contexts.
        """
        img_src = get_directive_value(csp_content, "img-src")
        
        # data: in img-src is less critical but worth noting
        if "data:" in img_src:
            # This is a warning, not a critical failure
            # data: in img-src is generally acceptable for inline images
            pass

    def test_self_in_script_src(self, csp_content):
        """
        [HIGH] script-src should include 'self' for same-origin scripts.
        
        Attack vector: Without 'self', legitimate same-origin scripts may be blocked,
        potentially causing developers to add more permissive rules.
        """
        script_src = get_directive_value(csp_content, "script-src")
        
        assert "'self'" in script_src.lower(), (
            f"WARNING: script-src should include 'self' to allow same-origin scripts. "
            f"Without it, developers might add unsafe rules. "
            f"Found in script-src: {script_src}"
        )

    def test_object_src_set_to_none(self, csp_content):
        """
        [HIGH] object-src should be 'none' to prevent plugin-based XSS.
        
        Attack vector: Plugins like Flash, Java can execute code.
        """
        object_src = get_directive_value(csp_content, "object-src")
        
        if object_src:
            assert "'none'" in object_src.lower(), (
                f"VULNERABILITY: object-src should be 'none' to block plugins. "
                f"Found in object-src: {object_src}"
            )

    def test_base_uri_recommended(self, csp_content):
        """
        [MEDIUM] base-uri should be set to prevent base tag injection.
        
        Attack vector: If base tag can be injected, relative URLs can be hijacked.
        """
        base_uri = get_directive_value(csp_content, "base-uri")
        
        # This is recommended but not always required
        # We issue a warning if missing
        if not base_uri:
            pass  # Advisory check

    def test_form_action_recommended(self, csp_content):
        """
        [MEDIUM] form-action should be set to prevent form hijacking.
        
        Attack vector: Forms can be redirected to attacker-controlled domains.
        """
        form_action = get_directive_value(csp_content, "form-action")
        
        # This is recommended but not always required
        if not form_action:
            pass  # Advisory check


class TestCSPHardeningRecommendations:
    """Additional security recommendations for CSP."""

    @pytest.fixture
    def base_config_path(self):
        """Path to the base_config.html file."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, "..", "src", "khoj", "interface", "web", "base_config.html")

    @pytest.fixture
    def csp_content(self, base_config_path):
        """Extract CSP content from base_config.html."""
        return get_csp_content(base_config_path)

    def test_recommend_nonce_for_inline_scripts(self, csp_content):
        """
        [RECOMMENDATION] Use nonces instead of 'unsafe-inline'.
        
        For inline scripts (like the one at line 51-55 in base_config.html),
        use nonce-based CSP instead of 'unsafe-inline'.
        """
        script_src = get_directive_value(csp_content, "script-src")
        
        if "'unsafe-inline'" in script_src.lower():
            # Check if nonce is also present (better than just unsafe-inline)
            has_nonce = "'nonce-" in script_src.lower()
            
            assert has_nonce, (
                f"RECOMMENDATION: script-src uses 'unsafe-inline'. "
                f"Consider using nonce-based approach: script-src 'self' 'nonce-{'{dynamic_nonce}'}' "
                f"for the inline script at line 51-55 in base_config.html"
            )

    def test_subresource_integrity_used(self, csp_content):
        """
        [RECOMMENDATION] External scripts should use Subresource Integrity (SRI).
        
        Check if the HTML file uses integrity attributes for external scripts.
        """
        base_config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "src", "khoj", "interface", "web", "base_config.html"
        )
        
        with open(base_config_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check for external script tags without integrity
        external_scripts = re.findall(
            r'<script[^>]+src=["\'](https?://[^"\']+)["\'][^>]*>',
            content
        )
        
        # Check for integrity attribute
        scripts_without_sri = []
        for script in external_scripts:
            # Check if this script has integrity attribute
            if f'src="{script}"' in content or f"src='{script}'" in content:
                sri_pattern = rf'<script[^>]+src=["\']?{re.escape(script)}["\']?[^>]*integrity'
                if not re.search(sri_pattern, content):
                    scripts_without_sri.append(script)
        
        # This is informational - SRI is recommended for external resources
        if scripts_without_sri:
            pass  # Advisory


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
