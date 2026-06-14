import logging
from typing import List
from ...utils.config import EMBEDDING_API_KEY, EMBEDDING_BASE_URL, EMBEDDING_MODEL, EMBEDDING_DIM

logger = logging.getLogger(__name__)


class EmbeddingModel:
    def __init__(self, model_name: str = None, dimension: int = None):
        self.model_name = model_name or EMBEDDING_MODEL
        self.dim = dimension or EMBEDDING_DIM
        self._api_key = EMBEDDING_API_KEY
        self._base_url = EMBEDDING_BASE_URL
        self.model = "openai_compatible"  # sentinel: not None = loaded

    def load(self):
        if not self._api_key:
            logger.warning("EMBEDDING_API_KEY not set; RAG will use simple hash fallback")
            self.model = None
            return
        if not self._base_url:
            logger.warning("EMBEDDING_BASE_URL not set; RAG will use simple hash fallback")
            self.model = None
            return
        self.model = "openai_compatible"
        logger.info(f"Embedding model configured: {self.model_name} at {self._base_url}")

    def encode(self, texts: List[str], normalize: bool = True) -> List[List[float]]:
        if self.model is None:
            return self._simple_encode(texts)

        try:
            import httpx
        except ImportError:
            logger.warning("httpx not available; using simple hash fallback")
            return self._simple_encode(texts)

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "input": texts,
            "encoding_format": "float",
        }
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{self._base_url.rstrip('/')}/embeddings",
                    json=payload,
                    headers=headers,
                )
            resp.raise_for_status()
            data = resp.json()
            embeddings = [item["embedding"] for item in data["data"]]
            if normalize:
                import math
                result = []
                for vec in embeddings:
                    norm = math.sqrt(sum(x * x for x in vec))
                    result.append([x / (norm + 1e-10) for x in vec])
                return result
            return embeddings
        except Exception as e:
            logger.error(f"Embedding API call failed: {e}")
            return self._simple_encode(texts)

    def _simple_encode(self, texts: List[str]) -> List[List[float]]:
        import hashlib, struct
        dim = self.dim

        def hash_vec(text: str) -> List[float]:
            h = hashlib.sha256(text.encode()).digest()
            nums = struct.unpack(f"{dim}f", h[:dim * 4] + b"\x00" * max(0, dim * 4 - len(h)))
            vec = list(nums)
            norm = sum(x * x for x in vec) ** 0.5
            return [x / (norm + 1e-10) for x in vec]

        return [hash_vec(t) for t in texts]
