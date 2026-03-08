import logging
from typing import Dict, List, Optional

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from khoj.utils.helpers import get_device, timer

logger = logging.getLogger(__name__)


class SparseEmbeddingGenerator:
    """
    Generates sparse (lexical) embeddings using FlagEmbedding BGE-M3 model.

    Sparse embeddings represent text as a sparse vector of token IDs and their associated
    weights, capturing lexical information complementary to dense embeddings.
    """

    DEFAULT_BATCH_SIZE = 32
    DEFAULT_MAX_LENGTH = 8192

    def __init__(self, model_name: str = "BAAI/bge-m3"):
        """
        Initialize the sparse embedding generator.

        Args:
            model_name: Name of the FlagEmbedding model to use (default: BAAI/bge-m3)
        """
        self.model_name = model_name
        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        """Load the FlagEmbedding model with sparse embedding support."""
        try:
            from FlagEmbedding import BGEM3FlagModel

            with timer(f"Loaded sparse embedding model {self.model_name}", logger):
                self.model = BGEM3FlagModel(
                    self.model_name,
                    use_fp16=False,
                    device=get_device(),
                )
            logger.info(f"Successfully loaded sparse embedding model: {self.model_name}")
        except ImportError as e:
            logger.error(f"Failed to import FlagEmbedding: {e}")
            raise ImportError(
                "FlagEmbedding library is required for sparse embeddings. "
                "Install with: pip install FlagEmbedding"
            ) from e
        except Exception as e:
            logger.error(f"Failed to load sparse embedding model {self.model_name}: {e}")
            raise

    def _convert_to_sparse_dict(
        self, lexical_weights: List[Dict[str, float]]
    ) -> List[Dict[int, float]]:
        """
        Convert lexical weights from token to weight mapping to token_id to weight mapping.

        Args:
            lexical_weights: List of dictionaries mapping tokens to weights

        Returns:
            List of dictionaries mapping token_ids to weights
        """
        sparse_embeddings = []
        for weights in lexical_weights:
            sparse_dict: Dict[int, float] = {}
            for token, weight in weights.items():
                # Get token ID from the model's tokenizer
                if hasattr(self.model, 'tokenizer') and self.model.tokenizer is not None:
                    token_ids = self.model.tokenizer.encode(token, add_special_tokens=False)
                    if token_ids:
                        token_id = token_ids[0]
                        sparse_dict[token_id] = max(sparse_dict.get(token_id, 0.0), float(weight))
                else:
                    # Fallback: use hash if tokenizer unavailable
                    token_id = hash(token) % (2**31)  # Keep within positive int range
                    sparse_dict[token_id] = max(sparse_dict.get(token_id, 0.0), float(weight))
            sparse_embeddings.append(sparse_dict)
        return sparse_embeddings

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_random_exponential(multiplier=1, max=10),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.DEBUG),
    )
    def _encode_batch(self, texts: List[str]) -> List[Dict[str, float]]:
        """
        Encode a batch of texts to get lexical weights with retry logic.

        Args:
            texts: List of text strings to encode

        Returns:
            List of dictionaries mapping tokens to weights
        """
        try:
            result = self.model.encode(
                texts,
                batch_size=len(texts),
                max_length=self.DEFAULT_MAX_LENGTH,
                return_dense=False,
                return_sparse=True,
                return_colbert_vecs=False,
            )
            return result.get("lexical_weights", [])
        except Exception as e:
            logger.error(f"Error encoding batch: {e}")
            raise

    def generate_sparse_embeddings(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
    ) -> List[Dict[int, float]]:
        """
        Generate sparse embeddings for a list of texts.

        Args:
            texts: List of text strings to generate embeddings for
            batch_size: Number of texts to process in each batch (default: 32)

        Returns:
            List of dictionaries mapping token_id to weight for each text
        """
        if not texts:
            return []

        batch_size = batch_size or self.DEFAULT_BATCH_SIZE
        all_sparse_embeddings: List[Dict[int, float]] = []

        logger.debug(f"Generating sparse embeddings for {len(texts)} texts with batch size {batch_size}")

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(texts) + batch_size - 1) // batch_size

            try:
                # Get lexical weights from the model
                lexical_weights = self._encode_batch(batch_texts)

                # Convert to token_id -> weight format
                sparse_embeddings = self._convert_to_sparse_dict(lexical_weights)
                all_sparse_embeddings.extend(sparse_embeddings)

                logger.debug(
                    f"Processed batch {batch_num}/{total_batches} "
                    f"({len(batch_texts)} texts)"
                )

            except Exception as e:
                logger.error(f"Failed to process batch {batch_num}/{total_batches}: {e}")
                # Return empty sparse embeddings for failed batch to maintain alignment
                all_sparse_embeddings.extend([{} for _ in range(len(batch_texts))])

        logger.info(f"Successfully generated sparse embeddings for {len(texts)} texts")
        return all_sparse_embeddings

    def encode_single(self, text: str) -> Dict[int, float]:
        """
        Generate sparse embedding for a single text.

        Args:
            text: Text string to generate embedding for

        Returns:
            Dictionary mapping token_id to weight
        """
        result = self.generate_sparse_embeddings([text])
        return result[0] if result else {}

    def get_model_info(self) -> Dict[str, str]:
        """
        Get information about the loaded model.

        Returns:
            Dictionary containing model information
        """
        return {
            "model_name": self.model_name,
            "model_type": "sparse (lexical)",
            "batch_size": str(self.DEFAULT_BATCH_SIZE),
            "max_length": str(self.DEFAULT_MAX_LENGTH),
        }
