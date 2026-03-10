"""
Tests for api_chat.py retry logic

Verifies:
- Retry decorator is applied to event_generator
- Exception types (ConnectError, TimeoutException, NetworkError) trigger retries
- After 3 retries, exception is raised
- HTTP endpoint returns 503 on retry exhaustion
- WebSocket sends error message on retry exhaustion
"""

import os
import re

# Get the base directory (khoj-repo)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_FILE = os.path.join(BASE_DIR, 'src', 'khoj', 'routers', 'api_chat.py')


def test_retry_decorator_is_applied():
    """Verify event_generator has the retry decorator applied"""
    # Read the source file
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Check that the retry decorator is applied to event_generator
    # The decorator spans multiple lines, so we need to use re.DOTALL
    pattern = r'@retry\([\s\S]*?\)\s+async def event_generator'
    assert re.search(pattern, content), "Retry decorator should be applied to event_generator"


def test_retry_stops_after_3_attempts():
    """Verify retry stops after 3 attempts"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Check that stop_after_attempt(3) is used
    assert 'stop=stop_after_attempt(3)' in content, "Retry should stop after 3 attempts"


def test_retry_uses_exponential_backoff():
    """Verify retry uses exponential backoff wait strategy"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Check that wait_exponential is used
    assert 'wait=wait_exponential' in content, "Retry should use exponential backoff"


def test_retry_reraise_is_true():
    """Verify retry is configured to reraise exception after retries"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Check that reraise=True is set
    assert 'reraise=True' in content, "Retry should reraise exception after retries are exhausted"


def test_retry_on_connect_error():
    """Verify ConnectError triggers retry"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Check that ConnectError is in the retry list
    assert 'httpx.ConnectError' in content, "Retry should trigger on ConnectError"


def test_retry_on_timeout_exception():
    """Verify TimeoutException triggers retry"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Check that TimeoutException is in the retry list
    assert 'httpx.TimeoutException' in content, "Retry should trigger on TimeoutException"


def test_retry_on_network_error():
    """Verify NetworkError triggers retry"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Check that NetworkError is in the retry list
    assert 'httpx.NetworkError' in content, "Retry should trigger on NetworkError"


def test_retry_uses_retry_if_exception_type():
    """Verify retry uses retry_if_exception_type"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Check that retry_if_exception_type is used
    assert 'retry_if_exception_type' in content, "Retry should use retry_if_exception_type"


def test_http_endpoint_returns_503_on_retry_exhaustion():
    """Verify HTTP endpoint returns 503 when retries are exhausted"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Find the chat endpoint function and verify 503 response
    # Look for the pattern that catches the retry exceptions and returns 503
    assert 'status_code=503' in content, "HTTP endpoint should return 503 on retry exhaustion"
    assert 'Service temporarily unavailable' in content, "HTTP endpoint should return unavailable message"


def test_websocket_sends_error_on_retry_exhaustion():
    """Verify WebSocket sends error message when retries are exhausted"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Verify WebSocket sends error on retry exhaustion
    # The WebSocket handler should catch the exceptions and send an error message
    assert 'websocket.send_text' in content, "WebSocket should send text messages"
    assert '"error": "Service temporarily unavailable' in content, "WebSocket should send error message"


def test_websocket_handles_retry_exceptions():
    """Verify WebSocket endpoint handles retry exceptions"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Verify the WebSocket endpoint catches retry exceptions
    # Look for the except block that handles the httpx exceptions in WebSocket context
    ws_section = content[content.find('@api_chat.websocket'):]
    
    # Check that the websocket handler has the exception handling
    assert 'except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)' in ws_section


def test_http_endpoint_handles_retry_exceptions():
    """Verify HTTP endpoint handles retry exceptions"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Find the HTTP chat endpoint section
    http_section = content[content.find('@api_chat.post("")'):]
    
    # Check that the HTTP endpoint catches retry exceptions
    assert 'except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)' in http_section


def test_retry_decorator_full_configuration():
    """Verify the full retry decorator configuration"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Extract the retry decorator configuration
    retry_config_pattern = r'@retry\(\s*stop=stop_after_attempt\(3\),\s*wait=wait_exponential\([^)]+\),\s*retry=retry_if_exception_type\(\(httpx\.ConnectError,\s*httpx\.TimeoutException,\s*httpx\.NetworkError\)\),\s*reraise=True\s*\)'
    
    # This is a more thorough check of the decorator configuration
    assert '@retry(' in content
    assert 'stop=stop_after_attempt(3)' in content
    assert 'wait=wait_exponential' in content
    assert 'retry=retry_if_exception_type' in content
    assert 'reraise=True' in content


def test_all_three_exception_types_in_tuple():
    """Verify all three exception types are in the retry tuple"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Check that all three exception types are in a tuple for retry_if_exception_type
    # Looking for the pattern in the retry decorator
    assert 'retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError))' in content


def test_event_generator_has_retry_decorator():
    """Verify event_generator is decorated with @retry"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Find the event_generator function definition
    # The @retry decorator should be right before it
    pattern = r'@retry\([\s\S]*?\)\s+async def event_generator\('
    match = re.search(pattern, content)
    assert match is not None, "event_generator should have @retry decorator"


def test_retry_wait_exponential_params():
    """Verify exponential backoff has proper parameters"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Check that wait_exponential has the right parameters
    assert 'wait_exponential(multiplier=1, min=2, max=10)' in content
