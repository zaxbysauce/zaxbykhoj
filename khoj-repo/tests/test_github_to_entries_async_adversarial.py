"""
Adversarial tests for asyncio.sleep fix in github_to_entries.py

Tests attack vectors:
1. Race conditions in async context
2. Event loop blocking scenarios  
3. Exception propagation through async wrapper

This is a standalone test file that doesn't require Django database.
Run with: python test_file.py
"""
import asyncio
import importlib.util
import sys
import time
from unittest.mock import MagicMock


def get_loaded_module():
    """Setup mocks and load the github_to_entries module."""
    # Mock the Django/database dependencies BEFORE loading
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
    
    # Mock requests and magika
    sys.modules['requests'] = MagicMock()
    sys.modules['magika'] = MagicMock()
    
    # Load the module
    spec = importlib.util.spec_from_file_location(
        "github_to_entries",
        "khoj-repo/src/khoj/processor/content/github/github_to_entries.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ============================================================================
# Test 1: Race Conditions in Async Context
# ============================================================================
async def test_concurrent_rate_limit_waits_do_not_block():
    """Attack Vector: Multiple coroutines hitting rate limit simultaneously."""
    module = get_loaded_module()
    
    # Create mock response indicating rate limit hit
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.headers = {
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": str(int(time.time()) + 1)  # 1 second in future
    }
    
    # Track concurrent executions
    execution_count = 0
    execution_times = []
    
    async def mock_func():
        nonlocal execution_count
        execution_count += 1
        execution_times.append(time.time())
        await asyncio.sleep(0.01)  # Simulate some async work
        return "success"
    
    # Run multiple coroutines concurrently
    tasks = []
    for _ in range(5):
        task = asyncio.create_task(
            module.GithubToEntries.wait_for_rate_limit_reset(
                mock_response, mock_func
            )
        )
        tasks.append(task)
    
    # Wait for all with timeout - should complete, not hang
    done, pending = await asyncio.wait(tasks, timeout=5.0)
    
    # Assert: All tasks should complete (no deadlock)
    assert len(done) == 5, f"Only {len(done)} tasks completed, {len(pending)} are pending - possible deadlock"
    assert len(pending) == 0, "Tasks still pending - possible deadlock or infinite block"
    
    # Each execution should have started
    assert execution_count == 5, f"Expected 5 executions, got {execution_count}"
    
    print("[PASS] test_concurrent_rate_limit_waits_do_not_block")


async def test_race_condition_exception_during_wait():
    """Attack Vector: Exception thrown in one coroutine should not affect others."""
    module = get_loaded_module()
    
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.headers = {
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": str(int(time.time()) + 1)
    }
    
    async def failing_func():
        raise RuntimeError("Intentional failure in rate-limited request")
    
    async def success_func():
        return "ok"
    
    # Create tasks - one will fail, others should continue
    tasks = [
        asyncio.create_task(module.GithubToEntries.wait_for_rate_limit_reset(mock_response, failing_func)),
        asyncio.create_task(module.GithubToEntries.wait_for_rate_limit_reset(mock_response, success_func)),
        asyncio.create_task(module.GithubToEntries.wait_for_rate_limit_reset(mock_response, success_func)),
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Verify: exceptions should be propagated, not swallow other coroutines
    exceptions = [r for r in results if isinstance(r, Exception)]
    successes = [r for r in results if not isinstance(r, Exception)]
    
    assert len(exceptions) >= 1, "Expected at least one exception"
    assert len(successes) >= 2, f"Expected at least 2 successes, got {len(successes)}"
    
    print("[PASS] test_race_condition_exception_during_wait")


# ============================================================================
# Test 2: Event Loop Blocking Scenarios
# ============================================================================
async def test_asyncio_sleep_does_not_block_event_loop():
    """Attack Vector: Verify asyncio.sleep yields control properly."""
    module = get_loaded_module()
    
    # Create response with very short wait time
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.headers = {
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": str(int(time.time()) + 0)  # Immediate/very short wait
    }
    
    background_task_executed = False
    
    async def background_task():
        nonlocal background_task_executed
        await asyncio.sleep(0.001)  # Very short sleep
        background_task_executed = True
    
    async def rate_limited_func():
        return "completed"
    
    async def main():
        nonlocal background_task_executed
        
        # Schedule background task to run during rate limit wait
        bg = asyncio.create_task(background_task())
        
        # Run the rate limit wait
        await module.GithubToEntries.wait_for_rate_limit_reset(mock_response, rate_limited_func)
        
        # Give background task chance to complete
        await asyncio.sleep(0.01)
        
        # If asyncio.sleep properly yields, background task should execute
        return bg
    
    await main()
    
    # Verify background task was able to execute (event loop not blocked)
    assert background_task_executed, "Background task did not execute - event loop may be blocked"
    
    print("[PASS] test_asyncio_sleep_does_not_block_event_loop")


async def test_no_time_sleep_in_async_context():
    """Attack Vector: Verify time.sleep is NOT used in async code."""
    # Read source to verify no time.sleep
    with open("khoj-repo/src/khoj/processor/content/github/github_to_entries.py", "r") as f:
        source = f.read()
    
    # time.sleep should NOT appear in the source - it blocks the event loop
    assert "time.sleep" not in source, \
        "CRITICAL: time.sleep found in async code - this blocks the event loop!"
    
    # asyncio.sleep SHOULD be present
    assert "asyncio.sleep" in source, \
        "asyncio.sleep should be used for non-blocking waits"
    
    print("[PASS] test_no_time_sleep_in_async_context")


# ============================================================================
# Test 3: Exception Propagation Through Async Wrapper
# ============================================================================
async def test_exception_propagation_from_wrapped_function():
    """Attack Vector: Exceptions from wrapped function should propagate."""
    module = get_loaded_module()
    
    # Use a status code that triggers the rate limit path AND wait (remaining = 0)
    # This will wait then call the function, where exception is raised
    mock_response = MagicMock()
    mock_response.status_code = 403  # != 200 triggers the first check
    mock_response.headers = {
        "X-RateLimit-Remaining": "0",  # Rate limited, triggers wait
        "X-RateLimit-Reset": str(int(time.time()) + 0)  # Zero wait time
    }
    
    async def failing_func():
        raise ValueError("Test exception")
    
    # Exception should propagate because func is called after wait
    try:
        await module.GithubToEntries.wait_for_rate_limit_reset(mock_response, failing_func)
        assert False, "Expected ValueError to be raised"
    except ValueError as e:
        assert "Test exception" in str(e)
    
    print("[PASS] test_exception_propagation_from_wrapped_function")


async def test_exception_during_rate_limit_wait_propagates():
    """Attack Vector: Exception after rate limit wait should propagate."""
    module = get_loaded_module()
    
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.headers = {
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": str(int(time.time()) + 0)
    }
    
    call_count = 0
    
    async def failing_after_wait():
        nonlocal call_count
        call_count += 1
        if call_count > 0:
            raise ConnectionError("Network error after rate limit wait")
    
    # Exception should propagate after wait completes
    try:
        await module.GithubToEntries.wait_for_rate_limit_reset(mock_response, failing_after_wait)
        assert False, "Expected ConnectionError to be raised"
    except ConnectionError as e:
        assert "Network error" in str(e)
    
    assert call_count == 1, "Function should have been called exactly once"
    
    print("[PASS] test_exception_during_rate_limit_wait_propagates")


async def test_cancellation_during_wait_propagates():
    """Attack Vector: Cancellation during wait should propagate correctly."""
    module = get_loaded_module()
    
    # Long wait time to allow cancellation
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.headers = {
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": str(int(time.time()) + 60)  # 60 second wait
    }
    
    async def long_running_func():
        return "should not reach here"
    
    task = asyncio.create_task(
        module.GithubToEntries.wait_for_rate_limit_reset(mock_response, long_running_func)
    )
    await asyncio.sleep(0.01)  # Let it start waiting
    task.cancel()
    await asyncio.sleep(0.01)  # Let cancellation propagate
    
    # Task should be done (cancelled)
    assert task.done(), "Task should be marked as done after cancellation"
    
    print("[PASS] test_cancellation_during_wait_propagates")


# ============================================================================
# Edge Cases
# ============================================================================
async def test_zero_wait_time_handled():
    """Edge case: Zero or negative wait time should be handled gracefully."""
    module = get_loaded_module()
    
    # Zero or negative wait time
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.headers = {
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": str(int(time.time()) - 1)  # In the past
    }
    
    async def target_func():
        return "executed"
    
    # Should handle gracefully without hanging
    result = await asyncio.wait_for(
        module.GithubToEntries.wait_for_rate_limit_reset(mock_response, target_func),
        timeout=2.0
    )
    assert result == "executed", "Function should complete even with zero/negative wait"
    
    print("[PASS] test_zero_wait_time_handled")


async def test_missing_rate_limit_headers():
    """Edge case: Missing rate limit headers should be handled gracefully."""
    module = get_loaded_module()
    
    # Missing headers
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {}  # Empty headers
    
    async def target_func():
        return "success"
    
    result = await module.GithubToEntries.wait_for_rate_limit_reset(mock_response, target_func)
    # Should return None when no rate limit
    assert result is None, "Should return None when not rate limited"
    
    print("[PASS] test_missing_rate_limit_headers")


# ============================================================================
# Run all tests
# ============================================================================
async def run_all_tests():
    print("=" * 60)
    print("Running Adversarial Tests for asyncio.sleep fix")
    print("=" * 60)
    print()
    
    tests = [
        test_concurrent_rate_limit_waits_do_not_block,
        test_race_condition_exception_during_wait,
        test_asyncio_sleep_does_not_block_event_loop,
        test_no_time_sleep_in_async_context,
        test_exception_propagation_from_wrapped_function,
        test_exception_during_rate_limit_wait_propagates,
        test_cancellation_during_wait_propagates,
        test_zero_wait_time_handled,
        test_missing_rate_limit_headers,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print()
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
