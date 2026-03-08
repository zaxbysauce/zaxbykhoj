import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from openai import OpenAI

logger = logging.getLogger(__name__)


class RetrievalEvaluation(Enum):
    """CRAG-style evaluation of retrieval quality."""

    CONFIDENT = "CONFIDENT"
    AMBIGUOUS = "AMBIGUOUS"
    NO_MATCH = "NO_MATCH"


@dataclass
class ChunkInfo:
    """Represents a retrieved chunk with its content."""

    content: str
    score: Optional[float] = None

    def __post_init__(self):
        if self.content is None:
            self.content = ""


class RetrievalEvaluator:
    """
    CRAG-style evaluator for assessing retrieval quality.

    Uses an LLM to classify whether retrieved chunks are relevant to the query.
    """

    SYSTEM_PROMPT = """You are a retrieval quality evaluator. Your task is to assess whether the retrieved document chunks are relevant and sufficient to answer the user's query.

Classify the retrieval quality as one of:
- CONFIDENT: The chunks contain clear, sufficient information to answer the query
- AMBIGUOUS: The chunks contain partial or unclear information that may help answer the query but may not be sufficient
- NO_MATCH: The chunks do not contain relevant information to answer the query

Respond with only one word: CONFIDENT, AMBIGUOUS, or NO_MATCH."""

    MAX_CHUNK_LENGTH = 500
    MAX_CHUNKS = 3
    DEFAULT_TEMPERATURE = 0.0

    def __init__(self, llm_client: OpenAI, model_name: str = "gpt-4o-mini"):
        """
        Initialize the retrieval evaluator.

        Args:
            llm_client: OpenAI-compatible client for making LLM calls
            model_name: Name of the model to use for evaluation (default: gpt-4o-mini)
        """
        self.llm_client = llm_client
        self.model_name = model_name

    def _truncate_chunk(self, chunk: dict) -> str:
        """Extract and truncate chunk content to MAX_CHUNK_LENGTH characters."""
        # Handle both dict with 'content' key and string input
        if isinstance(chunk, dict):
            content = chunk.get("content", "") or chunk.get("text", "")
        else:
            content = str(chunk)

        if len(content) > self.MAX_CHUNK_LENGTH:
            return content[: self.MAX_CHUNK_LENGTH] + "..."
        return content

    def _build_prompt(self, query: str, chunks: List[dict]) -> List[dict]:
        """Build the messages for the LLM call."""
        # Take top chunks and truncate them
        top_chunks = chunks[: self.MAX_CHUNKS]
        truncated_chunks = [self._truncate_chunk(chunk) for chunk in top_chunks]

        # Build user message
        chunks_text = "\n\n".join(
            [f"Chunk {i + 1}:\n{content}" for i, content in enumerate(truncated_chunks)]
        )

        user_message = f"""Query: {query}

Retrieved Chunks:
{chunks_text}

Based on the query and retrieved chunks, classify the retrieval quality as CONFIDENT, AMBIGUOUS, or NO_MATCH."""

        return [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

    def _parse_response(self, response_text: str) -> RetrievalEvaluation:
        """Parse the LLM response to get the evaluation result."""
        # Clean and normalize the response
        cleaned = response_text.strip().upper()

        # Remove any punctuation or extra whitespace
        cleaned = cleaned.replace(".", "").replace("!", "").replace("?", "").strip()

        # Map to enum values using exact matching
        if cleaned == "CONFIDENT":
            return RetrievalEvaluation.CONFIDENT
        elif cleaned == "AMBIGUOUS":
            return RetrievalEvaluation.AMBIGUOUS
        elif cleaned == "NO_MATCH":
            return RetrievalEvaluation.NO_MATCH
        else:
            # Default to AMBIGUOUS if response is unclear
            logger.warning(f"Unclear evaluation response: '{response_text}'. Defaulting to AMBIGUOUS.")
            return RetrievalEvaluation.AMBIGUOUS

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
            temperature=self.DEFAULT_TEMPERATURE,
            max_tokens=10,  # We only need a single word response
            timeout=30,
        )
        return response.choices[0].message.content

    def evaluate(self, query: str, chunks: List[dict]) -> RetrievalEvaluation:
        """
        Evaluate the quality of retrieved chunks for the given query.

        Args:
            query: The user's search query
            chunks: List of retrieved chunk dictionaries, each containing at least a 'content' or 'text' key

        Returns:
            RetrievalEvaluation enum value indicating the quality assessment
        """
        if not chunks:
            logger.debug("No chunks provided for evaluation, returning NO_MATCH")
            return RetrievalEvaluation.NO_MATCH

        try:
            messages = self._build_prompt(query, chunks)
            response_text = self._call_llm(messages)
            result = self._parse_response(response_text)
            logger.debug(f"Retrieval evaluation for query '{query[:50]}...': {result.value}")
            return result
        except Exception as e:
            logger.error(f"Error during retrieval evaluation: {e}")
            # On error, default to AMBIGUOUS to allow for fallback handling upstream
            return RetrievalEvaluation.AMBIGUOUS

    def evaluate_with_fallback(
        self,
        query: str,
        chunks: List[dict],
        search_fn: Optional[callable] = None,
        lower_threshold: float = 0.3,
    ) -> tuple[List[dict], RetrievalEvaluation, Optional[str]]:
        """
        Evaluate retrieval quality and apply fallback actions based on CRAG classification.

        Fallback actions:
        - CONFIDENT: Return the original chunks as-is
        - AMBIGUOUS: Lower the similarity threshold and re-search if search_fn provided
        - NO_MATCH: Return empty list with a warning message

        Args:
            query: The user's search query
            chunks: List of retrieved chunk dictionaries
            search_fn: Optional callable for re-searching with lower threshold (query, threshold) -> chunks
            lower_threshold: The lowered threshold to use for AMBIGUOUS re-search (default: 0.3)

        Returns:
            Tuple of (filtered_chunks, evaluation, warning_message)
            - filtered_chunks: The chunks to use (original, re-searched, or empty)
            - evaluation: The CRAG classification result
            - warning_message: Optional warning message (for NO_MATCH case)
        """
        evaluation = self.evaluate(query, chunks)

        if evaluation == RetrievalEvaluation.CONFIDENT:
            # Return original chunks, no fallback needed
            return chunks, evaluation, None

        elif evaluation == RetrievalEvaluation.AMBIGUOUS:
            # Lower threshold and re-search if search function is available
            if search_fn is not None:
                try:
                    logger.debug(f"AMBIGUOUS evaluation: re-searching with lower threshold {lower_threshold}")
                    re_search_chunks = search_fn(query, lower_threshold)
                    if re_search_chunks:
                        logger.debug(f"Re-search found {len(re_search_chunks)} chunks with lower threshold")
                        return re_search_chunks, evaluation, None
                    else:
                        logger.warning("Re-search with lower threshold returned no results")
                except Exception as e:
                    logger.error(f"Error during AMBIGUOUS fallback re-search: {e}")
            # If re-search fails or no search_fn, return original chunks
            return chunks, evaluation, None

        elif evaluation == RetrievalEvaluation.NO_MATCH:
            # Return empty list with warning
            warning_msg = f"Retrieval evaluation: NO_MATCH for query '{query[:50]}...' - no relevant documents found"
            logger.warning(warning_msg)
            return [], evaluation, warning_msg

        # Should not reach here, but return original chunks as safe default
        return chunks, evaluation, None
