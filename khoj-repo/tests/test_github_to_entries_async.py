"""
Test to verify that github_to_entries.py uses asyncio.sleep instead of time.sleep
in async context. This ensures non-blocking behavior in async functions.
"""
import ast
import inspect
import sys


def test_wait_for_rate_limit_reset_is_async():
    """Test that wait_for_rate_limit_reset is an async function."""
    # Import the module directly without Django dependencies
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "github_to_entries", 
        "khoj-repo/src/khoj/processor/content/github/github_to_entries.py"
    )
    module = importlib.util.module_from_spec(spec)
    
    # Mock the Django/database dependencies before loading
    sys.modules['khoj.database.models'] = type(sys)('khoj.database.models')
    sys.modules['khoj.database.models'].Entry = type('Entry', (), {})
    sys.modules['khoj.database.models'].KhojUser = type('KhojUser', (), {})
    sys.modules['khoj.database.models'].GithubConfig = type('GithubConfig', (), {})
    sys.modules['khoj.processor.content.markdown.markdown_to_entries'] = type(sys)('markdown')
    sys.modules['khoj.processor.content.markdown.markdown_to_entries'].MarkdownToEntries = type('MarkdownToEntries', (), {})
    sys.modules['khoj.processor.content.org_mode.org_to_entries'] = type(sys)('org')
    sys.modules['khoj.processor.content.org_mode.org_to_entries'].OrgToEntries = type('OrgToEntries', (), {})
    sys.modules['khoj.processor.content.plaintext.plaintext_to_entries'] = type(sys)('plaintext')
    sys.modules['khoj.processor.content.plaintext.plaintext_to_entries'].PlaintextToEntries = type('PlaintextToEntries', (), {})
    sys.modules['khoj.processor.content.text_to_entries'] = type(sys)('text_to_entries')
    sys.modules['khoj.processor.content.text_to_entries'].TextToEntries = type('TextToEntries', (), {})
    sys.modules['khoj.utils.helpers'] = type(sys)('helpers')
    sys.modules['khoj.utils.helpers'].is_none_or_empty = lambda x: x is None or (isinstance(x, (list, dict, str)) and len(x) == 0)
    sys.modules['khoj.utils.helpers'].timer = lambda *args, **kwargs: lambda x: x
    sys.modules['khoj.utils.rawconfig'] = type(sys)('rawconfig')
    sys.modules['khoj.utils.rawconfig'].GithubContentConfig = type('GithubContentConfig', (), {})
    sys.modules['khoj.utils.rawconfig'].GithubRepoConfig = type('GithubRepoConfig', (), {})
    
    spec.loader.exec_module(module)
    
    # Get the wait_for_rate_limit_reset method
    method = module.GithubToEntries.wait_for_rate_limit_reset
    
    # Verify it's a coroutine function (async)
    assert inspect.iscoroutinefunction(method), \
        "wait_for_rate_limit_reset should be an async function"
    print("[PASS] wait_for_rate_limit_reset is an async function")


def test_asyncio_sleep_used_not_time_sleep():
    """Test that asyncio.sleep is used, not time.sleep in the async function."""
    # Read the source file directly
    with open("khoj-repo/src/khoj/processor/content/github/github_to_entries.py", "r") as f:
        source = f.read()
    
    # Parse the source to AST
    tree = ast.parse(source)
    
    # Check for time.sleep calls (blocking)
    time_sleep_found = False
    asyncio_sleep_found = False
    
    for node in ast.walk(tree):
        # Check for time.sleep() calls
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                # Check for time.sleep
                if (isinstance(node.func.value, ast.Name) and 
                    node.func.value.id == 'time' and 
                    node.func.attr == 'sleep'):
                    time_sleep_found = True
                # Check for asyncio.sleep
                if (isinstance(node.func.value, ast.Name) and 
                    node.func.value.id == 'asyncio' and 
                    node.func.attr == 'sleep'):
                    asyncio_sleep_found = True
    
    assert not time_sleep_found, \
        "time.sleep (blocking) should not be used in github_to_entries.py"
    assert asyncio_sleep_found, \
        "asyncio.sleep should be used in github_to_entries.py for non-blocking behavior"
    print("[PASS] asyncio.sleep is used, not time.sleep")


def test_no_blocking_sleep_in_async_context():
    """Test that there are no blocking time.sleep calls anywhere in the module."""
    # Read the source file directly
    with open("khoj-repo/src/khoj/processor/content/github/github_to_entries.py", "r") as f:
        source = f.read()
    
    # Verify time.sleep is not imported/used for sleeping
    # time module should only be used for time.time() (non-blocking)
    assert 'time.sleep' not in source, \
        "time.sleep should not be used - it blocks the event loop"
    print("[PASS] No blocking time.sleep calls in the module")


def test_function_signature_and_await():
    """Test that the function properly awaits asyncio.sleep."""
    # Read the source file directly
    with open("khoj-repo/src/khoj/processor/content/github/github_to_entries.py", "r") as f:
        source = f.read()
    
    tree = ast.parse(source)
    
    # Find the wait_for_rate_limit_reset function
    wait_func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == 'wait_for_rate_limit_reset':
            wait_func = node
            break
    
    assert wait_func is not None, "wait_for_rate_limit_reset function not found"
    
    # Check that it uses await asyncio.sleep
    has_await_asyncio_sleep = False
    for node in ast.walk(wait_func):
        if isinstance(node, ast.Await):
            if isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Attribute):
                    if (isinstance(node.value.func.value, ast.Name) and 
                        node.value.func.value.id == 'asyncio' and 
                        node.value.func.attr == 'sleep'):
                        has_await_asyncio_sleep = True
    
    assert has_await_asyncio_sleep, \
        "wait_for_rate_limit_reset should await asyncio.sleep"
    print("[PASS] Function properly awaits asyncio.sleep")


if __name__ == "__main__":
    print("Running tests for asyncio.sleep fix in github_to_entries.py\n")
    print("=" * 60)
    
    test_wait_for_rate_limit_reset_is_async()
    test_asyncio_sleep_used_not_time_sleep()
    test_no_blocking_sleep_in_async_context()
    test_function_signature_and_await()
    
    print("=" * 60)
    print("\n[PASS] All tests PASSED!")
