import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from .embedding import EmbeddingModel
from .vector_index import VectorIndex
from ...utils.config import EMBEDDING_DIM

logger = logging.getLogger(__name__)


class RAGRetriever:

    def __init__(self, entries: List[Dict[str, Any]] = None):
        self.entries: List[Dict[str, Any]] = entries or []
        self.embedding_model: Optional[EmbeddingModel] = None
        self.vector_index: Optional[VectorIndex] = None
        self._initialized = False

    def initialize(self):
        from ...utils.config import EMBEDDING_MODEL
        try:
            self.embedding_model = EmbeddingModel(EMBEDDING_MODEL)
            self.embedding_model.load()
            if self.embedding_model.model is None:
                logger.warning("Embedding model not loaded, RAG disabled")
                return

            texts = [e.get("content", e.get("text", "")) for e in self.entries]
            embeddings = self.embedding_model.encode(texts)

            metadata = []
            for e in self.entries:
                meta = {
                    "content": e.get("content", ""),
                    "title": e.get("title", ""),
                    "chapter": e.get("chapter", ""),
                    "source": "印人传",
                }
                if "person" in e:
                    meta["person"] = e["person"]
                metadata.append(meta)

            self.vector_index = VectorIndex(dimension=self.embedding_model.dim)
            self.vector_index.build(texts, embeddings, metadata)
            self._initialized = True
            logger.info(f"RAG retriever initialized with {len(self.entries)} entries")
        except Exception as e:
            logger.error(f"Failed to initialize RAG retriever: {e}")
            self._initialized = False

    def save(self, index_path: Path, meta_path: Path):
        from ...utils.config import EMBEDDING_MODEL
        """持久化索引（FAISS + metadata JSON）。"""
        if not self._initialized or self.vector_index is None:
            raise RuntimeError("RAG retriever not initialized; call initialize() first")
        index_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        self.vector_index.save(index_path, meta_path)
        Path(meta_path).with_suffix(".model.txt").write_text(
            EMBEDDING_MODEL, encoding="utf-8"
        )
        logger.info(f"RAG index saved: {index_path}, {meta_path}")

    def load(self, index_path: Path, meta_path: Path):
        from ...utils.config import EMBEDDING_MODEL
        if not index_path.exists() or not meta_path.exists():
            logger.warning(f"RAG index files missing: {index_path.exists()=} {meta_path.exists()=}")
            self._initialized = False
            return False
        try:
            self.embedding_model = EmbeddingModel(EMBEDDING_MODEL)
            self.embedding_model.load()
            if self.embedding_model.model is None:
                logger.warning("Embedding model not loaded; RAG disabled")
                return False

            self.vector_index = VectorIndex(dimension=self.embedding_model.dim)
            self.vector_index.load(index_path, meta_path)
            if not self.vector_index._built:
                logger.warning("FAISS index failed to load")
                return False

            self._initialized = True
            logger.info(f"RAG retriever loaded: {self.vector_index.index.ntotal} vectors")
            return True
        except Exception as e:
            logger.error(f"Failed to load RAG retriever: {e}")
            self._initialized = False
            return False

    def retrieve(self, query: str, top_k: int = 5, threshold: float = 0.3) -> List[Dict[str, Any]]:
        if not self._initialized or self.vector_index is None:
            logger.warning("RAG retriever not initialized")
            return []

        query_embedding = self.embedding_model.encode([query])
        results = self.vector_index.search(query_embedding[0], top_k=top_k)

        filtered = [r for r in results if r.get("score", 0) >= threshold]
        logger.info(f"RAG retrieved {len(filtered)} chunks above threshold {threshold}")
        return filtered

    def retrieve_with_context(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        chunks = self.retrieve(query, top_k=top_k)
        if not chunks:
            return {
                "query": query,
                "chunks": [],
                "context": "",
            }

        context_parts = []
        for chunk in chunks:
            src = f"（{chunk.get('chapter', '')} {chunk.get('title', '')}）"
            context_parts.append(f"{src}「{chunk.get('content', '')[:200]}」")

        return {
            "query": query,
            "chunks": chunks,
            "context": "\n\n".join(context_parts),
        }
