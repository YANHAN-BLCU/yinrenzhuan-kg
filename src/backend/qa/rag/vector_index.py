import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


class VectorIndex:

    def __init__(self, dimension: int = 768):
        self.dimension = dimension
        self.index = None
        self.metadata: List[Dict[str, Any]] = []
        self._built = False

    def build(self, texts: List[str], embeddings: List[List[float]], metadata: Optional[List[Dict[str, Any]]] = None):
        try:
            import faiss
            self.index = faiss.IndexFlatIP(self.dimension)
            arr = np.array(embeddings, dtype=np.float32)
            if arr.ndim == 1:
                arr = arr.reshape(-1, self.dimension)
            faiss.normalize_L2(arr)
            self.index.add(arr)
            self.metadata = metadata or [{"text": t, "index": i} for i, t in enumerate(texts)]
            self._built = True
            logger.info(f"Built FAISS index with {self.index.ntotal} vectors")
        except ImportError:
            logger.warning("faiss not available, using simple numpy index")
            self._build_numpy(texts, embeddings, metadata)

    def _build_numpy(self, texts: List[str], embeddings: List[List[float]], metadata: Optional[List[Dict[str, Any]]] = None):
        self.vectors = np.array(embeddings, dtype=np.float32)
        self.metadata = metadata or [{"text": t, "index": i} for i, t in enumerate(texts)]
        self._built = True

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        if not self._built:
            return []

        query_vec = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query_vec)

        if self.index is not None:
            try:
                import faiss
                distances, indices = self.index.search(query_vec, min(top_k, self.index.ntotal))
                results = []
                for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
                    if idx < len(self.metadata):
                        result = dict(self.metadata[int(idx)])
                        result["score"] = float(dist)
                        results.append(result)
                return results
            except Exception:
                pass

        q = np.array(query_embedding, dtype=np.float32)
        norm_q = q / (np.linalg.norm(q) + 1e-10)
        scores = np.dot(self.vectors, norm_q)
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                result = dict(self.metadata[idx])
                result["score"] = float(scores[idx])
                results.append(result)
        return results

    def save(self, index_path: Path, meta_path: Path):
        if self.index is not None:
            try:
                import faiss
                faiss.write_index(self.index, str(index_path))
                logger.info(f"Saved FAISS index to {index_path}")
            except Exception:
                pass

        import json
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved metadata to {meta_path}")

    def load(self, index_path: Path, meta_path: Path):
        import json
        try:
            import faiss
            self.index = faiss.read_index(str(index_path))
            self._built = True
            logger.info(f"Loaded FAISS index from {index_path}")
        except Exception:
            self._built = False

        with open(meta_path, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)
