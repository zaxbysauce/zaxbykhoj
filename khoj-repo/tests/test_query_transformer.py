"""
Tests for QueryTransformer class.

Tests step-back prompting query transformation with mock LLM responses.
"""

import pytest
from unittest.mock import MagicMock

from khoj.processor.query_transformer import QueryTransformer


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    return MagicMock()


@pytest.fixture
def transformer(mock_llm_client):
    """Create a QueryTransformer instance with mock client."""
    return QueryTransformer(
        llm_client=mock_llm_client,
        model_name="gpt-4o-mini",
        temperature=0.7,
        max_tokens=100,
    )


class TestQueryTransformerTransform:
    """Tests for the transform() method."""

    def test_transform_generates_step_back_query(self, transformer, mock_llm_client):
        """Test transform() returns both original and step-back query."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "What are popular programming languages?"
        mock_llm_client.chat.completions.create.return_value = mock_response

        result = transformer.transform("What is Python?")

        assert len(result) == 2
        assert result[0] == "What is Python?"
        assert result[1] == "What are popular programming languages?"

    def test_transform_step_back_broader_query(self, transformer, mock_llm_client):
        """Test transform() generates a broader step-back query."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "What are famous landmarks in Paris?"
        mock_llm_client.chat.completions.create.return_value = mock_response

        result = transformer.transform("What is the height of the Eiffel Tower?")

        assert result[0] == "What is the height of the Eiffel Tower?"
        assert "famous landmarks" in result[1] or "Paris" in result[1]

    def test_transform_handles_author_query(self, transformer, mock_llm_client):
        """Test transform() handles author/book query transformation."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Who are famous English novelists?"
        mock_llm_client.chat.completions.create.return_value = mock_response

        result = transformer.transform("Who wrote Pride and Prejudice?")

        assert result[0] == "Who wrote Pride and Prejudice?"
        assert "English novelists" in result[1] or "famous" in result[1]

    def test_transform_handles_technical_query(self, transformer, mock_llm_client):
        """Test transform() handles technical/engineering query."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "What are the types of internal combustion engines?"
        mock_llm_client.chat.completions.create.return_value = mock_response

        result = transformer.transform("How does a diesel engine work?")

        assert result[0] == "How does a diesel engine work?"
        assert "engines" in result[1].lower()


class TestQueryTransformerErrorHandling:
    """Tests for error handling in transform()."""

    def test_transform_llm_error_returns_original(self, transformer, mock_llm_client):
        """Test transform() returns [original_query] on LLM error."""
        mock_llm_client.chat.completions.create.side_effect = Exception("API Error")

        result = transformer.transform("What is Python?")

        assert len(result) == 1
        assert result[0] == "What is Python?"

    def test_transform_timeout_returns_original(self, transformer, mock_llm_client):
        """Test transform() returns [original_query] on timeout."""
        mock_llm_client.chat.completions.create.side_effect = TimeoutError("Request timed out")

        result = transformer.transform("What is Python?")

        assert len(result) == 1
        assert result[0] == "What is Python?"

    def test_transform_network_error_returns_original(self, transformer, mock_llm_client):
        """Test transform() returns [original_query] on network error."""
        mock_llm_client.chat.completions.create.side_effect = ConnectionError("Network error")

        result = transformer.transform("What is Python?")

        assert len(result) == 1
        assert result[0] == "What is Python?"

    def test_transform_empty_query_returns_empty_list(self, transformer):
        """Test transform() returns empty list for empty query."""
        result = transformer.transform("")

        assert result == []

    def test_transform_whitespace_only_query_returns_empty_list(self, transformer):
        """Test transform() returns empty list for whitespace-only query."""
        result = transformer.transform("   \t\n  ")

        assert result == []

    def test_transform_none_response_handled(self, transformer, mock_llm_client):
        """Test transform() handles None response gracefully."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_llm_client.chat.completions.create.return_value = mock_response

        result = transformer.transform("What is Python?")

        # Should return original query if response is None
        assert len(result) >= 1
        assert result[0] == "What is Python?"


class TestQueryTransformerParseResponse:
    """Tests for the _parse_response() method."""

    def test_parse_response_strips_whitespace(self, transformer):
        """Test _parse_response() strips leading/trailing whitespace."""
        result = transformer._parse_response("  What is Python?  ")

        assert result == "What is Python?"

    def test_parse_response_removes_double_quotes(self, transformer):
        """Test _parse_response() removes surrounding double quotes."""
        result = transformer._parse_response('"What is Python?"')

        assert result == "What is Python?"

    def test_parse_response_removes_single_quotes(self, transformer):
        """Test _parse_response() removes surrounding single quotes."""
        result = transformer._parse_response("'What is Python?'")

        assert result == "What is Python?"

    def test_parse_response_handles_mixed_quotes(self, transformer):
        """Test _parse_response() handles mismatched quotes."""
        # Only removes if both start and end with same quote type
        result = transformer._parse_response('"What is Python?\'')

        assert result == '"What is Python?\''

    def test_parse_response_empty_string(self, transformer):
        """Test _parse_response() handles empty string."""
        result = transformer._parse_response("")

        assert result == ""

    def test_parse_response_preserves_internal_quotes(self, transformer):
        """Test _parse_response() preserves quotes inside the text."""
        result = transformer._parse_response('"What is "Python" programming?"')

        assert result == 'What is "Python" programming?'


class TestQueryTransformerPromptBuilding:
    """Tests for prompt building."""

    def test_build_prompt_structure(self, transformer):
        """Test _build_prompt() creates proper message structure."""
        messages = transformer._build_prompt("What is Python?")

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "step-back prompting" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert "What is Python?" in messages[1]["content"]
        assert "Generate a broader" in messages[1]["content"]

    def test_build_prompt_includes_original_query(self, transformer):
        """Test _build_prompt() includes the original query in user message."""
        messages = transformer._build_prompt("How does machine learning work?")

        user_content = messages[1]["content"]
        assert "How does machine learning work?" in user_content


class TestQueryTransformerLLMCall:
    """Tests for LLM calling with retries."""

    def test_call_llm_parameters(self, transformer, mock_llm_client):
        """Test _call_llm() passes correct parameters to LLM."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Broader query"
        mock_llm_client.chat.completions.create.return_value = mock_response

        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "User prompt"},
        ]

        transformer._call_llm(messages)

        call_args = mock_llm_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-4o-mini"
        assert call_args[1]["messages"] == messages
        assert call_args[1]["temperature"] == 0.7
        assert call_args[1]["max_tokens"] == 100

    def test_call_llm_returns_content(self, transformer, mock_llm_client):
        """Test _call_llm() returns the response content."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Transformed query result"
        mock_llm_client.chat.completions.create.return_value = mock_response

        messages = [{"role": "user", "content": "Test"}]
        result = transformer._call_llm(messages)

        assert result == "Transformed query result"


class TestQueryTransformerConfiguration:
    """Tests for QueryTransformer configuration options."""

    def test_default_configuration(self, mock_llm_client):
        """Test QueryTransformer uses default configuration values."""
        transformer = QueryTransformer(llm_client=mock_llm_client)

        assert transformer.model_name == "gpt-4o-mini"
        assert transformer.temperature == 0.7
        assert transformer.max_tokens == 100

    def test_custom_configuration(self, mock_llm_client):
        """Test QueryTransformer accepts custom configuration values."""
        transformer = QueryTransformer(
            llm_client=mock_llm_client,
            model_name="gpt-4o",
            temperature=0.5,
            max_tokens=200,
        )

        assert transformer.model_name == "gpt-4o"
        assert transformer.temperature == 0.5
        assert transformer.max_tokens == 200

    def test_custom_model_in_llm_call(self, mock_llm_client):
        """Test custom model name is passed to LLM call."""
        transformer = QueryTransformer(
            llm_client=mock_llm_client,
            model_name="custom-model",
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Result"
        mock_llm_client.chat.completions.create.return_value = mock_response

        messages = [{"role": "user", "content": "Test"}]
        transformer._call_llm(messages)

        call_args = mock_llm_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "custom-model"

    def test_custom_temperature_in_llm_call(self, mock_llm_client):
        """Test custom temperature is passed to LLM call."""
        transformer = QueryTransformer(
            llm_client=mock_llm_client,
            temperature=0.9,
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Result"
        mock_llm_client.chat.completions.create.return_value = mock_response

        messages = [{"role": "user", "content": "Test"}]
        transformer._call_llm(messages)

        call_args = mock_llm_client.chat.completions.create.call_args
        assert call_args[1]["temperature"] == 0.9

    def test_custom_max_tokens_in_llm_call(self, mock_llm_client):
        """Test custom max_tokens is passed to LLM call."""
        transformer = QueryTransformer(
            llm_client=mock_llm_client,
            max_tokens=50,
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Result"
        mock_llm_client.chat.completions.create.return_value = mock_response

        messages = [{"role": "user", "content": "Test"}]
        transformer._call_llm(messages)

        call_args = mock_llm_client.chat.completions.create.call_args
        assert call_args[1]["max_tokens"] == 50


class TestQueryTransformerEdgeCases:
    """Tests for edge cases."""

    def test_transform_long_query(self, transformer, mock_llm_client):
        """Test transform() handles very long queries."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Broader version"
        mock_llm_client.chat.completions.create.return_value = mock_response

        long_query = "What is " + "Python " * 100
        result = transformer.transform(long_query)

        assert len(result) == 2
        assert result[0] == long_query
        assert result[1] == "Broader version"

    def test_transform_special_characters(self, transformer, mock_llm_client):
        """Test transform() handles queries with special characters."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "What are programming languages?"
        mock_llm_client.chat.completions.create.return_value = mock_response

        query = "What is Python (programming language) & how does it work?"
        result = transformer.transform(query)

        assert result[0] == query

    def test_transform_unicode_characters(self, transformer, mock_llm_client):
        """Test transform() handles queries with unicode characters."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "What are European landmarks?"
        mock_llm_client.chat.completions.create.return_value = mock_response

        query = "What is the height of the 埃菲尔铁塔?"
        result = transformer.transform(query)

        assert result[0] == query
