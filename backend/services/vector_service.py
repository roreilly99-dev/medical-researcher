import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from models import DocumentChunk
from exceptions import VectorSearchError

logger = logging.getLogger(__name__)


class VectorService:
    """Performs cosine-similarity search against stored document chunk embeddings using PostgreSQL vector DB."""

    def __init__(self):
        self._embedder = None

    async def _get_embedder(self):
        """Lazy load the sentence-transformers model."""
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                # Use the same model as in embedding service
                self._embedder = SentenceTransformer('all-MiniLM-L6-v2')
            except ImportError:
                raise VectorSearchError("sentence-transformers not installed")
        return self._embedder

    async def _embed_query(self, query: str) -> Optional[list[float]]:
        """Embed a single query string using sentence-transformers.

        Returns ``None`` if the embedding call fails so that callers can fall
        back to an unordered chunk scan.
        """
        try:
            embedder = await self._get_embedder()
            embedding = embedder.encode([query], convert_to_numpy=False)[0]
            return embedding.tolist()
        except Exception as exc:
            logger.error("Query embedding failed: %s", exc)
            return None

    @staticmethod
    def _row_to_chunk(row) -> DocumentChunk:
        c = DocumentChunk()
        c.id = row.id
        c.document_id = row.document_id
        c.chunk_index = row.chunk_index
        c.content = row.content
        c.embedding = None
        return c

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def similarity_search(
        self, db: AsyncSession, query: str, limit: int = 5
    ) -> list[DocumentChunk]:
        """Find the most relevant document chunks for *query* using cosine similarity in PostgreSQL vector DB.

        Falls back to an arbitrary unordered scan when no embedding is available.

        Raises:
            VectorSearchError: if the database query fails.
        """
        embedding = await self._embed_query(query)

        try:
            if embedding is None:
                result = await db.execute(
                    text(
                        "SELECT id, document_id, chunk_index, content "
                        "FROM document_chunks "
                        "ORDER BY id "
                        "LIMIT :limit"
                    ),
                    {"limit": limit},
                )
                return [self._row_to_chunk(row) for row in result.fetchall()]

            embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
            result = await db.execute(
                text(
                    "SELECT id, document_id, chunk_index, content, "
                    "1 - (embedding <=> :embedding::vector) AS similarity "
                    "FROM document_chunks "
                    "WHERE embedding IS NOT NULL "
                    "ORDER BY embedding <=> :embedding::vector "
                    "LIMIT :limit"
                ),
                {"embedding": embedding_str, "limit": limit},
            )
            return [self._row_to_chunk(row) for row in result.fetchall()]

        except Exception as exc:
            logger.error("Vector similarity search failed: %s", exc)
            raise VectorSearchError(f"Similarity search failed: {exc}") from exc
            logger.error("Vector similarity search failed: %s", exc)
            raise VectorSearchError(f"Similarity search failed: {exc}") from exc

