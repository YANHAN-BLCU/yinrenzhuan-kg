import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class EmbeddingModel:
    def __init__(self, model_name: str = "BAAI/bge-base-zh-v1.5", device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self.model = None
        self.tokenizer = None
        self.dim = 768

    def load(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name, device=self.device)
            self.tokenizer = self.model.tokenizer
            self.dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Loaded embedding model: {self.model_name}, dim={self.dim}")
        except ImportError:
            logger.warning("sentence-transformers not available, using simple hash embedding")
            self.model = None

    def encode(self, texts: List[str], normalize: bool = True) -> List[List[float]]:
        if self.model is None:
            return self._simple_encode(texts)

        embeddings = self.model.encode(texts, normalize_to_unit=normalize)
        return embeddings.tolist()

    def _simple_encode(self, texts: List[str]) -> List[List[float]]:
        import hashlib
        import struct

        def hash_vec(text: str) -> List[float]:
            h = hashlib.sha256(text.encode()).digest()
            nums = struct.unpack(f"{self.dim}f", h[:self.dim * 4] + b"\x00" * max(0, self.dim * 4 - len(h)))
            vec = list(nums)
            norm = sum(x * x for x in vec) ** 0.5
            return [x / (norm + 1e-10) for x in vec]

        return [hash_vec(t) for t in texts]
