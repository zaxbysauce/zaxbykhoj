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


class QueryTransformer:
    """
    Step-back prompting query transformer for CRAG.

    Generates broader, more general versions of user queries to improve retrieval coverage.
    This is useful when the original query is too specific and might miss relevant context.
    """

    SYSTEM_PROMPT = """You are a query transformation assistant. Your task is to generate a broader, more general version of the user's query using step-back prompting.

Step-back prompting means:
- Take a step back from the specific details
- Identify the general concept, principle, or category behind the query
- Formulate a more general question that captures the essence

Examples:
- "What is the height of the Eiffel Tower?" -> "What are the dimensions of famous landmarks?"
- "Who wrote Pride and Prejudice?" -> "Who are famous English novelists?"
- "How does a diesel engine work?" -> "What are the types of internal combustion engines?"

Respond with ONLY the transformed query. Do not add any explanation, quotes, or additional text."""

    DEFAULT_MODEL = "gpt-4o-mini"
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 100
    MAX_RETRIES = 3

    def __init__(
        self,
        llm_client: OpenAI,
        model_name: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        """
        Initialize the query transformer.

        Args:
            llm_client: OpenAI-compatible client for making LLM calls
            model_name: Name of the model to use for transformation (default: gpt-4o-mini)
            temperature: Temperature for LLM sampling (default: 0.7)
            max_tokens: Maximum tokens for the response (default: 100)
        """
        self.llm_client = llm_client
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _build_prompt(self, query: str) -> List[dict]:
        """Build the messages for the LLM call."""
        user_message = f"Original query: {query}\n\nGenerate a broader, more general step-back version of this query."

        return [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

    def _parse_response(self, response_text: str, original_query: str) -> str:
        """Parse and clean the LLM response."""
        # Clean the response by stripping whitespace and removing quotes
        cleaned = response_text.strip()

        # Remove surrounding quotes if present
        if cleaned.startswith('"') and cleaned.endswith('"'):
            cleaned = cleaned[1:-1]
        elif cleaned.startswith("'") and cleaned.endswith("'"):
            cleaned = cleaned[1:-1]

        if not cleaned:
            logger.warning("Empty response from LLM, returning original query")
            return original_query

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
            timeout=30,
        )
        return response.choices[0].message.content

    def transform(self, query: str) -> List[str]:
        """
        Transform a query using step-back prompting.

        Args:
            query: The user's original search query

        Returns:
            List containing [original_query, step_back_variant]
            On error, returns [original_query] as fallback
        """
        if not query or not query.strip():
            logger.debug("Empty query provided, returning empty list")
            return []

        try:
            messages = self._build_prompt(query)
            response_text = self._call_llm(messages)
            step_back_query = self._parse_response(response_text, query)

            logger.debug(f"Query transformation: '{query[:50]}...' -> '{step_back_query[:50]}...'")

            # Return both original and step-back query
            return [query, step_back_query]
        except Exception as e:
            logger.error(f"Error during query transformation: {e}")
            # On error, return original query as fallback
            return [query]
