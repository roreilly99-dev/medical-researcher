import os
import logging
from typing import Optional

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from models import DocumentChunk
from config import (
    get_llm_provider,
    OLLAMA_BASE_URL, OLLAMA_EMBED_MODEL,
    OPENAI_EMBED_MODEL, EMBEDDING_DIMENSIONS,
)
from exceptions import VectorSearchError

logger = logging.getLogger(__name__)


class VectorService:
    """Performs cosine-similarity search against stored document chunk embeddings."""

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> tuple[AsyncOpenAI, str]:
        """Return (AsyncOpenAI-compatible client, model_name) for the active provider."""
        provider = get_llm_provider()
        if provider == "openai":
            return AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")), OPENAI_EMBED_MODEL
        return AsyncOpenAI(
            base_url=f"{OLLAMA_BASE_URL}/v1",
            api_key="ollama",
        ), OLLAMA_EMBED_MODEL

    async def _embed_query(self, query: str) -> Optional[list[float]]:
        """Embed a single query string using the active provider.

        Returns ``None`` if the embedding call fails so that callers can fall
        back to an unordered chunk scan.
        """
        client, model = self._get_client()
        provider = get_llm_provider()

        try:
            kwargs: dict = {"model": model, "input": [query]}
            if provider == "openai":
                kwargs["dimensions"] = EMBEDDING_DIMENSIONS

            response = await client.embeddings.create(**kwargs)
            return response.data[0].embedding

        except Exception as exc:
            logger.error("Query embedding failed (%s / %s): %s", provider, model, exc)
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
        """Find the most relevant document chunks for *query* using cosine similarity.

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

