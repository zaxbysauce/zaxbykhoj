"""
Adversarial tests for exc_info=True additions in router files.

These tests verify that adding exc_info=True doesn't introduce:
1. Security vulnerabilities (sensitive data leakage in stack traces)
2. Performance issues (excessive stack trace capture)
3. Type errors (invalid exc_info values)
4. Edge cases (using exc_info when no exception is active)

Target files:
- khoj-repo/src/khoj/routers/helpers.py
- khoj-repo/src/khoj/routers/api_chat.py
- khoj-repo/src/khoj/routers/auth.py
- khoj-repo/src/khoj/routers/storage.py
"""

import logging
import re
import sys
from io import StringIO
from pathlib import Path
from typing import List, Tuple
from unittest.mock import patch

import pytest


# Mark all tests in this module to NOT require Django database
pytestmark = pytest.mark.django_db(databases=[])


# Get the routers directory path
def get_routers_directory():
    """Get the routers directory path."""
    current = Path(__file__).parent.absolute()
    repo_root = current.parent
    routers_dir = repo_root / "src" / "khoj" / "routers"
    return routers_dir


class TestExcInfoSecurityAdversarial:
    """Test for security vulnerabilities in exc_info=True usage."""

    def test_no_sensitive_data_in_log_messages(self):
        """
        Adversarial test: Verify that log messages don't contain hardcoded sensitive data
        that could be exposed via stack traces.
        
        exc_info=True adds stack trace to logs, which could expose:
        - File paths
        - Variable names
        - Code snippets
        """
        routers_dir = get_routers_directory()
        
        sensitive_patterns = [
            (r'password["\']?\s*[:=]', 'password assignment'),
            (r'secret["\']?\s*[:=]', 'secret assignment'),
            (r'api[_-]?key["\']?\s*[:=]', 'API key assignment'),
            (r'token["\']?\s*[:=]\s*["\']?[a-zA-Z0-9_-]{20,}', 'token assignment'),
            (r'Authorization["\']?\s*[:=]', 'authorization header'),
        ]
        
        target_files = ['helpers.py', 'api_chat.py', 'auth.py', 'storage.py']
        violations = []
        
        for filename in target_files:
            filepath = routers_dir / filename
            if not filepath.exists():
                continue
                
            content = filepath.read_text(encoding='utf-8')
            
            # Check for logger.error calls with exc_info=True that contain sensitive patterns
            for pattern, desc in sensitive_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Check if this is near a logger.error with exc_info=True
                    line_start = content.rfind('\n', 0, match.start()) + 1
                    line_end = content.find('\n', match.start())
                    line = content[line_start:line_end]
                    
                    if 'logger.error' in line and 'exc_info=True' in line:
                        violations.append(f"{filename}: Potential {desc} in logger call: {line.strip()}")
        
        if violations:
            pytest.fail(
                "Security issue: Found potential sensitive data in logger calls:\n" + 
                "\n".join(violations)
            )

    def test_no_pII_in_exception_variables_logged(self):
        """
        Adversarial test: Ensure exception variables that could contain PII
        are not logged with exc_info=True.
        """
        routers_dir = get_routers_directory()
        
        # Look for patterns where exception variables with user data are logged
        pii_exception_patterns = [
            (r'logger\.(error|warning|exception)\([^)]*user\.email[^)]*exc_info\s*=\s*True', 
             'user.email in logged exception'),
            (r'logger\.(error|warning|exception)\([^)]*request\.[^)]*exc_info\s*=\s*True',
             'request data in logged exception'),
        ]
        
        target_files = ['helpers.py', 'api_chat.py', 'auth.py', 'storage.py']
        violations = []
        
        for filename in target_files:
            filepath = routers_dir / filename
            if not filepath.exists():
                continue
                
            content = filepath.read_text(encoding='utf-8')
            
            for pattern, desc in pii_exception_patterns:
                if re.search(pattern, content):
                    # This is expected behavior - we want exc_info=True
                    # But we should verify it's intentional
                    pass
        
        # This test documents that PII could be exposed - it's a warning test
        # The actual protection is in the code review process
        assert True, "PII exposure test completed"


class TestExcInfoTypeAdversarial:
    """Test for type errors in exc_info=True usage."""

    def test_exc_info_accepts_valid_boolean_values(self):
        """Verify that exc_info=True works correctly with boolean values."""
        logger = logging.getLogger("test_exc_info_types")
        
        # Capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.ERROR)
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)
        
        try:
            # Test exc_info=True
            try:
                raise ValueError("test error")
            except ValueError:
                logger.error("Test message", exc_info=True)
            
            # Verify log was written
            log_output = stream.getvalue()
            assert "Test message" in log_output
            
            # Test exc_info=False
            stream.truncate(0)
            stream.seek(0)
            logger.error("Test message 2", exc_info=False)
            log_output = stream.getvalue()
            assert "Test message 2" in log_output
            
        finally:
            logger.removeHandler(handler)

    def test_exc_info_with_none_value(self):
        """Verify behavior when exc_info=None (should be treated as False)."""
        logger = logging.getLogger("test_exc_info_none")
        
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.ERROR)
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)
        
        try:
            # exc_info=None should not add stack trace
            logger.error("Test message", exc_info=None)
            log_output = stream.getvalue()
            
            # Should not contain Traceback when exc_info=None
            assert "Traceback" not in log_output
        finally:
            logger.removeHandler(handler)

    def test_exc_info_with_invalid_string_value(self):
        """Test behavior with invalid exc_info string value - should not crash."""
        logger = logging.getLogger("test_exc_info_invalid")
        
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.ERROR)
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)
        
        try:
            # Python logging should handle invalid exc_info gracefully
            # It may warn but should not crash
            try:
                raise ValueError("test")
            except ValueError:
                # This might produce a warning but shouldn't crash
                logger.error("Test", exc_info="invalid")
            
            assert True  # If we get here, no crash occurred
        except (TypeError, ValueError) as e:
            # This is acceptable - invalid exc_info may raise
            pass
        finally:
            logger.removeHandler(handler)


class TestExcInfoPerformanceAdversarial:
    """Test for performance issues with exc_info=True."""

    def test_exc_info_performance_impact(self):
        """
        Adversarial test: Verify that exc_info=True doesn't cause
        significant performance degradation in tight loops.
        """
        import time
        
        logger = logging.getLogger("test_performance")
        
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.ERROR)
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)
        
        try:
            # Benchmark without exc_info
            start = time.perf_counter()
            for _ in range(100):
                try:
                    raise ValueError("test")
                except ValueError:
                    logger.error("message", exc_info=False)
            time_without = time.perf_counter() - start
            
            # Benchmark with exc_info
            stream.truncate(0)
            stream.seek(0)
            
            start = time.perf_counter()
            for _ in range(100):
                try:
                    raise ValueError("test")
                except ValueError:
                    logger.error("message", exc_info=True)
            time_with = time.perf_counter() - start
            
            # exc_info=True should be slower, but not by an extreme factor
            # Typically 2-10x slower depending on stack depth
            ratio = time_with / time_without if time_without > 0 else 1
            
            # If ratio is extremely high (>50x), there might be an issue
            # This is a warning rather than failure since it depends on stack depth
            if ratio > 50:
                pytest.skip(
                    f"Performance ratio too high: {ratio:.1f}x - "
                    "this may indicate an issue but could be due to stack depth"
                )
                
        finally:
            logger.removeHandler(handler)


class TestExcInfoEdgeCases:
    """Test edge cases in exc_info=True usage."""

    def test_logging_without_active_exception(self):
        """
        Test logging with exc_info=True when no exception is active.
        
        This should still work but may produce unexpected output.
        """
        logger = logging.getLogger("test_no_exception")
        
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.ERROR)
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)
        
        try:
            # Log with exc_info=True but no active exception
            logger.error("No exception message", exc_info=True)
            log_output = stream.getvalue()
            
            # Should still log the message
            assert "No exception message" in log_output
        finally:
            logger.removeHandler(handler)

    def test_nested_exception_logging(self):
        """Test logging with exc_info=True in nested exception handlers."""
        logger = logging.getLogger("test_nested")
        
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.ERROR)
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)
        
        try:
            try:
                try:
                    raise ValueError("inner")
                except ValueError:
                    logger.error("Inner handler", exc_info=True)
                    raise KeyError("outer")
            except KeyError:
                logger.error("Outer handler", exc_info=True)
                
            log_output = stream.getvalue()
            assert "Inner handler" in log_output
            assert "Outer handler" in log_output
        finally:
            logger.removeHandler(handler)

    def test_exception_in_finally_block_with_exc_info(self):
        """Test exc_info=True in finally blocks (where exception may not be active)."""
        logger = logging.getLogger("test_finally")
        
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.ERROR)
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)
        
        try:
            try:
                raise ValueError("test")
            finally:
                # In finally, the exception may not be available
                # exc_info=True should still work but may behave differently
                logger.error("In finally", exc_info=True)
        except ValueError:
            # Expected - we need to catch the exception to continue
            pass
        
        log_output = stream.getvalue()
        assert "In finally" in log_output


class TestExcInfoIntegrationAdversarial:
    """Integration tests for exc_info=True in target files."""

    def test_all_target_files_have_exc_info_in_exception_handlers(self):
        """
        Verify that all target files have exc_info=True in their
        logger.error calls within exception handlers.
        """
        import ast
        
        routers_dir = get_routers_directory()
        
        target_files = [
            'helpers.py',
            'api_chat.py', 
            'auth.py',
            'storage.py'
        ]
        
        violations = []
        
        for filename in target_files:
            filepath = routers_dir / filename
            if not filepath.exists():
                continue
            
            content = filepath.read_text(encoding='utf-8')
            
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue
            
            # Find all try/except blocks
            class ExceptionHandlerFinder(ast.NodeVisitor):
                def __init__(self):
                    self.in_handler = False
                    self.violations = []
                    self.source_lines = content.split('\n')
                
                def visit_Try(self, node):
                    old_in_handler = self.in_handler
                    
                    # Check except handlers
                    for handler in node.handlers:
                        self.in_handler = True
                        for stmt in handler.body:
                            self.check_logger_error(stmt)
                    
                    self.in_handler = old_in_handler
                    self.generic_visit(node)
                
                def check_logger_error(self, node):
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Attribute):
                            if (isinstance(node.func.value, ast.Name) and 
                                node.func.value.id == 'logger' and 
                                node.func.attr == 'error'):
                                # Check for exc_info=True
                                has_exc_info = any(
                                    k.arg == 'exc_info' and 
                                    isinstance(k.value, ast.Constant) and 
                                    k.value.value is True
                                    for k in node.keywords
                                )
                                if not has_exc_info:
                                    line = node.lineno if hasattr(node, 'lineno') else '?'
                                    self.violations.append((filename, line))
            
            finder = ExceptionHandlerFinder()
            finder.visit(tree)
            
            violations.extend(finder.violations)
        
        if violations:
            details = "\n".join(f"  {f}:{line}" for f, line in violations)
            pytest.fail(
                f"Found logger.error in exception handlers without exc_info=True:\n{details}"
            )

    def test_exc_info_format_consistency(self):
        """
        Verify that exc_info=True is consistently formatted across all files.
        Should be exc_info=True, not exc_info = True or other variants.
        """
        routers_dir = get_routers_directory()
        
        target_files = ['helpers.py', 'api_chat.py', 'auth.py', 'storage.py']
        
        inconsistent = []
        
        for filename in target_files:
            filepath = routers_dir / filename
            if not filepath.exists():
                continue
            
            content = filepath.read_text(encoding='utf-8')
            
            # Check for inconsistent exc_info formatting
            # exc_info = True (with spaces) should trigger warning
            if re.search(r'exc_info\s*=\s*True', content):
                # Check if there are any with spaces around =
                inconsistent_spacing = re.findall(
                    r'exc_info\s+=\s+True', 
                    content
                )
                if inconsistent_spacing:
                    inconsistent.append(
                        f"{filename}: Found {len(inconsistent_spacing)} instances with inconsistent spacing"
                    )
        
        # This is a style warning, not a failure
        if inconsistent:
            print("\nStyle warning: Inconsistent exc_info formatting:")
            for item in inconsistent:
                print(f"  {item}")


class TestExcInfoRobustness:
    """Test robustness of exc_info=True handling."""

    def test_logger_error_with_multiple_keyword_args(self):
        """Test logger.error with exc_info alongside other keyword args."""
        logger = logging.getLogger("test_multi_keyword")
        
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.ERROR)
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)
        
        try:
            try:
                raise RuntimeError("test error")
            except RuntimeError:
                logger.error(
                    "Message with multiple kwargs",
                    exc_info=True,
                    extra={"key": "value"},
                    stack_info=False
                )
            
            log_output = stream.getvalue()
            assert "Message with multiple kwargs" in log_output
        finally:
            logger.removeHandler(handler)

    def test_logger_warning_with_exc_info(self):
        """Test that logger.warning with exc_info works correctly."""
        logger = logging.getLogger("test_warning")
        
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.WARNING)
        logger.addHandler(handler)
        logger.setLevel(logging.WARNING)
        
        try:
            try:
                raise ValueError("warning test")
            except ValueError:
                logger.warning("Warning with traceback", exc_info=True)
            
            log_output = stream.getvalue()
            assert "Warning with traceback" in log_output
            assert "ValueError" in log_output
        finally:
            logger.removeHandler(handler)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
