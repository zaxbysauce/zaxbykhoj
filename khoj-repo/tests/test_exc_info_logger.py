"""
Test that verifies exc_info=True is added to logger.error calls in exception handlers.

This test validates that all logger.error() calls within exception handlers
(try/except blocks) include exc_info=True to properly capture stack traces.

This is a standalone test that does not require database access.
"""
import ast
import re
import sys
from pathlib import Path
from typing import List, Tuple


class ExceptionHandlerVisitor(ast.NodeVisitor):
    """AST visitor to find logger.error calls within exception handlers."""
    
    def __init__(self):
        self.violations: List[Tuple[int, str, str]] = []  # (line_no, code_snippet, context)
        self.file_path = ""
        
    def visit_Try(self, node: ast.Try):
        # Check exception handlers (except blocks)
        for handler in node.handlers:
            # Visit the body of the exception handler
            self._check_node_for_logger_error(handler.body, "except handler")
        
        # Also check the else clause of try block (runs if no exception)
        self._check_node_for_logger_error(node.orelse, "try-else")
        
        # Visit child nodes
        self.generic_visit(node)
    
    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        # Direct visit to exception handler (backup for different AST structure)
        self._check_node_for_logger_error(node.body, "except handler")
        self.generic_visit(node)
    
    def _check_node_for_logger_error(self, nodes: List[ast.stmt], context: str):
        if not nodes:
            return
            
        for node in ast.walk(ast.Module(body=nodes)):
            if isinstance(node, ast.Call):
                # Check if it's a logger.error call
                if self._is_logger_error_call(node):
                    # Check if exc_info=True is present
                    has_exc_info = self._has_exc_info_true(node)
                    if not has_exc_info:
                        # Get the line number from the original node
                        line_no = node.lineno if hasattr(node, 'lineno') else 0
                        # Generate code snippet
                        code_snippet = ast.unparse(node) if hasattr(ast, 'unparse') else ""
                        self.violations.append((line_no, code_snippet, context))
    
    def _is_logger_error_call(self, node: ast.Call) -> bool:
        """Check if the node is a logger.error() call."""
        # Check for logger.error(...)
        if isinstance(node.func, ast.Attribute):
            if (isinstance(node.func.value, ast.Name) and 
                node.func.value.id == 'logger' and 
                node.func.attr == 'error'):
                return True
        return False
    
    def _has_exc_info_true(self, node: ast.Call) -> bool:
        """Check if exc_info=True is passed to the logger.error call."""
        for keyword in node.keywords:
            if keyword.arg == 'exc_info':
                # Check if it's True
                if isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    return True
                elif isinstance(keyword.value, ast.NameConstant) and keyword.value.value is True:
                    return True
        return False


def find_violations_in_file(file_path: str) -> List[Tuple[int, str, str]]:
    """Find all logger.error calls in exception handlers without exc_info=True."""
    with open(file_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return []
    
    visitor = ExceptionHandlerVisitor()
    visitor.file_path = file_path
    visitor.visit(tree)
    
    return visitor.violations


def main():
    """Run the test and exit with appropriate code."""
    base_path = Path("C:/opencode/khoj/khoj-repo/src/khoj")
    
    files = [
        base_path / "processor/content/github/github_to_entries.py",
        base_path / "routers/search_helpers.py",
        base_path / "routers/helpers.py",
        base_path / "routers/vector_helpers.py",
        base_path / "routers/api_chat.py",
        base_path / "routers/auth.py",
        base_path / "routers/storage.py",
    ]
    
    all_violations = {}
    has_errors = False
    
    print("Testing exc_info=True in logger.error calls within exception handlers...")
    print("=" * 80)
    
    for file_path in files:
        if not file_path.exists():
            print(f"WARNING: File not found: {file_path}")
            continue
            
        violations = find_violations_in_file(str(file_path))
        
        # Filter out false positives - only keep actual logger.error calls
        real_violations = [
            v for v in violations 
            if 'logger.error' in v[1].lower()
        ]
        
        if real_violations:
            has_errors = True
            all_violations[str(file_path)] = real_violations
            print(f"\nFAILED: {file_path.name}")
            for v in real_violations:
                print(f"  Line {v[0]}: {v[1][:80]}... (context: {v[2]})")
        else:
            print(f"\nPASSED: {file_path.name}")
    
    print("\n" + "=" * 80)
    
    # Also check specific patterns for the files
    print("\nVerifying specific logger.error patterns with exc_info=True...")
    print("-" * 40)
    
    # Check github_to_entries.py
    gh_file = base_path / "processor/content/github/github_to_entries.py"
    with open(gh_file, 'r', encoding='utf-8') as f:
        gh_content = f.read()
    
    gh_patterns = [
        (r'logger\.error\([^)]*Github rate limit[^)]*exc_info\s*=\s*True', "Github rate limit error"),
        (r'logger\.error\([^)]*Unable to download github repo[^)]*exc_info\s*=\s*True', "Download error"),
        (r'logger\.error\([^)]*Unable to identify content type[^)]*exc_info\s*=\s*True', "Identify content type"),
        (r'logger\.error\([^)]*Unable to decode content[^)]*exc_info\s*=\s*True', "Decode content"),
        (r'logger\.error\([^)]*Unable to decode chunk[^)]*exc_info\s*=\s*True', "Decode chunk"),
    ]
    
    for pattern, desc in gh_patterns:
        if re.search(pattern, gh_content):
            print(f"PASSED: {desc} in github_to_entries.py")
        else:
            print(f"FAILED: {desc} NOT FOUND in github_to_entries.py")
            has_errors = True
    
    # Check search_helpers.py
    sh_file = base_path / "routers/search_helpers.py"
    with open(sh_file, 'r', encoding='utf-8') as f:
        sh_content = f.read()
    
    sh_patterns = [
        (r'logger\.error\([^)]*Conversation with id[^)]*exc_info\s*=\s*True', "Conversation not found"),
        (r'logger\.error\([^)]*Invalid response for constructing subqueries[^)]*exc_info\s*=\s*True', "Invalid subqueries"),
        (r'logger\.error\([^)]*Agent.*is not accessible[^)]*exc_info\s*=\s*True', "Agent not accessible"),
    ]
    
    for pattern, desc in sh_patterns:
        if re.search(pattern, sh_content):
            print(f"PASSED: {desc} in search_helpers.py")
        else:
            print(f"FAILED: {desc} NOT FOUND in search_helpers.py")
            has_errors = True
    
    # Check grep_files exception handler
    if re.search(r'logger\.error\(error_msg,\s*exc_info\s*=\s*True\)', sh_content):
        print("PASSED: grep_files exception handler in search_helpers.py")
    else:
        print("FAILED: grep_files exception handler NOT FOUND in search_helpers.py")
        has_errors = True
    
    # Check list_files exception handler (appears twice in search_helpers.py)
    list_files_count = len(re.findall(r'logger\.error\(error_msg,\s*exc_info\s*=\s*True\)', sh_content))
    if list_files_count >= 2:
        print(f"PASSED: list_files exception handlers in search_helpers.py ({list_files_count} found)")
    else:
        print(f"FAILED: list_files exception handlers NOT FOUND (found {list_files_count}, expected 2)")
        has_errors = True
    
    # Check vector_helpers.py
    vh_file = base_path / "routers/vector_helpers.py"
    with open(vh_file, 'r', encoding='utf-8') as f:
        vh_content = f.read()
    
    vh_patterns = [
        (r'logger\.error\([^)]*Conversation with id[^)]*exc_info\s*=\s*True', "Conversation not found"),
        (r'logger\.error\([^)]*Agent.*is not accessible[^)]*exc_info\s*=\s*True', "Agent not accessible"),
        (r'logger\.error\([^)]*Invalid response for constructing subqueries[^)]*exc_info\s*=\s*True', "Invalid subqueries"),
    ]
    
    for pattern, desc in vh_patterns:
        if re.search(pattern, vh_content):
            print(f"PASSED: {desc} in vector_helpers.py")
        else:
            print(f"FAILED: {desc} NOT FOUND in vector_helpers.py")
            has_errors = True
    
    # Check helpers.py for specific patterns
    hl_file = base_path / "routers/helpers.py"
    with open(hl_file, 'r', encoding='utf-8') as f:
        hl_content = f.read()
    
    hl_patterns = [
        (r'logger\.error\([^)]*Invalid response for checking safe prompt[^)]*exc_info\s*=\s*True', "Safe prompt check"),
        (r'logger\.error\([^)]*Invalid response for determining relevant tools[^)]*exc_info\s*=\s*True', "Relevant tools"),
        (r'logger\.error\([^)]*Error summarizing file[^)]*exc_info\s*=\s*True', "Summarize file"),
        (r'logger\.error\([^)]*Error generating Excalidraw diagram[^)]*exc_info\s*=\s*True', "Excalidraw diagram"),
    ]
    
    for pattern, desc in hl_patterns:
        if re.search(pattern, hl_content):
            print(f"PASSED: {desc} in helpers.py")
        else:
            print(f"FAILED: {desc} NOT FOUND in helpers.py")
            has_errors = True

    # Check api_chat.py for specific patterns
    ac_file = base_path / "routers/api_chat.py"
    with open(ac_file, 'r', encoding='utf-8') as f:
        ac_content = f.read()
    
    ac_patterns = [
        (r'logger\.error\([^)]*Error adding file filter[^)]*exc_info\s*=\s*True', "File filter error"),
        (r'logger\.error\([^)]*Error in disconnect monitor[^)]*exc_info\s*=\s*True', "Disconnect monitor error"),
        (r'logger\.error\([^)]*Failed to stream chat API response[^)]*exc_info\s*=\s*True', "Stream chat API response"),
        (r'logger\.error\([^)]*Error getting data sources and output format[^)]*exc_info\s*=\s*True', "Data sources and output format"),
        (r'logger\.error\(error_message,\s*exc_info\s*=\s*True', "Search knowledge base"),  # uses variable error_message
        (r'logger\.warning\([^)]*Error reading webpages[^)]*exc_info\s*=\s*True', "Read webpages (warning)"),
        (r'logger\.warning\([^)]*Failed to use code tool[^)]*exc_info\s*=\s*True', "Code tool (warning)"),
    ]
    
    for pattern, desc in ac_patterns:
        if re.search(pattern, ac_content):
            print(f"PASSED: {desc} in api_chat.py")
        else:
            print(f"FAILED: {desc} NOT FOUND in api_chat.py")
            has_errors = True

    # Check auth.py for specific patterns
    auth_file = base_path / "routers/auth.py"
    with open(auth_file, 'r', encoding='utf-8') as f:
        auth_content = f.read()
    
    auth_patterns = [
        (r'logger\.error\([^)]*Token request failed[^)]*exc_info\s*=\s*True', "Token request failed"),
        (r'logger\.error\([^)]*Error response JSON for Google verification[^)]*exc_info\s*=\s*True', "Google verification JSON"),
        (r'logger\.error\([^)]*Response content is not valid JSON[^)]*exc_info\s*=\s*True', "Invalid JSON response"),
        (r'logger\.error\([^)]*Missing id_token in OAuth response[^)]*exc_info\s*=\s*True', "Missing id_token"),
    ]
    
    for pattern, desc in auth_patterns:
        if re.search(pattern, auth_content):
            print(f"PASSED: {desc} in auth.py")
        else:
            print(f"FAILED: {desc} NOT FOUND in auth.py")
            has_errors = True

    # Check storage.py for specific patterns
    storage_file = base_path / "routers/storage.py"
    with open(storage_file, 'r', encoding='utf-8') as f:
        storage_content = f.read()
    
    storage_patterns = [
        (r'logger\.error\([^)]*Failed to upload image to S3[^)]*exc_info\s*=\s*True', "S3 upload error"),
    ]
    
    for pattern, desc in storage_patterns:
        if re.search(pattern, storage_content):
            print(f"PASSED: {desc} in storage.py")
        else:
            print(f"FAILED: {desc} NOT FOUND in storage.py")
            has_errors = True
    
    print("\n" + "=" * 80)
    
    if has_errors:
        print("RESULT: FAIL - Some tests failed")
        sys.exit(1)
    else:
        print("RESULT: PASS - All tests passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
