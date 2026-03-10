# tests/test_operator_platform_detection.py
"""Test that platform.system() is used for OS detection instead of hardcoded linux."""
from unittest.mock import MagicMock, patch

import pytest

from khoj.processor.operator.operator_agent_openai import OpenAIOperatorAgent
from khoj.processor.operator.operator_environment_base import EnvironmentType, EnvState


class TestPlatformSystemDetection:
    """Test that OS detection uses platform.system() instead of hardcoded values."""

    def _create_mock_agent(self, environment_type: EnvironmentType):
        """Create a mock agent with mocked ChatModel to avoid database access."""
        mock_model = MagicMock()
        mock_model.name = "computer-use-preview"
        return OpenAIOperatorAgent(
            query="test query",
            vision_model=mock_model,
            environment_type=environment_type,
            max_iterations=5,
            max_context=128000,
        )

    def test_platform_system_used_for_darwin(self):
        """Test that Darwin (macOS) is detected correctly via platform.system()."""
        with patch("khoj.processor.operator.operator_agent_openai.platform.system", return_value="Darwin"):
            agent = self._create_mock_agent(EnvironmentType.COMPUTER)
            state = EnvState(url="", width=1920, height=1080)
            tools = agent.get_tools(EnvironmentType.COMPUTER, state)

            # Verify environment_os is "mac" for Darwin
            computer_tool = tools[0]
            assert computer_tool["environment"] == "mac"

    def test_platform_system_used_for_windows(self):
        """Test that Windows is detected correctly via platform.system()."""
        with patch("khoj.processor.operator.operator_agent_openai.platform.system", return_value="Windows"):
            agent = self._create_mock_agent(EnvironmentType.COMPUTER)
            state = EnvState(url="", width=1920, height=1080)
            tools = agent.get_tools(EnvironmentType.COMPUTER, state)

            # Verify environment_os is "windows" for Windows
            computer_tool = tools[0]
            assert computer_tool["environment"] == "windows"

    def test_platform_system_used_for_linux(self):
        """Test that Linux is detected correctly via platform.system()."""
        with patch("khoj.processor.operator.operator_agent_openai.platform.system", return_value="Linux"):
            agent = self._create_mock_agent(EnvironmentType.COMPUTER)
            state = EnvState(url="", width=1920, height=1080)
            tools = agent.get_tools(EnvironmentType.COMPUTER, state)

            # Verify environment_os is "linux" for Linux
            computer_tool = tools[0]
            assert computer_tool["environment"] == "linux"

    def test_platform_system_not_hardcoded(self):
        """Test that the code uses platform.system() dynamically, not hardcoded value."""
        # This test verifies that the environment_os changes based on platform.system() return value
        # by checking that the implementation is NOT using a hardcoded string

        # If it were hardcoded, patching platform.system() wouldn't change the result
        with patch("khoj.processor.operator.operator_agent_openai.platform.system", return_value="Windows"):
            agent = self._create_mock_agent(EnvironmentType.COMPUTER)
            state = EnvState(url="", width=1920, height=1080)
            tools = agent.get_tools(EnvironmentType.COMPUTER, state)

            # This would fail if the code had hardcoded "linux"
            # because patching to return "Windows" would still produce "linux"
            assert tools[0]["environment"] != "linux", (
                "OS detection appears to be hardcoded to 'linux' instead of using platform.system()"
            )

    def test_browser_environment_uses_browser_not_os(self):
        """Test that BROWSER environment type uses 'browser' regardless of OS."""
        with patch("khoj.processor.operator.operator_agent_openai.platform.system", return_value="Windows"):
            agent = self._create_mock_agent(EnvironmentType.BROWSER)
            state = EnvState(url="https://example.com", width=1920, height=1080)
            tools = agent.get_tools(EnvironmentType.BROWSER, state)

            # Verify environment_os is "browser" for BROWSER type
            computer_tool = tools[0]
            assert computer_tool["environment"] == "browser"
