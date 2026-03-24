import os
import logging
from typing import Optional

import tiktoken
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
import google.generativeai as genai

from config import (
    get_llm_provider,
    OLLAMA_BASE_URL, OLLAMA_EMBED_MODEL,
    OPENAI_EMBED_MODEL, EMBEDDING_DIMENSIONS,
    GOOGLE_EMBED_MODEL,
)
from exceptions import EmbeddingError

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


class EmbeddingService:
    """Chunks text into overlapping token windows and embeds them via the active provider."""

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_encoding():
        try:
            return tiktoken.encoding_for_model(OPENAI_EMBED_MODEL)
        except Exception:
            return tiktoken.get_encoding("cl100k_base")

    def _get_openai_client(self) -> tuple[AsyncOpenAI, str]:
        """Return (AsyncOpenAI-compatible client, model_name) for OpenAI/Ollama."""
        provider = get_llm_provider()
        if provider == "openai":
            return AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")), OPENAI_EMBED_MODEL
        return AsyncOpenAI(
            base_url=f"{OLLAMA_BASE_URL}/v1",
            api_key="ollama",
        ), OLLAMA_EMBED_MODEL

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chunk_text(
        self,
        text: str,
        chunk_size: int = CHUNK_SIZE,
        overlap: int = CHUNK_OVERLAP,
    ) -> list[str]:
        """Split *text* into overlapping token-based chunks."""
        enc = self._get_encoding()
        tokens = enc.encode(text)
        chunks: list[str] = []
        start = 0

        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunks.append(enc.decode(tokens[start:end]))
            if end == len(tokens):
                break
            start += chunk_size - overlap

        return chunks

    async def embed_texts(self, texts: list[str]) -> list[Optional[list[float]]]:
        """Embed a batch of texts using the active provider.

        Returns a list of embedding vectors (or ``None`` entries on failure).

        Raises:
            EmbeddingError: if the embedding API call fails.
        """
        provider = get_llm_provider()

        try:
            if provider == "google":
                # Use Google embeddings
                genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
                embeddings = []
                for text in texts:
                    result = genai.embed_content(
                        model=f"models/{GOOGLE_EMBED_MODEL}",
                        content=text,
                        task_type="retrieval_document",
                    )
                    embeddings.append(result["embedding"])
                return embeddings
            else:
                # Use OpenAI or Ollama
                client, model = self._get_openai_client()
                kwargs: dict = {"model": model, "input": texts}
                # OpenAI text-embedding-3-* supports truncating output dimensions
                if provider == "openai":
                    kwargs["dimensions"] = EMBEDDING_DIMENSIONS

                response = await client.embeddings.create(**kwargs)
                return [item.embedding for item in response.data]

        except Exception as exc:
            logger.error("Embedding failed (%s): %s", provider, exc)
            raise EmbeddingError(f"Embedding API call failed: {exc}") from exc

    async def chunk_and_embed_document(
        self, db: AsyncSession, document_id: str, markdown: str
    ) -> None:
        """Chunk *markdown*, embed each chunk, and persist ``DocumentChunk`` rows.

        Existing chunks for the document are deleted first so re-processing is
        idempotent.
        """
        from sqlalchemy import delete
        from models import DocumentChunk

        await db.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        await db.commit()

        chunks = self.chunk_text(markdown)
        if not chunks:
            return

        batch_size = 20
        for batch_start in range(0, len(chunks), batch_size):
            batch = chunks[batch_start: batch_start + batch_size]

            try:
                embeddings = await self.embed_texts(batch)
            except EmbeddingError:
                # Store chunks without embeddings rather than failing the pipeline
                embeddings = [None] * len(batch)

            for idx, (content, embedding) in enumerate(zip(batch, embeddings), start=batch_start):
                chunk = DocumentChunk(
                    document_id=document_id,
                    chunk_index=idx,
                    content=content,
                    embedding=embedding,
                )
                db.add(chunk)

            await db.commit()

        logger.info("Stored %d chunks for document %s", len(chunks), document_id)

