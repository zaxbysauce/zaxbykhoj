import asyncio
import logging
from typing import List

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from openai import OpenAI

logger = logging.getLogger(__name__)


class ContextualChunker:
    """
    Generates LLM summaries of chunks to provide contextual context.

    Uses an LLM to generate 1-2 sentence summaries capturing the main idea
    of each chunk, which can be used for contextual chunking in retrieval.
    """

    SYSTEM_PROMPT = """Summarize the following text fragment in 1-2 sentences, capturing its main idea"""

    DEFAULT_MODEL = "gpt-4o-mini"
    DEFAULT_TEMPERATURE = 0.0
    DEFAULT_MAX_TOKENS = 60
    MAX_RETRIES = 3
    MAX_CONCURRENT = 5

    def __init__(
        self,
        llm_client: OpenAI,
        model_name: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        """
        Initialize the contextual chunker.

        Args:
            llm_client: OpenAI-compatible client for making LLM calls
            model_name: Name of the model to use for summarization (default: gpt-4o-mini)
            temperature: Temperature for LLM sampling (default: 0.0)
            max_tokens: Maximum tokens for the response (default: 60)
        """
        self.llm_client = llm_client
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT)

    def _build_prompt(self, chunk_text: str) -> List[dict]:
        """Build the messages for the LLM call."""
        return [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": chunk_text},
        ]

    def _parse_response(self, response_text: str) -> str:
        """Parse and clean the LLM response."""
        # Clean the response by stripping whitespace
        cleaned = response_text.strip()
        return cleaned

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_random_exponential(multiplier=1, max=10),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.DEBUG),
    )
    def _call_llm(self, messages: List[dict]) -> str:
        """Make the LLM call with retry logic."""
        response = self.llm_client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content

    def summarize_chunk(self, chunk_text: str) -> str:
        """
        Summarize a single chunk into 1-2 sentences.

        Args:
            chunk_text: The text content of the chunk to summarize

        Returns:
            A 1-2 sentence summary of the chunk, or empty string on error
        """
        if not chunk_text or not chunk_text.strip():
            logger.debug("Empty chunk text provided, returning empty string")
            return ""

        try:
            messages = self._build_prompt(chunk_text)
            response_text = self._call_llm(messages)
            summary = self._parse_response(response_text)

            logger.debug(f"Chunk summarization: '{chunk_text[:50]}...' -> '{summary[:50]}...'")

            return summary
        except Exception as e:
            logger.error(f"Error during chunk summarization: {e}")
            # On error, return empty string
            return ""

    async def _summarize_chunk_async(self, chunk_text: str) -> str:
        """
        Async helper to summarize a single chunk with rate limiting.

        Args:
            chunk_text: The text content of the chunk to summarize

        Returns:
            A 1-2 sentence summary of the chunk, or empty string on error
        """
        async with self._semaphore:
            # Run the synchronous _call_llm in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            if not chunk_text or not chunk_text.strip():
                logger.debug("Empty chunk text provided, returning empty string")
                return ""

            try:
                messages = self._build_prompt(chunk_text)
                response_text = await loop.run_in_executor(
                    None, self._call_llm, messages
                )
                summary = self._parse_response(response_text)

                logger.debug(f"Chunk summarization: '{chunk_text[:50]}...' -> '{summary[:50]}...'")

                return summary
            except Exception as e:
                logger.error(f"Error during chunk summarization: {e}")
                # On error, return empty string
                return ""

    async def summarize_chunks(self, chunk_texts: List[str]) -> List[str]:
        """
        Summarize multiple chunks in parallel with rate limiting.

        Args:
            chunk_texts: List of chunk texts to summarize

        Returns:
            List of summaries, one per chunk. Empty strings for failed summaries.
        """
        if not chunk_texts:
            logger.debug("Empty chunk texts list provided, returning empty list")
            return []

        # Create tasks for all chunks
        tasks = [
            self._summarize_chunk_async(chunk_text)
            for chunk_text in chunk_texts
        ]

        # Run all tasks concurrently (rate limited by semaphore)
        summaries = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert any exceptions to empty strings
        results = []
        for i, summary in enumerate(summaries):
            if isinstance(summary, Exception):
                logger.error(f"Error summarizing chunk {i}: {summary}")
                results.append("")
            else:
                results.append(summary)

        logger.debug(f"Summarized {len(chunk_texts)} chunks")

        return results
