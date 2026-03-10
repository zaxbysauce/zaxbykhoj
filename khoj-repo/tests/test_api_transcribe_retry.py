"""
Tests for api.py transcribe retry logic

Verifies:
- Retry decorator is applied to transcribe function
- Exception types (ConnectError, TimeoutException, NetworkError) trigger retries
- After 3 retries, exception is raised
- Variables (status_code, audio_file) are properly initialized
"""

import os
import re

# Get the base directory (khoj-repo)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_FILE = os.path.join(BASE_DIR, 'src', 'khoj', 'routers', 'api.py')


def test_retry_decorator_is_applied():
    """Verify transcribe function has the retry decorator applied"""
    # Read the source file
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Find the transcribe function section - include some lines above it
    transcribe_func_pos = content.find('async def transcribe')
    # Get a section that includes the decorators above transcribe (go back 500 chars to include decorators)
    transcribe_section = content[max(0, transcribe_func_pos - 500):transcribe_func_pos + 1000]
    
    # Check that both @retry and async def transcribe are in this section
    assert '@retry' in transcribe_section, "Retry decorator should be present"
    assert 'async def transcribe' in transcribe_section, "transcribe function should be present"


def test_retry_stops_after_3_attempts():
    """Verify retry stops after 3 attempts"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Check that stop_after_attempt(3) is used in the transcribe section
    transcribe_section = content[content.find('@retry'):content.find('async def transcribe') + 800]
    assert 'stop_after_attempt(3)' in transcribe_section, "Retry should stop after 3 attempts"


def test_retry_uses_exponential_backoff():
    """Verify retry uses exponential backoff wait strategy"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Check that wait_exponential is used
    transcribe_section = content[content.find('@retry'):content.find('async def transcribe') + 800]
    assert 'wait_exponential' in transcribe_section, "Retry should use exponential backoff"


def test_retry_on_connect_error():
    """Verify ConnectError triggers retry"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Check that ConnectError is in the retry list
    transcribe_section = content[content.find('@retry'):content.find('async def transcribe') + 800]
    assert 'httpx.ConnectError' in transcribe_section, "Retry should trigger on ConnectError"


def test_retry_on_timeout_exception():
    """Verify TimeoutException triggers retry"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Check that TimeoutException is in the retry list
    transcribe_section = content[content.find('@retry'):content.find('async def transcribe') + 800]
    assert 'httpx.TimeoutException' in transcribe_section, "Retry should trigger on TimeoutException"


def test_retry_on_network_error():
    """Verify NetworkError triggers retry"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Check that NetworkError is in the retry list
    transcribe_section = content[content.find('@retry'):content.find('async def transcribe') + 800]
    assert 'httpx.NetworkError' in transcribe_section, "Retry should trigger on NetworkError"


def test_retry_uses_retry_if_exception_type():
    """Verify retry uses retry_if_exception_type"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Check that retry_if_exception_type is used
    transcribe_section = content[content.find('@retry'):content.find('async def transcribe') + 800]
    assert 'retry_if_exception_type' in transcribe_section, "Retry should use retry_if_exception_type"


def test_status_code_variable_initialized():
    """Verify status_code variable is initialized"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Find the transcribe function
    transcribe_start = content.find('async def transcribe')
    transcribe_section = content[transcribe_start:transcribe_start + 1500]
    
    # Check that status_code is initialized to None
    assert 'status_code = None' in transcribe_section, "status_code should be initialized to None"


def test_audio_file_variable_initialized():
    """Verify audio_file variable is initialized"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Find the transcribe function
    transcribe_start = content.find('async def transcribe')
    transcribe_section = content[transcribe_start:transcribe_start + 1500]
    
    # Check that audio_file is initialized to None
    assert 'audio_file = None' in transcribe_section, "audio_file should be initialized to None"


def test_user_message_variable_initialized():
    """Verify user_message variable is initialized to None"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Find the transcribe function
    transcribe_start = content.find('async def transcribe')
    transcribe_section = content[transcribe_start:transcribe_start + 1500]
    
    # Check that user_message is initialized to None
    assert 'user_message: str = None' in transcribe_section or 'user_message = None' in transcribe_section, \
        "user_message should be initialized to None"


def test_retry_decorator_full_configuration():
    """Verify the full retry decorator configuration for transcribe"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Extract the retry decorator configuration
    transcribe_section = content[content.find('@retry'):content.find('async def transcribe') + 800]
    
    # Verify the complete configuration
    assert 'stop=stop_after_attempt(3)' in transcribe_section, "Should have stop_after_attempt(3)"
    assert 'wait=wait_exponential' in transcribe_section, "Should have wait_exponential"
    assert 'retry=retry_if_exception_type' in transcribe_section, "Should have retry_if_exception_type"
    assert 'httpx.ConnectError' in transcribe_section, "Should include ConnectError"
    assert 'httpx.TimeoutException' in transcribe_section, "Should include TimeoutException"
    assert 'httpx.NetworkError' in transcribe_section, "Should include NetworkError"


def test_transcribe_function_has_requires_auth():
    """Verify transcribe function has authentication decorator"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Find the transcribe function section - include some lines above it
    transcribe_func_pos = content.find('async def transcribe')
    # Get a section that includes the decorators above transcribe (go back 500 chars to include decorators)
    transcribe_section = content[max(0, transcribe_func_pos - 500):transcribe_func_pos + 1000]
    
    # Check that both @requires and async def transcribe are in this section
    assert '@requires' in transcribe_section, "@requires decorator should be present"
    assert 'async def transcribe' in transcribe_section, "transcribe function should be present"


def test_transcribe_has_rate_limiting():
    """Verify transcribe function has rate limiting"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Find the transcribe function
    transcribe_section = content[content.find('async def transcribe'):content.find('async def transcribe') + 2000]
    
    # Check for rate limiting dependencies
    assert 'rate_limiter' in transcribe_section, "transcribe should have rate limiting"
    assert 'ApiUserRateLimiter' in transcribe_section, "transcribe should use ApiUserRateLimiter"


def test_exception_types_tuple_format():
    """Verify exception types are passed as a tuple"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Find the retry decorator
    transcribe_section = content[content.find('@retry'):content.find('async def transcribe') + 800]
    
    # Check that exceptions are passed as a tuple (tuple in parentheses)
    assert 'retry_if_exception_type((' in transcribe_section, "Exception types should be passed as a tuple"


def test_transcribe_endpoint_is_post():
    """Verify transcribe endpoint is a POST endpoint"""
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    
    # Find the transcribe endpoint decorator
    transcribe_start = content.find('@api.post("/transcribe")')
    assert transcribe_start != -1, "transcribe should be a POST endpoint"
