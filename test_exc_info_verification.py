"""
Test to verify exc_info=True is present in all logger.error calls in EXCEPTION HANDLERS
in the specified files: helpers.py, api_chat.py, auth.py, storage.py
"""
import ast
import pytest


# Files to check - as specified in the task
FILES = [
    "khoj-repo/src/khoj/routers/helpers.py",
    "khoj-repo/src/khoj/routers/api_chat.py",
    "khoj-repo/src/khoj/routers/auth.py",
    "khoj-repo/src/khoj/routers/storage.py",
]


def get_all_linenos(node):
    """Recursively get all line numbers from an AST node."""
    linenos = set()
    if hasattr(node, 'lineno'):
        linenos.add(node.lineno)
    for child in ast.iter_child_nodes(node):
        linenos.update(get_all_linenos(child))
    return linenos


class ExceptionHandlerVisitor(ast.NodeVisitor):
    """AST visitor to find logger.error calls in exception handlers."""
    
    def __init__(self):
        self.exception_handler_lines = set()
        self.logger_errors_in_handlers = []
        self.logger_errors_without_exc_info = []
    
    def visit_Try(self, node) -> None:
        """Process try-except blocks."""
        # Get all line numbers in the try-except block
        all_lines = get_all_linenos(node)
        
        # Add all lines to exception handler lines
        for line in all_lines:
            self.exception_handler_lines.add(line)
        
        # Continue visiting child nodes
        self.generic_visit(node)
    
    def visit_Call(self, node) -> None:
        """Find logger.error calls."""
        if not hasattr(node, 'lineno'):
            self.generic_visit(node)
            return
            
        if node.lineno in self.exception_handler_lines:
            # Check if this is a logger.error call
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == 'error':
                    if isinstance(node.func.value, ast.Name):
                        if node.func.value.id == 'logger':
                            # This is a logger.error call in an exception handler
                            # Check if exc_info=True is present
                            has_exc_info = False
                            for kw in node.keywords:
                                if kw.arg == 'exc_info':
                                    if isinstance(kw.value, ast.Constant) and kw.value.value is True:
                                        has_exc_info = True
                                    elif hasattr(kw.value, 'id') and kw.value.id == 'True':
                                        has_exc_info = True
                            
                            if has_exc_info:
                                self.logger_errors_in_handlers.append(node.lineno)
                            else:
                                self.logger_errors_without_exc_info.append(node.lineno)
        
        self.generic_visit(node)


def analyze_file(file_path: str) -> dict:
    """Analyze a single file for logger.error calls in exception handlers."""
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    try:
        tree = ast.parse(content, filename=file_path)
    except SyntaxError:
        return {'error': 'Syntax error in file'}
    
    visitor = ExceptionHandlerVisitor()
    visitor.visit(tree)
    
    return {
        'in_handlers_with_exc_info': visitor.logger_errors_in_handlers,
        'in_handlers_without_exc_info': visitor.logger_errors_without_exc_info,
        'all_handler_lines': visitor.exception_handler_lines,
    }


def test_exc_info_in_exception_handlers():
    """
    Verify exc_info=True is present in all logger.error calls that are 
    within exception handlers in the specified files.
    """
    all_results = {}
    failures = []
    successes = []
    
    for file_path in FILES:
        result = analyze_file(file_path)
        
        if 'error' in result:
            failures.append(f"{file_path}: {result['error']}")
            continue
        
        with_exc_info = result['in_handlers_with_exc_info']
        without_exc_info = result['in_handlers_without_exc_info']
        
        all_results[file_path] = result
        
        if without_exc_info:
            for line in without_exc_info:
                failures.append(f"{file_path}:{line} - Missing exc_info=True")
        else:
            if with_exc_info:
                successes.append(f"{file_path}: {len(with_exc_info)} logger.error calls in exception handlers, all have exc_info=True")
            else:
                successes.append(f"{file_path}: No logger.error calls in exception handlers found")
    
    # Print results for visibility
    print("\n" + "="*70)
    print("LOGGER.ERROR EXC_INFO VERIFICATION RESULTS")
    print("="*70)
    
    print("\nPASSED:")
    for s in successes:
        print(f"  {s}")
    
    if failures:
        print("\nFAILED:")
        for f in failures:
            print(f"  {f}")
        
        # Show details
        print("\nDetails:")
        for file_path, result in all_results.items():
            if result.get('in_handlers_without_exc_info'):
                print(f"\n  {file_path}:")
                for line in result['in_handlers_without_exc_info']:
                    print(f"    Line {line}: Missing exc_info=True")
        
        pytest.fail(f"\n\nFound {len(failures)} issues with logger.error in exception handlers")
    
    print("\n" + "="*70)
    total_with_exc_info = sum(len(r['in_handlers_with_exc_info']) for r in all_results.values() if 'error' not in r)
    print(f"RESULT: All {total_with_exc_info} logger.error calls in exception handlers have exc_info=True")
    print("="*70)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
