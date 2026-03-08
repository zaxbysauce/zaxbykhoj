"""
Tests for RetrievalEvaluator class.

Tests CRAG-style retrieval quality evaluation with mock LLM responses.
"""

import pytest
from unittest.mock import MagicMock, patch

from khoj.processor.retrieval_evaluator import (
    RetrievalEvaluator,
    RetrievalEvaluation,
    ChunkInfo,
)


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    return MagicMock()


@pytest.fixture
def evaluator(mock_llm_client):
    """Create a RetrievalEvaluator instance with mock client."""
    return RetrievalEvaluator(llm_client=mock_llm_client, model_name="gpt-4o-mini")


class TestRetrievalEvaluatorEvaluate:
    """Tests for the evaluate() method."""

    def test_evaluate_confident(self, evaluator, mock_llm_client):
        """Test evaluate() returns CONFIDENT when LLM responds with 'CONFIDENT'."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "CONFIDENT"
        mock_llm_client.chat.completions.create.return_value = mock_response

        # Test
        chunks = [{"content": "This is relevant information about Python programming."}]
        result = evaluator.evaluate("What is Python?", chunks)

        assert result == RetrievalEvaluation.CONFIDENT

    def test_evaluate_ambiguous(self, evaluator, mock_llm_client):
        """Test evaluate() returns AMBIGUOUS when LLM responds with 'AMBIGUOUS'."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "AMBIGUOUS"
        mock_llm_client.chat.completions.create.return_value = mock_response

        chunks = [{"content": "Some partial information."}]
        result = evaluator.evaluate("What is Python?", chunks)

        assert result == RetrievalEvaluation.AMBIGUOUS

    def test_evaluate_no_match(self, evaluator, mock_llm_client):
        """Test evaluate() returns NO_MATCH when LLM responds with 'NO_MATCH'."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "NO_MATCH"
        mock_llm_client.chat.completions.create.return_value = mock_response

        chunks = [{"content": "Completely unrelated content."}]
        result = evaluator.evaluate("What is Python?", chunks)

        assert result == RetrievalEvaluation.NO_MATCH

    def test_evaluate_empty_chunks(self, evaluator):
        """Test evaluate() returns NO_MATCH when no chunks provided."""
        result = evaluator.evaluate("What is Python?", [])

        assert result == RetrievalEvaluation.NO_MATCH

    def test_evaluate_chunks_with_text_key(self, evaluator, mock_llm_client):
        """Test evaluate() handles chunks with 'text' key instead of 'content'."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "CONFIDENT"
        mock_llm_client.chat.completions.create.return_value = mock_response

        chunks = [{"text": "This is relevant information."}]
        result = evaluator.evaluate("What is Python?", chunks)

        assert result == RetrievalEvaluation.CONFIDENT


class TestRetrievalEvaluatorParseResponse:
    """Tests for the _parse_response() method."""

    def test_parse_response_confident(self, evaluator):
        """Test _parse_response() correctly identifies CONFIDENT."""
        result = evaluator._parse_response("CONFIDENT")
        assert result == RetrievalEvaluation.CONFIDENT

    def test_parse_response_ambiguous(self, evaluator):
        """Test _parse_response() correctly identifies AMBIGUOUS."""
        result = evaluator._parse_response("AMBIGUOUS")
        assert result == RetrievalEvaluation.AMBIGUOUS

    def test_parse_response_no_match(self, evaluator):
        """Test _parse_response() correctly identifies NO_MATCH."""
        result = evaluator._parse_response("NO_MATCH")
        assert result == RetrievalEvaluation.NO_MATCH

    def test_parse_response_nomatch_no_underscore(self, evaluator):
        """Test _parse_response() handles NOMATCH without underscore."""
        result = evaluator._parse_response("NOMATCH")
        assert result == RetrievalEvaluation.NO_MATCH

    def test_parse_response_with_whitespace(self, evaluator):
        """Test _parse_response() handles whitespace in response."""
        result = evaluator._parse_response("  CONFIDENT  ")
        assert result == RetrievalEvaluation.CONFIDENT

    def test_parse_response_lowercase(self, evaluator):
        """Test _parse_response() handles lowercase response."""
        result = evaluator._parse_response("confident")
        assert result == RetrievalEvaluation.CONFIDENT

    def test_parse_response_with_punctuation(self, evaluator):
        """Test _parse_response() handles punctuation in response."""
        result = evaluator._parse_response("CONFIDENT!")
        assert result == RetrievalEvaluation.CONFIDENT

    def test_parse_response_unclear_defaults_to_ambiguous(self, evaluator):
        """Test _parse_response() defaults to AMBIGUOUS for unclear responses."""
        result = evaluator._parse_response("I think maybe it's relevant")
        assert result == RetrievalEvaluation.AMBIGUOUS

    def test_parse_response_empty_string(self, evaluator):
        """Test _parse_response() defaults to AMBIGUOUS for empty string."""
        result = evaluator._parse_response("")
        assert result == RetrievalEvaluation.AMBIGUOUS


class TestRetrievalEvaluatorErrorHandling:
    """Tests for error handling in evaluate()."""

    def test_evaluate_llm_error_defaults_to_ambiguous(self, evaluator, mock_llm_client):
        """Test evaluate() defaults to AMBIGUOUS on LLM error."""
        mock_llm_client.chat.completions.create.side_effect = Exception("API Error")

        chunks = [{"content": "Some content."}]
        result = evaluator.evaluate("What is Python?", chunks)

        assert result == RetrievalEvaluation.AMBIGUOUS

    def test_evaluate_timeout_defaults_to_ambiguous(self, evaluator, mock_llm_client):
        """Test evaluate() defaults to AMBIGUOUS on timeout."""
        mock_llm_client.chat.completions.create.side_effect = TimeoutError("Request timed out")

        chunks = [{"content": "Some content."}]
        result = evaluator.evaluate("What is Python?", chunks)

        assert result == RetrievalEvaluation.AMBIGUOUS

    def test_evaluate_network_error_defaults_to_ambiguous(self, evaluator, mock_llm_client):
        """Test evaluate() defaults to AMBIGUOUS on network error."""
        mock_llm_client.chat.completions.create.side_effect = ConnectionError("Network error")

        chunks = [{"content": "Some content."}]
        result = evaluator.evaluate("What is Python?", chunks)

        assert result == RetrievalEvaluation.AMBIGUOUS


class TestRetrievalEvaluatorWithFallback:
    """Tests for the evaluate_with_fallback() method."""

    def test_confident_fallback_returns_original_chunks(self, evaluator, mock_llm_client):
        """Test CONFIDENT evaluation returns original chunks without fallback."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "CONFIDENT"
        mock_llm_client.chat.completions.create.return_value = mock_response

        chunks = [{"content": "Python is a programming language."}]
        result_chunks, evaluation, warning = evaluator.evaluate_with_fallback(
            "What is Python?", chunks
        )

        assert evaluation == RetrievalEvaluation.CONFIDENT
        assert result_chunks == chunks
        assert warning is None

    def test_ambiguous_fallback_with_search_fn(self, evaluator, mock_llm_client):
        """Test AMBIGUOUS evaluation triggers re-search with search_fn."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "AMBIGUOUS"
        mock_llm_client.chat.completions.create.return_value = mock_response

        original_chunks = [{"content": "Some partial info."}]
        fallback_chunks = [
            {"content": "More comprehensive info."},
            {"content": "Additional context."},
        ]

        def mock_search_fn(query, threshold):
            return fallback_chunks

        result_chunks, evaluation, warning = evaluator.evaluate_with_fallback(
            "What is Python?", original_chunks, search_fn=mock_search_fn
        )

        assert evaluation == RetrievalEvaluation.AMBIGUOUS
        assert result_chunks == fallback_chunks
        assert warning is None

    def test_ambiguous_fallback_without_search_fn(self, evaluator, mock_llm_client):
        """Test AMBIGUOUS evaluation returns original chunks when no search_fn."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "AMBIGUOUS"
        mock_llm_client.chat.completions.create.return_value = mock_response

        chunks = [{"content": "Some content."}]
        result_chunks, evaluation, warning = evaluator.evaluate_with_fallback(
            "What is Python?", chunks
        )

        assert evaluation == RetrievalEvaluation.AMBIGUOUS
        assert result_chunks == chunks
        assert warning is None

    def test_no_match_fallback_returns_empty_and_warning(self, evaluator, mock_llm_client):
        """Test NO_MATCH evaluation returns empty list with warning."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "NO_MATCH"
        mock_llm_client.chat.completions.create.return_value = mock_response

        chunks = [{"content": "Irrelevant content."}]
        result_chunks, evaluation, warning = evaluator.evaluate_with_fallback(
            "What is Python?", chunks
        )

        assert evaluation == RetrievalEvaluation.NO_MATCH
        assert result_chunks == []
        assert warning is not None
        assert "NO_MATCH" in warning
        assert "What is Python?" in warning

    def test_ambiguous_fallback_search_error(self, evaluator, mock_llm_client):
        """Test AMBIGUOUS fallback handles search function errors gracefully."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "AMBIGUOUS"
        mock_llm_client.chat.completions.create.return_value = mock_response

        original_chunks = [{"content": "Some content."}]

        def mock_search_fn_with_error(query, threshold):
            raise Exception("Search service unavailable")

        result_chunks, evaluation, warning = evaluator.evaluate_with_fallback(
            "What is Python?", original_chunks, search_fn=mock_search_fn_with_error
        )

        assert evaluation == RetrievalEvaluation.AMBIGUOUS
        assert result_chunks == original_chunks  # Should return original on error
        assert warning is None

    def test_ambiguous_fallback_empty_research_results(self, evaluator, mock_llm_client):
        """Test AMBIGUOUS fallback when re-search returns empty results."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "AMBIGUOUS"
        mock_llm_client.chat.completions.create.return_value = mock_response

        original_chunks = [{"content": "Some content."}]

        def mock_search_fn_returns_empty(query, threshold):
            return []

        result_chunks, evaluation, warning = evaluator.evaluate_with_fallback(
            "What is Python?", original_chunks, search_fn=mock_search_fn_returns_empty
        )

        assert evaluation == RetrievalEvaluation.AMBIGUOUS
        assert result_chunks == original_chunks  # Should return original if no new results
        assert warning is None

    def test_confident_fallback_with_custom_threshold(self, evaluator, mock_llm_client):
        """Test CONFIDENT evaluation ignores custom threshold parameter."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "CONFIDENT"
        mock_llm_client.chat.completions.create.return_value = mock_response

        chunks = [{"content": "Python info."}]

        search_calls = []

        def mock_search_fn(query, threshold):
            search_calls.append(threshold)
            return [{"content": "fallback"}]

        result_chunks, evaluation, warning = evaluator.evaluate_with_fallback(
            "What is Python?", chunks, search_fn=mock_search_fn, lower_threshold=0.2
        )

        assert evaluation == RetrievalEvaluation.CONFIDENT
        assert len(search_calls) == 0  # Search should not be called for CONFIDENT

    def test_ambiguous_fallback_custom_lower_threshold(self, evaluator, mock_llm_client):
        """Test AMBIGUOUS fallback uses custom lower_threshold parameter."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "AMBIGUOUS"
        mock_llm_client.chat.completions.create.return_value = mock_response

        chunks = [{"content": "Some content."}]

        received_threshold = None

        def mock_search_fn(query, threshold):
            nonlocal received_threshold
            received_threshold = threshold
            return [{"content": "fallback"}]

        evaluator.evaluate_with_fallback(
            "What is Python?", chunks, search_fn=mock_search_fn, lower_threshold=0.15
        )

        assert received_threshold == 0.15

    def test_no_match_fallback_does_not_call_search(self, evaluator, mock_llm_client):
        """Test NO_MATCH evaluation does not trigger re-search."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "NO_MATCH"
        mock_llm_client.chat.completions.create.return_value = mock_response

        chunks = [{"content": "Irrelevant content."}]

        search_called = False

        def mock_search_fn(query, threshold):
            nonlocal search_called
            search_called = True
            return [{"content": "fallback"}]

        result_chunks, evaluation, warning = evaluator.evaluate_with_fallback(
            "What is Python?", chunks, search_fn=mock_search_fn
        )

        assert search_called is False
        assert result_chunks == []


class TestRetrievalEvaluatorPromptBuilding:
    """Tests for prompt building and truncation."""

    def test_truncate_long_chunk(self, evaluator):
        """Test _truncate_chunk() truncates content exceeding MAX_CHUNK_LENGTH."""
        long_content = "A" * 1000
        chunk = {"content": long_content}

        result = evaluator._truncate_chunk(chunk)

        assert len(result) == evaluator.MAX_CHUNK_LENGTH + 3  # +3 for "..."
        assert result.endswith("...")

    def test_truncate_short_chunk_unchanged(self, evaluator):
        """Test _truncate_chunk() does not modify short content."""
        short_content = "Short content"
        chunk = {"content": short_content}

        result = evaluator._truncate_chunk(chunk)

        assert result == short_content

    def test_truncate_chunk_with_string_input(self, evaluator):
        """Test _truncate_chunk() handles string input directly."""
        long_string = "B" * 1000

        result = evaluator._truncate_chunk(long_string)

        assert len(result) == evaluator.MAX_CHUNK_LENGTH + 3
        assert result.endswith("...")

    def test_build_prompt_limits_chunks(self, evaluator):
        """Test _build_prompt() limits to MAX_CHUNKS."""
        chunks = [{"content": f"Content {i}"} for i in range(10)]

        messages = evaluator._build_prompt("Query?", chunks)

        user_message = messages[1]["content"]
        # Should only have MAX_CHUNKS chunks in the prompt
        chunk_count = user_message.count("Chunk ")
        assert chunk_count == evaluator.MAX_CHUNKS

    def test_build_prompt_structure(self, evaluator):
        """Test _build_prompt() creates proper message structure."""
        chunks = [{"content": "Test content."}]

        messages = evaluator._build_prompt("What is Python?", chunks)

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "What is Python?" in messages[1]["content"]
        assert "Test content" in messages[1]["content"]


class TestRetrievalEvaluatorChunkInfo:
    """Tests for ChunkInfo dataclass."""

    def test_chunk_info_creation(self):
        """Test ChunkInfo can be created with content and score."""
        chunk = ChunkInfo(content="Test content", score=0.95)

        assert chunk.content == "Test content"
        assert chunk.score == 0.95

    def test_chunk_info_default_score(self):
        """Test ChunkInfo defaults score to None."""
        chunk = ChunkInfo(content="Test content")

        assert chunk.content == "Test content"
        assert chunk.score is None

    def test_chunk_info_handles_none_content(self):
        """Test ChunkInfo handles None content in post_init."""
        chunk = ChunkInfo(content=None)

        assert chunk.content == ""

    def test_chunk_info_empty_string_content(self):
        """Test ChunkInfo handles empty string content."""
        chunk = ChunkInfo(content="")

        assert chunk.content == ""


class TestRetrievalEvaluatorLLMCall:
    """Tests for LLM calling with retries."""

    def test_call_llm_parameters(self, evaluator, mock_llm_client):
        """Test _call_llm() passes correct parameters to LLM."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "CONFIDENT"
        mock_llm_client.chat.completions.create.return_value = mock_response

        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "User prompt"},
        ]

        evaluator._call_llm(messages)

        call_args = mock_llm_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-4o-mini"
        assert call_args[1]["messages"] == messages
        assert call_args[1]["temperature"] == evaluator.DEFAULT_TEMPERATURE
        assert call_args[1]["max_tokens"] == 10
