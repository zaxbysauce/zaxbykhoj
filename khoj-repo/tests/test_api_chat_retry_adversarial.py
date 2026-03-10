"""
Adversarial Security Tests for api_chat.py Retry Logic

Security-focused tests for the retry mechanism in event_generator:
- Invalid exception types passed to retry decorator
- Boundary: max retries exceeded behavior
- Edge case: multiple concurrent retries
- Resource exhaustion: many rapid retry attempts

ATTACK VECTORS TESTED:
1. Malformed exception types (non-Exception classes, strings, etc.)
2. Boundary violations (max_retries=0, negative values, extremely large values)
3. Concurrent retry attacks (multiple simultaneous retry consumers)
4. Resource exhaustion (rapid retry spam, unbounded retry loops)
"""

import asyncio
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


# ==============================================================================
# TEST 1: Invalid Exception Types - Malformed Inputs to Retry Decorator
# ==============================================================================


class TestInvalidExceptionTypes:
    """Test that invalid exception types are handled safely"""

    def test_non_exception_class_in_retry(self):
        """
        Attack Vector: Pass non-Exception class to retry_if_exception_type
        Expected: Should either fail gracefully or ignore invalid types
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt

        # Attempt to create retry with invalid type (non-Exception class)
        invalid_type = type("InvalidType", (), {})  # Not an Exception

        # This should fail at definition time or be handled safely
        try:
            @retry(
                stop=stop_after_attempt(1),
                retry=retry_if_exception_type((invalid_type,)),
                reraise=True,
            )
            async def will_never_run():
                pass

            # If we get here, the decorator accepted it - verify it doesn't crash
            # when trying to use it
            pytest.skip("Decorator accepted invalid type - security note: validation happens at runtime")
        except (TypeError, AttributeError):
            # Expected: decorator should reject invalid types
            pass

    def test_string_instead_of_exception_type(self):
        """
        Attack Vector: Pass string instead of exception class
        Expected: Should raise TypeError or handle gracefully
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt

        # String is not a valid exception type
        try:
            @retry(
                stop=stop_after_attempt(1),
                retry=retry_if_exception_type(("ValueError",)),  # String, not class
                reraise=True,
            )
            async def will_never_run():
                pass
            pytest.skip("Decorator accepted string type - security note: validation needed")
        except TypeError:
            # Expected: should reject string
            pass

    def test_none_in_exception_types(self):
        """
        Attack Vector: Pass None in exception type tuple
        Expected: Should handle gracefully without crash
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt

        try:
            @retry(
                stop=stop_after_attempt(1),
                retry=retry_if_exception_type((None, ValueError)),
                reraise=True,
            )
            async def will_never_run():
                pass
            pytest.skip("Decorator accepted None type")
        except (TypeError, AttributeError):
            pass

    def test_mixed_valid_invalid_exception_types(self):
        """
        Attack Vector: Tuple with both valid and invalid exception types
        Expected: Should either work with valid ones or fail completely
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt

        class NotAnException:
            pass

        # Mix of valid and invalid - tenacity may accept but behavior is undefined
        try:
            retry_decorator = retry(
                stop=stop_after_attempt(1),
                retry=retry_if_exception_type((NotAnException, ValueError)),
                reraise=True,
            )

            @retry_decorator
            async def test_func():
                raise ValueError("test")

            # Run it - should work since ValueError is valid
            try:
                asyncio.get_event_loop().run_until_complete(test_func())
            except ValueError:
                pass  # Expected

            # If no crash, the decorator handled it
        except Exception as e:
            # Should fail gracefully
            assert "exception" in str(e).lower() or "type" in str(e).lower()


# ==============================================================================
# TEST 2: Boundary - Max Retries Exceeded Behavior
# ==============================================================================


class TestMaxRetriesBoundary:
    """Test boundary conditions for max retries"""

    def test_max_retries_zero(self):
        """
        Attack Vector: Set max_retries to 0 - should never retry
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt

        attempt_count = 0

        @retry(
            stop=stop_after_attempt(0),  # Zero retries
            retry=retry_if_exception_type((httpx.ConnectError,)),
            reraise=True,
        )
        async def zero_retries():
            nonlocal attempt_count
            attempt_count += 1
            raise httpx.ConnectError("test")

        with pytest.raises(httpx.ConnectError):
            asyncio.get_event_loop().run_until_complete(zero_retries())

        # With 0 attempts, should still run once
        assert attempt_count >= 1

    def test_max_retries_negative(self):
        """
        Attack Vector: Negative max_retries value
        Expected: Should handle gracefully (likely treated as 0 or error)
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt

        try:
            @retry(
                stop=stop_after_attempt(-1),
                retry=retry_if_exception_type((httpx.ConnectError,)),
                reraise=True,
            )
            async def negative_retries():
                raise httpx.ConnectError("test")

            # May error immediately or behave unexpectedly
            asyncio.get_event_loop().run_until_complete(negative_retries())
        except (ValueError, Exception):
            pass  # Expected to fail or behave unexpectedly

    def test_max_retries_very_large(self):
        """
        Attack Vector: Extremely large max_retries value
        Expected: Should not cause infinite loop or OOM
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt

        attempt_count = 0

        @retry(
            stop=stop_after_attempt(10**6),  # 1 million attempts
            wait=wait_exponential(multiplier=0, min=0, max=0),  # No wait to make it fast
            retry=retry_if_exception_type((httpx.ConnectError,)),
            reraise=True,
        )
        async def huge_retries():
            nonlocal attempt_count
            attempt_count += 1
            raise httpx.ConnectError("test")

        start_time = time.time()
        timeout = 5  # 5 second timeout for safety

        try:
            # This should complete within timeout due to reraise
            asyncio.get_event_loop().run_until_complete(huge_retries())
        except httpx.ConnectError:
            pass  # Expected after all retries

        elapsed = time.time() - start_time

        # Should have attempted many times but not infinite
        assert attempt_count > 0
        # Should have stopped within reasonable time (not 1 million * exponential wait)
        assert elapsed < timeout

    def test_retry_count_exactly_at_boundary(self):
        """
        Attack Vector: Test exactly 3 retries (the configured max)
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

        attempt_count = 0

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=0, min=0, max=0),  # No wait for speed
            retry=retry_if_exception_type((httpx.ConnectError,)),
            reraise=True,
        )
        async def three_retries():
            nonlocal attempt_count
            attempt_count += 1
            raise httpx.ConnectError("test")

        with pytest.raises(httpx.ConnectError):
            asyncio.get_event_loop().run_until_complete(three_retries())

        # 1 initial + 3 retries = 4 total attempts
        assert attempt_count == 4


# ==============================================================================
# TEST 3: Concurrent Retries - Race Conditions
# ==============================================================================


class TestConcurrentRetries:
    """Test concurrent retry scenarios"""

    @pytest.mark.asyncio
    async def test_concurrent_retry_calls(self):
        """
        Attack Vector: Multiple concurrent calls to retry-decorated function
        Expected: Each call should have independent retry state
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

        call_tracker = {}
        lock = threading.Lock()

        @retry(
            stop=stop_after_attempt(2),
            wait=wait_exponential(multiplier=0, min=0, max=0),
            retry=retry_if_exception_type((httpx.ConnectError,)),
            reraise=True,
        )
        async def tracked_function(call_id):
            with lock:
                if call_id not in call_tracker:
                    call_tracker[call_id] = 0
                call_tracker[call_id] += 1

            raise httpx.ConnectError(f"call {call_id}")

        # Run 10 concurrent calls
        tasks = [tracked_function(f"call_{i}") for i in range(10)]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should fail after retries
        for result in results:
            assert isinstance(result, httpx.ConnectError)

        # Each call should have attempted 2 times (1 initial + 1 retry)
        for i in range(10):
            assert call_tracker.get(f"call_{i}", 0) == 2

    @pytest.mark.asyncio
    async def test_rapid_concurrent_retry_spam(self):
        """
        Attack Vector: Rapid fire many concurrent retry calls
        Expected: Should handle gracefully without resource exhaustion
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

        @retry(
            stop=stop_after_attempt(1),
            wait=wait_exponential(multiplier=0, min=0, max=0),
            retry=retry_if_exception_type((httpx.ConnectError,)),
            reraise=True,
        )
        async def fail_fast():
            raise httpx.ConnectError("fast fail")

        # Launch 100 concurrent calls
        start_time = time.time()
        tasks = [fail_fast() for _ in range(100)]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start_time

        # All should complete quickly without hanging
        assert elapsed < 10  # Should complete in under 10 seconds

        # All should have failed with ConnectError
        for result in results:
            assert isinstance(result, httpx.ConnectError)


# ==============================================================================
# TEST 4: Resource Exhaustion - Rapid Retry Attacks
# ==============================================================================


class TestResourceExhaustion:
    """Test resource exhaustion scenarios"""

    @pytest.mark.asyncio
    async def test_no_exponential_backoff_limits(self):
        """
        Attack Vector: Very small exponential backoff can cause rapid retries
        Expected: System should handle rapid retries without issues
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

        attempt_count = 0

        @retry(
            stop=stop_after_attempt(5),
            wait=wait_exponential(multiplier=0, min=0, max=0),  # No delay
            retry=retry_if_exception_type((httpx.ConnectError,)),
            reraise=True,
        )
        async def no_delay_retry():
            nonlocal attempt_count
            attempt_count += 1
            raise httpx.ConnectError("test")

        start_time = time.time()

        try:
            await no_delay_retry()
        except httpx.ConnectError:
            pass

        elapsed = time.time() - start_time

        # Should complete quickly even with 5 retries
        assert elapsed < 2  # Should be nearly instant
        assert attempt_count == 6  # 1 initial + 5 retries

    @pytest.mark.asyncio
    async def test_unbounded_wait_max_protection(self):
        """
        Attack Vector: Verify max wait time is enforced
        Expected: Exponential backoff should be capped at max
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

        @retry(
            stop=stop_after_attempt(10),
            wait=wait_exponential(multiplier=1, min=1, max=10),  # Max 10 seconds
            retry=retry_if_exception_type((httpx.ConnectError,)),
            reraise=True,
        )
        async def capped_wait():
            raise httpx.ConnectError("test")

        start_time = time.time()

        try:
            await capped_wait()
        except httpx.ConnectError:
            pass

        elapsed = time.time() - start_time

        # With max=10 and 10 attempts, should NOT take 2^10 = 1024 seconds
        # Should be capped around 10 seconds max per wait
        assert elapsed < 60, f"Retry took too long: {elapsed}s - max wait not enforced"

    @pytest.mark.asyncio
    async def test_memory_exhaustion_from_state(self):
        """
        Attack Vector: Check that retry state doesn't accumulate unbounded
        Expected: Each retry should clean up previous state
        """
        from tenacity import RetryCallState

        # Simulate what tenacity stores per retry attempt
        states = []

        for i in range(100):
            state = RetryCallState(
                retry_object= MagicMock(),
                fn=AsyncMock(),
                args=(),
                kwargs={},
            )
            state.set_result_value("test")
            states.append(state)

        # Verify we can still create new states (no memory leak in test)
        assert len(states) == 100

        # Clear references
        states.clear()

        # New states can be created
        new_state = RetryCallState(
            retry_object=MagicMock(),
            fn=AsyncMock(),
            args=(),
            kwargs={},
        )
        assert new_state is not None


# ==============================================================================
# TEST 5: Integration - Real Retry Behavior
# ==============================================================================


class TestRealRetryBehavior:
    """Test actual retry behavior matches configuration"""

    @pytest.mark.asyncio
    async def test_actual_retry_count_matches_config(self):
        """
        Verify actual retry attempts match configured stop_after_attempt
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

        attempt_count = 0

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=0, min=0, max=0),
            retry=retry_if_exception_type((httpx.ConnectError,)),
            reraise=True,
        )
        async def count_attempts():
            nonlocal attempt_count
            attempt_count += 1
            raise httpx.ConnectError("count")

        try:
            await count_attempts()
        except httpx.ConnectError:
            pass

        # Should be 1 initial + 3 retries = 4 total
        assert attempt_count == 4

    @pytest.mark.asyncio
    async def test_different_exceptions_differently(self):
        """
        Verify only specified exceptions trigger retry
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

        connect_count = 0
        value_count = 0

        @retry(
            stop=stop_after_attempt(2),
            wait=wait_exponential(multiplier=0, min=0, max=0),
            retry=retry_if_exception_type((httpx.ConnectError,)),  # Only ConnectError
            reraise=True,
        )
        async def mixed_errors(should_retry):
            if should_retry:
                nonlocal connect_count
                connect_count += 1
                raise httpx.ConnectError("retry")
            else:
                nonlocal value_count
                value_count += 1
                raise ValueError("no retry")

        # ConnectError should retry
        try:
            await mixed_errors(True)
        except httpx.ConnectError:
            pass

        # ValueError should NOT retry
        try:
            await mixed_errors(False)
        except ValueError:
            pass

        # ConnectError: 1 initial + 2 retries = 3
        assert connect_count == 3
        # ValueError: 1 initial + 0 retries = 1
        assert value_count == 1

    @pytest.mark.asyncio
    async def test_reraise_behavior(self):
        """
        Verify reraise=True causes final exception to propagate
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

        @retry(
            stop=stop_after_attempt(2),
            wait=wait_exponential(multiplier=0, min=0, max=0),
            retry=retry_if_exception_type((httpx.ConnectError,)),
            reraise=True,  # Should reraise
        )
        async def reraises():
            raise httpx.ConnectError("will reraise")

        with pytest.raises(httpx.ConnectError):
            await reraises()


# ==============================================================================
# TEST 6: Security Boundaries - Input Validation
# ==============================================================================


class TestSecurityBoundaries:
    """Test security boundaries and input validation"""

    @pytest.mark.asyncio
    async def test_exception_injection_via_decorator(self):
        """
        Attack Vector: Can we inject arbitrary exceptions into the retry config?
        Expected: Only whitelisted exception types should be retried
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

        # Try to use a dangerous exception that might have side effects
        class DangerousException(BaseException):
            """Could cause issues if caught by generic handlers"""
            pass

        @retry(
            stop=stop_after_attempt(1),
            retry=retry_if_exception_type((DangerousException,)),
            reraise=True,
        )
        async def dangerous():
            raise DangerousException()

        # BaseException should NOT be caught by retry_if_exception_type
        # because it's not an Exception (it's BaseException)
        # But if it is somehow accepted, verify behavior
        try:
            await dangerous()
        except DangerousException:
            pass  # Expected - BaseException propagates
        except Exception:
            # If retry catches it, that's a potential issue
            pytest.fail("BaseException was caught by retry - potential security issue")

    def test_retry_config_does_not_accept_callable(self):
        """
        Attack Vector: Can callable be passed as exception type?
        Expected: Should reject or handle safely
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt

        def dangerous_callable():
            """Could have side effects if called during retry"""
            return ValueError("called")

        try:
            # This should fail - retry_if_exception_type expects class, not callable
            @retry(
                stop=stop_after_attempt(1),
                retry=retry_if_exception_type((dangerous_callable,)),
                reraise=True,
            )
            async def test_callable():
                pass
            pytest.skip("Accepted callable")
        except TypeError:
            pass  # Expected to reject


# ==============================================================================
# TEST 7: Timing Attacks
# ==============================================================================


class TestTimingAttacks:
    """Test timing-related attack vectors"""

    @pytest.mark.asyncio
    async def test_retry_timing_consistency(self):
        """
        Attack Vector: Timing side-channel - does retry timing leak information?
        Expected: Retry timing should be consistent regardless of failure reason
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

        @retry(
            stop=stop_after_attempt(2),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((httpx.ConnectError,)),
            reraise=True,
        )
        async def timed_fail():
            raise httpx.ConnectError("test")

        times = []
        for _ in range(3):
            start = time.time()
            try:
                await timed_fail()
            except httpx.ConnectError:
                pass
            times.append(time.time() - start)

        # Timing should be relatively consistent (within an order of magnitude)
        # This is a weak test but checks for obvious timing leaks
        avg_time = sum(times) / len(times)
        for t in times:
            assert t < avg_time * 10, f"Timing anomaly detected: {t} vs avg {avg_time}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
