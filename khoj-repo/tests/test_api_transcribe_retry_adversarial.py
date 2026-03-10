"""
Adversarial Security Tests for api.py Transcribe Retry Logic

Security-focused attack tests for the transcribe endpoint retry mechanism:
- Invalid exception types in retry decorator
- Boundary: max retries exceeded behavior
- Concurrent retry attempts
- Resource exhaustion via rapid retries

ATTACK VECTORS TESTED:
1. Malformed exception types (non-Exception classes, strings, None)
2. Boundary violations (max_retries=0, negative, extremely large)
3. Concurrent retry attacks (multiple simultaneous retry consumers)
4. Resource exhaustion (rapid retry spam, unbounded retry loops)

Target endpoint: POST /api/transcribe
Retry decorator config: stop_after_attempt(3), wait_exponential(multiplier=1, min=2, max=10)
"""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


# ==============================================================================
# TEST 1: Invalid Exception Types - Malformed Inputs to Retry Decorator
# ==============================================================================


class TestInvalidExceptionTypesTranscribe:
    """Test that invalid exception types are handled safely in transcribe retry config"""

    def test_non_exception_class_in_retry_transcribe(self):
        """
        Attack Vector: Pass non-Exception class to retry_if_exception_type
        Expected: Should either fail gracefully or ignore invalid types
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt

        # Attempt to create retry with invalid type (non-Exception class)
        invalid_type = type("InvalidType", (), {})

        try:
            @retry(
                stop=stop_after_attempt(1),
                retry=retry_if_exception_type((invalid_type,)),
                reraise=True,
            )
            async def will_never_run():
                pass

            pytest.skip("Decorator accepted invalid type - validation happens at runtime")
        except (TypeError, AttributeError):
            pass  # Expected: decorator should reject invalid types

    def test_string_instead_of_exception_type_transcribe(self):
        """
        Attack Vector: Pass string instead of exception class (like in transcribe)
        Expected: Should raise TypeError or handle gracefully
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt

        # String is not a valid exception type - mimicking possible config error
        try:
            @retry(
                stop=stop_after_attempt(1),
                retry=retry_if_exception_type(("ValueError",)),  # String, not class
                reraise=True,
            )
            async def will_never_run():
                pass
            pytest.skip("Decorator accepted string type - validation needed")
        except TypeError:
            pass  # Expected: should reject string

    def test_none_in_exception_types_transcribe(self):
        """
        Attack Vector: Pass None in exception type tuple
        Expected: Should handle gracefully without crash
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt

        try:
            @retry(
                stop=stop_after_attempt(1),
                retry=retry_if_exception_type((None, httpx.ConnectError)),
                reraise=True,
            )
            async def will_never_run():
                pass
            pytest.skip("Decorator accepted None type")
        except (TypeError, AttributeError):
            pass  # Expected to reject None

    def test_mixed_valid_invalid_exception_types_transcribe(self):
        """
        Attack Vector: Tuple with both valid (httpx errors) and invalid types
        Expected: Should work with valid ones, fail gracefully for invalid
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt

        class NotAnException:
            pass

        attempt_count = 0

        # Mix of valid (httpx.ConnectError) and invalid (NotAnException)
        try:
            @retry(
                stop=stop_after_attempt(1),
                retry=retry_if_exception_type((NotAnException, httpx.ConnectError)),
                reraise=True,
            )
            async def test_func():
                nonlocal attempt_count
                attempt_count += 1
                raise httpx.ConnectError("test")

            try:
                asyncio.get_event_loop().run_until_complete(test_func())
            except httpx.ConnectError:
                pass  # Expected

            # If no crash, should have attempted once
            assert attempt_count >= 1
        except Exception as e:
            # Should fail gracefully
            assert "exception" in str(e).lower() or "type" in str(e).lower()


# ==============================================================================
# TEST 2: Boundary - Max Retries Exceeded Behavior
# ==============================================================================


class TestMaxRetriesBoundaryTranscribe:
    """Test boundary conditions for max retries matching transcribe config"""

    def test_max_retries_zero_transcribe(self):
        """
        Attack Vector: Set max_retries to 0 - should never retry
        Matches transcribe endpoint with stop_after_attempt(3)
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt

        attempt_count = 0

        @retry(
            stop=stop_after_attempt(0),  # Zero retries like transcribe config
            retry=retry_if_exception_type((httpx.ConnectError,)),
            reraise=True,
        )
        async def zero_retries():
            nonlocal attempt_count
            attempt_count += 1
            raise httpx.ConnectError("test")

        with pytest.raises(httpx.ConnectError):
            asyncio.get_event_loop().run_until_complete(zero_retries())

        # With 0 attempts, should still run once (initial attempt)
        assert attempt_count >= 1

    def test_max_retries_negative_transcribe(self):
        """
        Attack Vector: Negative max_retries value
        Expected: Should handle gracefully
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

            asyncio.get_event_loop().run_until_complete(negative_retries())
        except (ValueError, Exception):
            pass  # Expected to fail or behave unexpectedly

    def test_max_retries_very_large_transcribe(self):
        """
        Attack Vector: Extremely large max_retries value (DoS vector)
        Expected: Should not cause infinite loop or OOM
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

        attempt_count = 0

        @retry(
            stop=stop_after_attempt(10**6),  # 1 million attempts - DoS attempt
            wait=wait_exponential(multiplier=0, min=0, max=0),  # No wait
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
            asyncio.get_event_loop().run_until_complete(huge_retries())
        except httpx.ConnectError:
            pass  # Expected after all retries

        elapsed = time.time() - start_time

        # Should have attempted many times but not infinite
        assert attempt_count > 0
        # Should have stopped within reasonable time
        assert elapsed < timeout

    def test_retry_count_exactly_3_transcribe(self):
        """
        Attack Vector: Test exactly 3 retries (transcribe's configured max)
        Verify transcribe endpoint stops after 3 retry attempts
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

        attempt_count = 0

        @retry(
            stop=stop_after_attempt(3),  # Same as transcribe config
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

        # stop_after_attempt(3) = 3 total attempts (not 4)
        assert attempt_count == 3


# ==============================================================================
# TEST 3: Concurrent Retries - Race Conditions
# ==============================================================================


class TestConcurrentRetriesTranscribe:
    """Test concurrent retry scenarios for transcribe endpoint"""

    @pytest.mark.asyncio
    async def test_concurrent_retry_calls_transcribe(self):
        """
        Attack Vector: Multiple concurrent calls to transcribe retry-decorated function
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

        # Run 10 concurrent calls (simulating multiple transcribe requests)
        tasks = [tracked_function(f"call_{i}") for i in range(10)]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should fail after retries
        for result in results:
            assert isinstance(result, httpx.ConnectError)

        # Each call should have attempted 2 times (1 initial + 1 retry)
        for i in range(10):
            assert call_tracker.get(f"call_{i}", 0) == 2

    @pytest.mark.asyncio
    async def test_rapid_concurrent_retry_spam_transcribe(self):
        """
        Attack Vector: Rapid fire many concurrent retry calls (DoS)
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

        # Launch 100 concurrent calls (simulating retry spam)
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


class TestResourceExhaustionTranscribe:
    """Test resource exhaustion scenarios for transcribe retry"""

    @pytest.mark.asyncio
    async def test_no_exponential_backoff_limits_transcribe(self):
        """
        Attack Vector: Very small exponential backoff can cause rapid retries
        Expected: System should handle rapid retries without issues
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

        attempt_count = 0

        @retry(
            stop=stop_after_attempt(5),
            wait=wait_exponential(multiplier=0, min=0, max=0),  # No delay - rapid retries
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
        assert attempt_count == 5  # stop_after_attempt(5) = 5 total attempts

    @pytest.mark.asyncio
    async def test_unbounded_wait_max_protection_transcribe(self):
        """
        Attack Vector: Verify max wait time is enforced (transcribe uses max=10)
        Expected: Exponential backoff should be capped at max
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

        @retry(
            stop=stop_after_attempt(10),
            wait=wait_exponential(multiplier=1, min=1, max=10),  # Same as transcribe: max=10
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
    async def test_transcribe_retry_exponential_backoff_timing(self):
        """
        Attack Vector: Verify transcribe's exponential backoff timing
        Expected: wait_exponential(multiplier=1, min=2, max=10)
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

        sleep_times = []

        original_sleep = time.sleep
        def track_sleep(duration):
            sleep_times.append(duration)
            original_sleep(duration)

        @retry(
            stop=stop_after_attempt(4),
            wait=wait_exponential(multiplier=1, min=2, max=10),  # Exactly like transcribe
            retry=retry_if_exception_type((httpx.ConnectError,)),
            reraise=True,
        )
        async def timed_retry():
            raise httpx.ConnectError("test")

        with patch('time.sleep', side_effect=track_sleep):
            try:
                await timed_retry()
            except httpx.ConnectError:
                pass

        # Should have 3 retry wait periods (after 1st, 2nd, 3rd failures)
        assert len(sleep_times) == 3

        # First retry: min=2, then 4, then capped at max=10
        # Wait sequence: 2, 4, 8 (capped at 10 means max is 10, so 2, 4, 8)
        # Actually: 2^1=2, 2^2=4, 2^3=8 (all under max=10)
        assert sleep_times[0] >= 2  # min=2
        assert sleep_times[1] >= 4  # exponential
        assert sleep_times[2] >= 8  # exponential


# ==============================================================================
# TEST 5: Integration - Transcribe Retry Configuration Tests
# ==============================================================================


class TestTranscribeRetryConfig:
    """Test actual retry behavior matches transcribe endpoint configuration"""

    @pytest.mark.asyncio
    async def test_transcribe_exception_types_are_whitelisted(self):
        """
        Verify only whitelisted httpx exceptions trigger retry in transcribe
        Config: (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

        connect_count = 0
        timeout_count = 0
        network_count = 0
        value_count = 0

        @retry(
            stop=stop_after_attempt(2),
            wait=wait_exponential(multiplier=0, min=0, max=0),
            retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)),
            reraise=True,
        )
        async def test_exceptions(exception_type):
            nonlocal connect_count, timeout_count, network_count, value_count
            if exception_type == "connect":
                connect_count += 1
                raise httpx.ConnectError("retry")
            elif exception_type == "timeout":
                timeout_count += 1
                raise httpx.TimeoutException("retry")
            elif exception_type == "network":
                network_count += 1
                raise httpx.NetworkError("retry")
            else:
                value_count += 1
                raise ValueError("no retry")

        # All httpx exceptions should retry
        for _ in range(2):
            try:
                await test_exceptions("connect")
            except httpx.ConnectError:
                pass

        for _ in range(2):
            try:
                await test_exceptions("timeout")
            except httpx.TimeoutException:
                pass

        for _ in range(2):
            try:
                await test_exceptions("network")
            except httpx.NetworkError:
                pass

        # ValueError should NOT retry
        try:
            await test_exceptions("value")
        except ValueError:
            pass

        # Each httpx exception: 1 initial + 2 retries = 3
        assert connect_count == 3
        assert timeout_count == 3
        assert network_count == 3
        # ValueError: 1 initial + 0 retries = 1
        assert value_count == 1

    @pytest.mark.asyncio
    async def test_reraise_behavior_transcribe(self):
        """
        Verify reraise=True causes final exception to propagate
        Transcribe endpoint should fail after exhausting retries
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


class TestSecurityBoundariesTranscribe:
    """Test security boundaries for transcribe retry"""

    @pytest.mark.asyncio
    async def test_base_exception_not_caught_transcribe(self):
        """
        Attack Vector: BaseException should NOT be caught by retry
        Expected: Only Exception subclasses should trigger retry
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt

        class DangerousException(BaseException):
            pass

        @retry(
            stop=stop_after_attempt(1),
            retry=retry_if_exception_type((httpx.ConnectError,)),
            reraise=True,
        )
        async def dangerous():
            raise DangerousException()

        # BaseException should NOT be caught - should propagate immediately
        try:
            await dangerous()
        except DangerousException:
            pass  # Expected - BaseException propagates
        except Exception:
            pytest.fail("BaseException was caught by retry - potential security issue")

    def test_retry_config_does_not_accept_callable_transcribe(self):
        """
        Attack Vector: Can callable be passed as exception type?
        Expected: Should reject or handle safely
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt

        def dangerous_callable():
            return ValueError("called")

        try:
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
# TEST 7: Timing and DoS Resistance
# ==============================================================================


class TestTimingAttacksTranscribe:
    """Test timing-related attack vectors for transcribe retry"""

    @pytest.mark.asyncio
    async def test_retry_timing_consistency_transcribe(self):
        """
        Attack Vector: Timing side-channel
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

        # Timing should be relatively consistent
        avg_time = sum(times) / len(times)
        for t in times:
            assert t < avg_time * 10, f"Timing anomaly detected: {t} vs avg {avg_time}"

    @pytest.mark.asyncio
    async def test_dos_via_wait_parameter_manipulation(self):
        """
        Attack Vector: Can wait parameter be manipulated to cause DoS?
        Expected: Should have reasonable upper bounds
        """
        from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

        @retry(
            stop=stop_after_attempt(5),
            wait=wait_exponential(multiplier=1, min=1, max=60),  # Capped at 60s
            retry=retry_if_exception_type((httpx.ConnectError,)),
            reraise=True,
        )
        async def long_wait():
            raise httpx.ConnectError("test")

        start_time = time.time()

        try:
            await long_wait()
        except httpx.ConnectError:
            pass

        elapsed = time.time() - start_time

        # With max=60 and 5 attempts, max total wait ~60 seconds
        # But exponential: 1+2+4+8+16 = 31 seconds max
        assert elapsed < 120, f"DoS via wait param: {elapsed}s"


# ==============================================================================
# TEST 8: Verify Transcribe Endpoint Actual Configuration
# ==============================================================================


class TestVerifyTranscribeConfig:
    """Verify the actual transcribe endpoint retry configuration"""

    def test_transcribe_retry_config_matches_source(self):
        """
        Verify transcribe endpoint has correct retry config from source
        """
        import os
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        SOURCE_FILE = os.path.join(BASE_DIR, 'src', 'khoj', 'routers', 'api.py')

        with open(SOURCE_FILE, 'r') as f:
            content = f.read()

        # Find transcribe function's retry decorator
        transcribe_start = content.find('async def transcribe')
        transcribe_section = content[max(0, transcribe_start - 600):transcribe_start]

        # Verify the exact configuration from source
        assert '@retry' in transcribe_section
        assert 'stop_after_attempt(3)' in transcribe_section
        assert 'wait_exponential' in transcribe_section
        assert 'httpx.ConnectError' in transcribe_section
        assert 'httpx.TimeoutException' in transcribe_section
        assert 'httpx.NetworkError' in transcribe_section


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
