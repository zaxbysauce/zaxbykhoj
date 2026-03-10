"""
Test that verifies all logger.error calls in exception handlers have exc_info=True.

This test parses Python source files to find logger.error calls within exception
handlers (try/except/finally blocks) and verifies they include exc_info=True.
"""

import ast
import sys
from pathlib import Path

import pytest


# Mark all tests in this module to not require Django database
pytestmark = pytest.mark.django_db(databases=[])


class ExceptionHandlerVisitor(ast.NodeVisitor):
    """AST visitor to find logger.error calls in exception handlers."""

    def __init__(self, source_lines):
        self.source_lines = source_lines
        self.violations = []
        self._in_exception_handler = False

    def visit_Try(self, node):
        # Check if we're inside an exception handler
        old_in_handler = self._in_exception_handler

        # Check try body
        self._in_exception_handler = True
        for child in node.body:
            self.visit(child)

        # Check except handlers
        for handler in node.handlers:
            self._in_exception_handler = True
            for child in handler.body:
                self.visit(child)

        # Check else body (runs if no exception)
        self._in_exception_handler = True
        for child in node.orelse:
            self.visit(child)

        # Check finally body
        self._in_exception_handler = False  # Finally runs regardless of exception
        for child in node.finalbody:
            self.visit(child)

        self._in_exception_handler = old_in_handler
        # Don't call generic_visit here as we've already visited all children

    def visit_ExceptHandler(self, node):
        """Visit exception handler."""
        old_in_handler = self._in_exception_handler
        self._in_exception_handler = True
        for child in node.body:
            self.visit(child)
        self._in_exception_handler = old_in_handler
        # Don't call generic_visit here as we've already visited all children

    def visit_Call(self, node):
        """Find logger.error calls."""
        # Check if this is a logger.error call
        is_logger_error = False

        # Check for logger.error(...)
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "error":
                # Check if the attribute is on a logger object
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "logger":
                    is_logger_error = True

        if is_logger_error and self._in_exception_handler:
            # Check if exc_info=True is present in the call
            has_exc_info = False
            for keyword in node.keywords:
                if keyword.arg == "exc_info":
                    # Check if exc_info is set to True
                    if isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                        has_exc_info = True
                    elif isinstance(keyword.value, ast.NameConstant) and keyword.value.value is True:  # Python 3.7 compat
                        has_exc_info = True

            if not has_exc_info:
                # Get line number for error reporting
                line_no = node.lineno
                # Get the source line
                source_line = ""
                if line_no and 0 < line_no <= len(self.source_lines):
                    source_line = self.source_lines[line_no - 1].strip()

                self.violations.append({
                    "line": line_no,
                    "source": source_line,
                    "file": "unknown"
                })

        self.generic_visit(node)


def find_violations_in_file(file_path):
    """Find all logger.error calls in exception handlers without exc_info=True."""
    try:
        source_code = file_path.read_text(encoding='utf-8')
    except (UnicodeDecodeError, OSError):
        return []

    try:
        tree = ast.parse(source_code, filename=str(file_path))
    except SyntaxError:
        return []

    source_lines = source_code.split('\n')
    visitor = ExceptionHandlerVisitor(source_lines)
    visitor.visit(tree)

    # Add file path to violations
    for v in visitor.violations:
        v['file'] = str(file_path)

    return visitor.violations


def get_routers_directory():
    """Get the routers directory path."""
    # Navigate from tests directory to src/khoj/routers
    # Path structure: <repo_root>/tests/test_logger_exc_info.py
    current = Path(__file__).parent.absolute()
    # Go up one level to repo root (from tests/ to project root)
    repo_root = current.parent
    routers_dir = repo_root / "src" / "khoj" / "routers"
    return routers_dir


def test_helpers_py_logger_error_in_exceptions():
    """Test that logger.error in exception handlers in helpers.py have exc_info=True."""
    routers_dir = get_routers_directory()
    helpers_file = routers_dir / "helpers.py"

    assert helpers_file.exists(), f"helpers.py not found at {helpers_file}"

    violations = find_violations_in_file(helpers_file)
    
    # Filter to only violations in helpers.py
    helpers_violations = [v for v in violations if 'helpers.py' in v['file']]

    if helpers_violations:
        violation_details = "\n".join(
            f"  Line {v['line']}: {v['source']}"
            for v in helpers_violations
        )
        raise AssertionError(
            f"Found {len(helpers_violations)} logger.error call(s) in exception handlers "
            f"without exc_info=True in helpers.py:\n{violation_details}"
        )


def test_api_chat_py_logger_error_in_exceptions():
    """Test that logger.error in exception handlers in api_chat.py have exc_info=True."""
    routers_dir = get_routers_directory()
    api_chat_file = routers_dir / "api_chat.py"

    assert api_chat_file.exists(), f"api_chat.py not found at {api_chat_file}"

    violations = find_violations_in_file(api_chat_file)
    
    # Filter to only violations in api_chat.py
    api_chat_violations = [v for v in violations if 'api_chat.py' in v['file']]

    if api_chat_violations:
        violation_details = "\n".join(
            f"  Line {v['line']}: {v['source']}"
            for v in api_chat_violations
        )
        raise AssertionError(
            f"Found {len(api_chat_violations)} logger.error call(s) in exception handlers "
            f"without exc_info=True in api_chat.py:\n{violation_details}"
        )


def test_storage_py_logger_error_in_exceptions():
    """Test that logger.error in exception handlers in storage.py have exc_info=True."""
    routers_dir = get_routers_directory()
    storage_file = routers_dir / "storage.py"

    assert storage_file.exists(), f"storage.py not found at {storage_file}"

    violations = find_violations_in_file(storage_file)
    
    # Filter to only violations in storage.py
    storage_violations = [v for v in violations if 'storage.py' in v['file']]

    if storage_violations:
        violation_details = "\n".join(
            f"  Line {v['line']}: {v['source']}"
            for v in storage_violations
        )
        raise AssertionError(
            f"Found {len(storage_violations)} logger.error call(s) in exception handlers "
            f"without exc_info=True in storage.py:\n{violation_details}"
        )


def test_all_routers_files_logger_error_in_exceptions():
    """Test that all logger.error calls in exception handlers in routers have exc_info=True."""
    routers_dir = get_routers_directory()

    assert routers_dir.exists(), f"routers directory not found at {routers_dir}"

    all_violations = []

    # Test ALL files in routers directory
    routers_dir = get_routers_directory()

    all_violations = []

    # Find all Python files in routers directory
    for py_file in routers_dir.glob("*.py"):
        violations = find_violations_in_file(py_file)
        all_violations.extend(violations)

    if all_violations:
        # Group violations by file
        by_file = {}
        for v in all_violations:
            file_name = v['file']
            if file_name not in by_file:
                by_file[file_name] = []
            by_file[file_name].append(v)

        violation_details = []
        for file_name, file_violations in by_file.items():
            file_violation_details = "\n".join(
                f"    Line {v['line']}: {v['source']}"
                for v in file_violations
            )
            violation_details.append(
                f"  {file_name}:\n{file_violation_details}"
            )

        raise AssertionError(
            f"Found {len(all_violations)} total logger.error call(s) in exception handlers "
            f"without exc_info=True:\n" + "\n".join(violation_details)
        )


if __name__ == "__main__":
    # Allow running directly for debugging
    routers_dir = get_routers_directory()

    all_violations = []
    # Test ALL files in routers directory
    for py_file in routers_dir.glob("*.py"):
        violations = find_violations_in_file(py_file)
        all_violations.extend(violations)
        if violations:
            print(f'\n=== Violations in {py_file.name} ===')
            for v in violations:
                print(f'  Line {v["line"]}: {v["source"]}')

    if all_violations:
        print(f'\n\n=== TOTAL: {len(all_violations)} violations found ===')
        sys.exit(1)
    else:
        print('\n\n=== All logger.error calls in exception handlers have exc_info=True ===')
        sys.exit(0)
