import logging
from typing import List, Dict, Any, Optional
from .embedding import EmbeddingModel
from .vector_index import VectorIndex

logger = logging.getLogger(__name__)


class RAGRetriever:

    def __init__(self, entries: List[Dict[str, Any]]):
        self.entries = entries
        self.embedding_model: Optional[EmbeddingModel] = None
        self.vector_index: Optional[VectorIndex] = None
        self._initialized = False

    def initialize(self, model_name: str = "BAAI/bge-base-zh-v1.5"):
        try:
            self.embedding_model = EmbeddingModel(model_name)
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
