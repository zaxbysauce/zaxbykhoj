# tests/test_query_images_edge_cases.py
"""Adversarial tests for query_images parameter handling."""
import pytest
from unittest.mock import MagicMock

from khoj.processor.operator.operator_agent_base import OperatorAgent
from khoj.processor.operator.operator_environment_base import EnvironmentType


class MockOperatorAgent(OperatorAgent):
    """Mock implementation for testing."""
    async def act(self, current_state):
        pass


class TestQueryImagesEdgeCases:
    """Test query_images parameter edge cases."""

    def _create_mock_agent(self, query_images=None):
        """Create a mock agent with mocked ChatModel."""
        mock_model = MagicMock()
        mock_model.name = "claude-sonnet-4-20250514"
        return MockOperatorAgent(
            query="test query",
            vision_model=mock_model,
            environment_type=EnvironmentType.COMPUTER,
            max_iterations=5,
            max_context=128000,
            query_images=query_images,
        )

    def test_query_images_empty_list(self):
        """Test that empty list is handled without error."""
        agent = self._create_mock_agent(query_images=[])
        # Should not raise, empty list should be treated as no images
        assert agent.query_images == []

    def test_query_images_none(self):
        """Test that None is handled without error."""
        agent = self._create_mock_agent(query_images=None)
        # Should not raise, None should be treated as no images
        assert agent.query_images is None
