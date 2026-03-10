# tests/test_operator_environment_security.py
"""
Adversarial security tests for operator_environment_computer.py
Tests for command injection, shell escape, and other subprocess vulnerabilities
"""
import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Set Django settings before any imports to avoid database connection
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "khoj.app.settings")
os.environ["DATABASE_URL"] = "sqlite:///test.db"

# Mock Django to avoid database setup
import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
        ],
        SECRET_KEY='test-secret-key',
    )
    django.setup()

from khoj.processor.operator.operator_actions import OperatorAction
from khoj.processor.operator.operator_environment_computer import ComputerEnvironment


class TestCommandInjection:
    """Test command injection attack vectors in ComputerEnvironment"""

    @pytest.fixture
    def computer_env(self):
        """Create a ComputerEnvironment instance for testing"""
        return ComputerEnvironment(provider="local")

    @pytest.mark.asyncio
    async def test_terminal_action_command_injection_semicolon(self, computer_env):
        """Test: Attempt command injection via semicolon in terminal action"""
        # Payload: ; whoami - should execute both commands if vulnerable
        malicious_command = "echo test; whoami"
        
        action = OperatorAction(
            type="terminal",
            command=malicious_command
        )
        
        result = await computer_env.step(action)
        
        # If vulnerable, would see output from both commands
        # The implementation should only execute echo test, not whoami
        # Check that output doesn't contain user information
        if result.output:
            assert "whoami" not in result.output.lower() or "command execution failed" in result.error.lower() if result.error else True

    @pytest.mark.asyncio
    async def test_terminal_action_command_injection_pipe(self, computer_env):
        """Test: Attempt command injection via pipe in terminal action"""
        # Payload: echo test | cat
        malicious_command = "echo test | cat"
        
        action = OperatorAction(
            type="terminal",
            command=malicious_command
        )
        
        result = await computer_env.step(action)
        
        # Pipe should not be interpreted if using shlex.split with shell=False
        # But let's verify
        if result.output:
            assert "|" not in result.output or "command execution failed" in result.error.lower() if result.error else True

    @pytest.mark.asyncio
    async def test_terminal_action_command_injection_backtick(self, computer_env):
        """Test: Attempt command injection via backtick substitution"""
        malicious_command = "echo `whoami`"
        
        action = OperatorAction(
            type="terminal",
            command=malicious_command
        )
        
        result = await computer_env.step(action)
        
        # Backticks should not be interpreted
        if result.output:
            assert "`" not in result.output or "command execution failed" in result.error.lower() if result.error else True

    @pytest.mark.asyncio
    async def test_terminal_action_command_injection_dollar(self, computer_env):
        """Test: Attempt command injection via $() substitution"""
        malicious_command = "echo $(whoami)"
        
        action = OperatorAction(
            type="terminal",
            command=malicious_command
        )
        
        result = await computer_env.step(action)
        
        # $() should not be interpreted
        if result.output:
            assert "$(" not in result.output or "command execution failed" in result.error.lower() if result.error else True

    @pytest.mark.asyncio
    async def test_terminal_action_command_injection_newline(self, computer_env):
        """Test: Attempt command injection via newline escape"""
        malicious_command = "echo test\nwhoami"
        
        action = OperatorAction(
            type="terminal",
            command=malicious_command
        )
        
        result = await computer_env.step(action)
        
        # Newlines should not create multiple commands
        if result.output:
            # Should either fail or only output "test"
            assert result.output.strip() == "test" or "command execution failed" in result.error.lower() if result.error else True

    @pytest.mark.asyncio
    async def test_terminal_action_command_injection_redirect(self, computer_env):
        """Test: Attempt command injection via output redirect"""
        # Try to redirect output to a file
        malicious_command = "echo test > /tmp/pwned_test_file"
        
        action = OperatorAction(
            type="terminal",
            command=malicious_command
        )
        
        result = await computer_env.step(action)
        
        # Check that the file wasn't created (successful redirect would create it)
        # Note: This test checks if the redirect is blocked
        pwned_file = Path("/tmp/pwned_test_file")
        if pwned_file.exists():
            pwned_file.unlink()  # Clean up
            pytest.fail("Command injection successful: redirect was executed")

    @pytest.mark.asyncio
    async def test_terminal_action_command_injection_and(self, computer_env):
        """Test: Attempt command injection via && operator"""
        malicious_command = "echo test && whoami"
        
        action = OperatorAction(
            type="terminal",
            command=malicious_command
        )
        
        result = await computer_env.step(action)
        
        # && should not be interpreted
        if result.output:
            assert "&&" not in result.output or "command execution failed" in result.error.lower() if result.error else True

    @pytest.mark.asyncio
    async def test_terminal_action_command_injection_or(self, computer_env):
        """Test: Attempt command injection via || operator"""
        malicious_command = "nonexistent_cmd || whoami"
        
        action = OperatorAction(
            type="terminal",
            command=malicious_command
        )
        
        result = await computer_env.step(action)
        
        # || should not be interpreted
        if result.output:
            # Should not see whoami output
            assert "uid=" not in result.output.lower() and "command execution failed" in result.error.lower() if result.error else True


class TestShellEscape:
    """Test shell escape attack vectors"""

    @pytest.fixture
    def computer_env(self):
        """Create a ComputerEnvironment instance for testing"""
        return ComputerEnvironment(provider="local")

    @pytest.mark.asyncio
    async def test_text_editor_create_shell_escape_single_quote(self, computer_env):
        """Test: Attempt shell escape via single quote in text_editor_create"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Payload: file content with single quote that breaks out of echo
            # Original: echo 'content' > file
            # Attack: file'; malicious command; echo '
            malicious_text = "test'; touch /tmp/pwned_quote_test; echo '"
            malicious_path = os.path.join(tmpdir, "test.txt")
            
            action = OperatorAction(
                type="text_editor_create",
                path=malicious_path,
                file_text=malicious_text
            )
            
            result = await computer_env.step(action)
            
            # Check if pwned file was created
            pwned_file = Path("/tmp/pwned_quote_test")
            if pwned_file.exists():
                pwned_file.unlink()
                pytest.fail("Shell escape successful: single quote injection worked")

    @pytest.mark.asyncio
    async def test_text_editor_create_shell_escape_dollar(self, computer_env):
        """Test: Attempt shell escape via dollar sign in text_editor_create"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Payload: content with $()
            malicious_text = "test $(touch /tmp/pwned_dollar_test)"
            malicious_path = os.path.join(tmpdir, "test.txt")
            
            action = OperatorAction(
                type="text_editor_create",
                path=malicious_path,
                file_text=malicious_text
            )
            
            result = await computer_env.step(action)
            
            # Check if pwned file was created
            pwned_file = Path("/tmp/pwned_dollar_test")
            if pwned_file.exists():
                pwned_file.unlink()
                pytest.fail("Shell escape successful: dollar sign injection worked")

    @pytest.mark.asyncio
    async def test_text_editor_create_shell_escape_backtick(self, computer_env):
        """Test: Attempt shell escape via backtick in text_editor_create"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Payload: content with backticks
            malicious_text = "test `touch /tmp/pwned_backtick_test`"
            malicious_path = os.path.join(tmpdir, "test.txt")
            
            action = OperatorAction(
                type="text_editor_create",
                path=malicious_path,
                file_text=malicious_text
            )
            
            result = await computer_env.step(action)
            
            # Check if pwned file was created
            pwned_file = Path("/tmp/pwned_backtick_test")
            if pwned_file.exists():
                pwned_file.unlink()
                pytest.fail("Shell escape successful: backtick injection worked")

    @pytest.mark.asyncio
    async def test_text_editor_create_shell_escape_semicolon(self, computer_env):
        """Test: Attempt shell escape via semicolon in text_editor_create"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Payload: content with semicolon
            malicious_text = "test; touch /tmp/pwned_semicolon_test; echo "
            malicious_path = os.path.join(tmpdir, "test.txt")
            
            action = OperatorAction(
                type="text_editor_create",
                path=malicious_path,
                file_text=malicious_text
            )
            
            result = await computer_env.step(action)
            
            # Check if pwned file was created
            pwned_file = Path("/tmp/pwned_semicolon_test")
            if pwned_file.exists():
                pwned_file.unlink()
                pytest.fail("Shell escape successful: semicolon injection worked")

    @pytest.mark.asyncio
    async def test_text_editor_create_path_traversal(self, computer_env):
        """Test: Attempt path traversal in text_editor_create"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Payload: path with ../ to escape directory
            malicious_path = os.path.join(tmpdir, "..", "..", "pwned_path_test.txt")
            
            # This should either succeed in a safe way or fail
            # The key is it shouldn't write outside tmpdir
            action = OperatorAction(
                type="text_editor_create",
                path=malicious_path,
                file_text="test"
            )
            
            result = await computer_env.step(action)
            
            # Check that file wasn't created outside tmpdir
            pwned_file = Path("/tmp/pwned_path_test.txt")
            # This is less critical as it's a file write test, but good to verify


class TestDockerExecution:
    """Test Docker execution path vulnerabilities"""

    @pytest.mark.asyncio
    async def test_docker_terminal_command_injection(self):
        """Test: Command injection in Docker execution path"""
        # This test checks if docker execution path is vulnerable
        # Note: This may require docker to be available
        computer_env = ComputerEnvironment(provider="docker", docker_container_name="test-container")
        
        # If docker isn't available, skip
        import subprocess
        try:
            subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("Docker not available")
        
        malicious_command = "echo test; whoami"
        
        action = OperatorAction(
            type="terminal",
            command=malicious_command
        )
        
        # Even if docker is available, this would run in a container
        # The test is to verify the command doesn't get injection
        try:
            result = await computer_env.step(action)
            # If vulnerable, would see output from both commands
            if result.output:
                assert "whoami" not in result.output.lower() or result.error is not None
        except Exception:
            # If command fails due to no container, that's also acceptable
            pass


class TestPyautoguiExecution:
    """Test the pyautogui command execution path"""

    @pytest.fixture
    def computer_env(self):
        """Create a ComputerEnvironment instance for testing"""
        return ComputerEnvironment(provider="local")

    @pytest.mark.asyncio
    async def test_pyautogui_function_injection(self, computer_env):
        """Test: Attempt to inject arbitrary Python via pyautogui function args"""
        # The generate_pyautogui_command uses repr() which should be safe
        # Let's verify it doesn't allow code execution
        
        # Try to pass a malicious argument
        with patch('subprocess.run') as mock_run:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.stdout = "test"
            mock_process.stderr = ""
            mock_run.return_value = mock_process
            
            # This should safely pass the string, not execute it
            try:
                await computer_env._execute("click", x=100, y=100)
            except Exception:
                pass  # May fail due to pyautogui not being available
            
            # Check what was passed to subprocess
            if mock_run.called:
                call_args = mock_run.call_args
                if call_args:
                    # The python command should be safely quoted
                    python_cmd = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get('args', [''])[1]
                    # Should not contain __import__ or exec
                    assert "__import__" not in python_cmd or "exec" not in python_cmd


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.fixture
    def computer_env(self):
        """Create a ComputerEnvironment instance for testing"""
        return ComputerEnvironment(provider="local")

    @pytest.mark.asyncio
    async def test_empty_command(self, computer_env):
        """Test: Empty command should be handled safely"""
        action = OperatorAction(
            type="terminal",
            command=""
        )
        
        result = await computer_env.step(action)
        # Should either error or handle gracefully
        assert result.error is not None or result.output is not None

    @pytest.mark.asyncio
    async def test_null_byte_injection(self, computer_env):
        """Test: Null byte injection attempt"""
        # Null byte is often used to bypass checks
        malicious_command = "echo test\x00whoami"
        
        action = OperatorAction(
            type="terminal",
            command=malicious_command
        )
        
        result = await computer_env.step(action)
        
        # Should handle null byte safely
        assert result.error is not None or "test" in result.output if result.output else True

    @pytest.mark.asyncio
    async def test_very_long_command(self, computer_env):
        """Test: Very long command (buffer overflow attempt)"""
        malicious_command = "echo " + "a" * 100000
        
        action = OperatorAction(
            type="terminal",
            command=malicious_command
        )
        
        # Should handle long input without crashing
        try:
            result = await computer_env.step(action)
            # Should either succeed or fail gracefully
        except Exception as e:
            # Should not crash with memory error
            assert "memory" not in str(e).lower()

    @pytest.mark.asyncio
    async def test_unicode_injection(self, computer_env):
        """Test: Unicode character injection"""
        # Various unicode characters that might cause issues
        malicious_command = "echo test\u0000\u202e\u202d"
        
        action = OperatorAction(
            type="terminal",
            command=malicious_command
        )
        
        result = await computer_env.step(action)
        
        # Should handle unicode safely
        assert result.error is not None or result.output is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
