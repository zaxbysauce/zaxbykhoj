"""
Tests for ContextualChunker class.

Tests LLM-based chunk summarization with mock responses.
"""

import asyncio
import pytest
from unittest.mock import MagicMock, patch

from khoj.processor.contextual_chunker import ContextualChunker


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    return MagicMock()


@pytest.fixture
def chunker(mock_llm_client):
    """Create a ContextualChunker instance with mock client."""
    return ContextualChunker(
        llm_client=mock_llm_client,
        model_name="gpt-4o-mini",
        temperature=0.0,
        max_tokens=60,
    )


class TestSummarizeChunkBasic:
    """Tests for basic summarization with summarize_chunk()."""

    def test_summarize_chunk_returns_summary(self, chunker, mock_llm_client):
        """Test summarize_chunk() returns a summary for valid input."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is a concise summary of the chunk."
        mock_llm_client.chat.completions.create.return_value = mock_response

        chunk_text = "This is a long piece of text that needs to be summarized into a shorter form."
        result = chunker.summarize_chunk(chunk_text)

        assert result == "This is a concise summary of the chunk."

    def test_summarize_chunk_with_short_text(self, chunker, mock_llm_client):
        """Test summarize_chunk() handles short text input."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Brief summary."
        mock_llm_client.chat.completions.create.return_value = mock_response

        chunk_text = "Short text."
        result = chunker.summarize_chunk(chunk_text)

        assert result == "Brief summary."

    def test_summarize_chunk_with_long_text(self, chunker, mock_llm_client):
        """Test summarize_chunk() handles long text input."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Summary of lengthy document."
        mock_llm_client.chat.completions.create.return_value = mock_response

        chunk_text = "This is a very long text. " * 100
        result = chunker.summarize_chunk(chunk_text)

        assert result == "Summary of lengthy document."


class TestSummarizeChunksBatch:
    """Tests for batch async operations with summarize_chunks()."""

    @pytest.mark.asyncio
    async def test_summarize_chunks_processes_multiple(self, chunker, mock_llm_client):
        """Test summarize_chunks() processes multiple chunks."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Summary"
        mock_llm_client.chat.completions.create.return_value = mock_response

        chunk_texts = [
            "First chunk of text.",
            "Second chunk of text.",
            "Third chunk of text.",
        ]
        results = await chunker.summarize_chunks(chunk_texts)

        assert len(results) == 3
        assert all(r == "Summary" for r in results)

    @pytest.mark.asyncio
    async def test_summarize_chunks_respects_rate_limit(self, chunker, mock_llm_client):
        """Test summarize_chunks() respects rate limit via semaphore."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Summary"
        mock_llm_client.chat.completions.create.return_value = mock_response

        # Create more chunks than MAX_CONCURRENT to test rate limiting
        chunk_texts = [f"Chunk {i}" for i in range(10)]

        # Track concurrent executions
        concurrent_count = 0
        max_concurrent = 0

        original_call = chunker._call_llm

        def tracking_call(messages):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            try:
                return original_call(messages)
            finally:
                concurrent_count -= 1

        with patch.object(chunker, '_call_llm', side_effect=tracking_call):
            await chunker.summarize_chunks(chunk_texts)

        # Should not exceed MAX_CONCURRENT (5)
        assert max_concurrent <= chunker.MAX_CONCURRENT

    @pytest.mark.asyncio
    async def test_summarize_chunks_returns_list_of_summaries(self, chunker, mock_llm_client):
        """Test summarize_chunks() returns list matching input length."""
        responses = ["Summary 1", "Summary 2", "Summary 3"]

        def mock_create(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            # Return different summary for each call
            call_count = mock_llm_client.chat.completions.create.call_count
            mock_response.choices[0].message.content = responses[call_count % len(responses)]
            return mock_response

        mock_llm_client.chat.completions.create.side_effect = mock_create

        chunk_texts = ["Chunk one.", "Chunk two.", "Chunk three."]
        results = await chunker.summarize_chunks(chunk_texts)

        assert isinstance(results, list)
        assert len(results) == len(chunk_texts)
        assert all(isinstance(r, str) for r in results)


class TestContextualChunkerErrorHandling:
    """Tests for error handling scenarios."""

    def test_summarize_chunk_handles_llm_error(self, chunker, mock_llm_client):
        """Test summarize_chunk() returns empty string on LLM error."""
        mock_llm_client.chat.completions.create.side_effect = Exception("API Error")

        result = chunker.summarize_chunk("Some text to summarize.")

        assert result == ""

    def test_summarize_chunk_handles_timeout(self, chunker, mock_llm_client):
        """Test summarize_chunk() returns empty string on timeout."""
        mock_llm_client.chat.completions.create.side_effect = TimeoutError("Request timed out")

        result = chunker.summarize_chunk("Some text to summarize.")

        assert result == ""

    def test_summarize_chunk_handles_empty_response(self, chunker, mock_llm_client):
        """Test summarize_chunk() handles empty response from LLM."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ""
        mock_llm_client.chat.completions.create.return_value = mock_response

        result = chunker.summarize_chunk("Some text to summarize.")

        assert result == ""

    @pytest.mark.asyncio
    async def test_summarize_chunks_handles_partial_failures(self, chunker, mock_llm_client):
        """Test summarize_chunks() handles some failures gracefully."""
        call_count = 0

        def mock_create(*args, **kwargs):
            nonlocal call_count
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            call_count += 1
            if call_count == 2:
                raise Exception("Simulated failure")
            mock_response.choices[0].message.content = f"Summary {call_count}"
            return mock_response

        mock_llm_client.chat.completions.create.side_effect = mock_create

        chunk_texts = ["Chunk 1", "Chunk 2", "Chunk 3"]
        results = await chunker.summarize_chunks(chunk_texts)

        assert len(results) == 3
        assert results[0] == "Summary 1"
        assert results[1] == ""  # Failed chunk returns empty string
        assert results[2] == "Summary 3"


class TestContextualChunkerConfiguration:
    """Tests for configuration options."""

    def test_custom_model_name(self, mock_llm_client):
        """Test ContextualChunker accepts custom model name."""
        custom_chunker = ContextualChunker(
            llm_client=mock_llm_client,
            model_name="custom-model-v1",
        )

        assert custom_chunker.model_name == "custom-model-v1"

    def test_custom_temperature(self, mock_llm_client):
        """Test ContextualChunker accepts custom temperature."""
        custom_chunker = ContextualChunker(
            llm_client=mock_llm_client,
            temperature=0.5,
        )

        assert custom_chunker.temperature == 0.5

    def test_custom_max_tokens(self, mock_llm_client):
        """Test ContextualChunker accepts custom max_tokens."""
        custom_chunker = ContextualChunker(
            llm_client=mock_llm_client,
            max_tokens=100,
        )

        assert custom_chunker.max_tokens == 100

    def test_custom_model_in_llm_call(self, mock_llm_client):
        """Test custom model name is passed to LLM call."""
        custom_chunker = ContextualChunker(
            llm_client=mock_llm_client,
            model_name="gpt-4o",
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Summary"
        mock_llm_client.chat.completions.create.return_value = mock_response

        custom_chunker.summarize_chunk("Test chunk")

        call_args = mock_llm_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-4o"

    def test_custom_temperature_in_llm_call(self, mock_llm_client):
        """Test custom temperature is passed to LLM call."""
        custom_chunker = ContextualChunker(
            llm_client=mock_llm_client,
            temperature=0.3,
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Summary"
        mock_llm_client.chat.completions.create.return_value = mock_response

        custom_chunker.summarize_chunk("Test chunk")

        call_args = mock_llm_client.chat.completions.create.call_args
        assert call_args[1]["temperature"] == 0.3

    def test_custom_max_tokens_in_llm_call(self, mock_llm_client):
        """Test custom max_tokens is passed to LLM call."""
        custom_chunker = ContextualChunker(
            llm_client=mock_llm_client,
            max_tokens=120,
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Summary"
        mock_llm_client.chat.completions.create.return_value = mock_response

        custom_chunker.summarize_chunk("Test chunk")

        call_args = mock_llm_client.chat.completions.create.call_args
        assert call_args[1]["max_tokens"] == 120


class TestSummarizeChunkEdgeCases:
    """Tests for edge cases."""

    def test_empty_string_input(self, chunker):
        """Test summarize_chunk() handles empty string input."""
        result = chunker.summarize_chunk("")

        assert result == ""

    def test_whitespace_only_input(self, chunker):
        """Test summarize_chunk() handles whitespace-only input."""
        result = chunker.summarize_chunk("   \t\n  ")

        assert result == ""

    def test_very_long_text_truncation(self, chunker, mock_llm_client):
        """Test summarize_chunk() handles very long text."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Summary of long text."
        mock_llm_client.chat.completions.create.return_value = mock_response

        very_long_text = "A" * 10000
        result = chunker.summarize_chunk(very_long_text)

        assert result == "Summary of long text."

    def test_special_characters(self, chunker, mock_llm_client):
        """Test summarize_chunk() handles special characters."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Summary with special chars handled."
        mock_llm_client.chat.completions.create.return_value = mock_response

        special_text = "Test with special chars: @#$%^&*()_+{}[]|;':\",./<>?"
        result = chunker.summarize_chunk(special_text)

        assert result == "Summary with special chars handled."

    @pytest.mark.asyncio
    async def test_empty_list_input(self, chunker):
        """Test summarize_chunks() handles empty list input."""
        result = await chunker.summarize_chunks([])

        assert result == []

    @pytest.mark.asyncio
    async def test_single_item_list(self, chunker, mock_llm_client):
        """Test summarize_chunks() handles single item list."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Single summary."
        mock_llm_client.chat.completions.create.return_value = mock_response

        result = await chunker.summarize_chunks(["Only one chunk."])

        assert result == ["Single summary."]

    def test_unicode_characters(self, chunker, mock_llm_client):
        """Test summarize_chunk() handles unicode characters."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Unicode summary."
        mock_llm_client.chat.completions.create.return_value = mock_response

        unicode_text = "Unicode text: 你好世界 🌍 émojis ñoño"
        result = chunker.summarize_chunk(unicode_text)

        assert result == "Unicode summary."


class TestContextualChunkerPromptBuilding:
    """Tests for prompt building."""

    def test_build_prompt_structure(self, chunker):
        """Test _build_prompt() creates proper message structure."""
        messages = chunker._build_prompt("Test chunk text.")

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "Summarize" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Test chunk text."

    def test_build_prompt_includes_chunk_text(self, chunker):
        """Test _build_prompt() includes the chunk text in user message."""
        chunk_text = "This is the content to summarize."
        messages = chunker._build_prompt(chunk_text)

        assert messages[1]["content"] == chunk_text


class TestContextualChunkerParseResponse:
    """Tests for response parsing."""

    def test_parse_response_strips_whitespace(self, chunker):
        """Test _parse_response() strips leading/trailing whitespace."""
        result = chunker._parse_response("  Summary with spaces  ")

        assert result == "Summary with spaces"

    def test_parse_response_preserves_internal_whitespace(self, chunker):
        """Test _parse_response() preserves internal whitespace."""
        result = chunker._parse_response("Summary with  multiple   spaces")

        assert result == "Summary with  multiple   spaces"

    def test_parse_response_empty_string(self, chunker):
        """Test _parse_response() handles empty string."""
        result = chunker._parse_response("")

        assert result == ""


class TestContextualChunkerLLMCall:
    """Tests for LLM calling with retries."""

    def test_call_llm_parameters(self, chunker, mock_llm_client):
        """Test _call_llm() passes correct parameters to LLM."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Summary"
        mock_llm_client.chat.completions.create.return_value = mock_response

        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "User prompt"},
        ]

        chunker._call_llm(messages)

        call_args = mock_llm_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-4o-mini"
        assert call_args[1]["messages"] == messages
        assert call_args[1]["temperature"] == 0.0
        assert call_args[1]["max_tokens"] == 60

    def test_call_llm_returns_content(self, chunker, mock_llm_client):
        """Test _call_llm() returns the response content."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "The summary result"
        mock_llm_client.chat.completions.create.return_value = mock_response

        messages = [{"role": "user", "content": "Test"}]
        result = chunker._call_llm(messages)

        assert result == "The summary result"


class TestContextualChunkerRetryLogic:
    """Tests for retry logic with tenacity."""

    def test_retry_on_exception(self, chunker, mock_llm_client):
        """Test _call_llm() retries on exception."""
        mock_llm_client.chat.completions.create.side_effect = [
            Exception("Temporary error"),
            Exception("Another error"),
            MagicMock(choices=[MagicMock(message=MagicMock(content="Success after retries"))]),
        ]

        messages = [{"role": "user", "content": "Test"}]
        result = chunker._call_llm(messages)

        assert result == "Success after retries"
        assert mock_llm_client.chat.completions.create.call_count == 3

    def test_retry_exhausted_returns_error(self, chunker, mock_llm_client):
        """Test that after max retries, the exception propagates."""
        mock_llm_client.chat.completions.create.side_effect = Exception("Persistent error")

        messages = [{"role": "user", "content": "Test"}]

        with pytest.raises(Exception, match="Persistent error"):
            chunker._call_llm(messages)

        assert mock_llm_client.chat.completions.create.call_count == chunker.MAX_RETRIES


class TestContextualChunkerAsyncHelper:
    """Tests for async helper method."""

    @pytest.mark.asyncio
    async def test_async_helper_respects_semaphore(self, chunker, mock_llm_client):
        """Test _summarize_chunk_async() respects semaphore limit."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Async summary"
        mock_llm_client.chat.completions.create.return_value = mock_response

        result = await chunker._summarize_chunk_async("Test chunk")

        assert result == "Async summary"

    @pytest.mark.asyncio
    async def test_async_helper_empty_input(self, chunker):
        """Test _summarize_chunk_async() handles empty input."""
        result = await chunker._summarize_chunk_async("")

        assert result == ""

    @pytest.mark.asyncio
    async def test_async_helper_whitespace_input(self, chunker):
        """Test _summarize_chunk_async() handles whitespace-only input."""
        result = await chunker._summarize_chunk_async("   ")

        assert result == ""
