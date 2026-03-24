import logging
from typing import Optional

import tiktoken
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from config import (
    get_llm_provider,
    OLLAMA_BASE_URL, OLLAMA_EMBED_MODEL,
    OPENAI_EMBED_MODEL, EMBEDDING_DIMENSIONS,
)

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


# ---------------------------------------------------------------------------
# Tokenisation
# ---------------------------------------------------------------------------

def _get_encoding():
    try:
        return tiktoken.encoding_for_model(OPENAI_EMBED_MODEL)
    except Exception:
        return tiktoken.get_encoding("cl100k_base")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping token-based chunks."""
    enc = _get_encoding()
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


# ---------------------------------------------------------------------------
# Embedding client
# ---------------------------------------------------------------------------

def _get_embed_client() -> tuple[AsyncOpenAI, str]:
    """Return (AsyncOpenAI-compatible client, model_name) for the active provider."""
    provider = get_llm_provider()
    if provider == "openai":
        import os
        return AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")), OPENAI_EMBED_MODEL
    return AsyncOpenAI(
        base_url=f"{OLLAMA_BASE_URL}/v1",
        api_key="ollama",
    ), OLLAMA_EMBED_MODEL


async def _embed_texts(texts: list[str]) -> list[Optional[list[float]]]:
    """Embed a batch of texts using the active provider."""
    client, model = _get_embed_client()
    provider = get_llm_provider()

    try:
        kwargs: dict = {"model": model, "input": texts}
        # OpenAI text-embedding-3-* supports truncating output dimensions
        if provider == "openai":
            kwargs["dimensions"] = EMBEDDING_DIMENSIONS

        response = await client.embeddings.create(**kwargs)
        return [item.embedding for item in response.data]

    except Exception as exc:
        logger.error("Embedding failed (%s / %s): %s", provider, model, exc)
        return [None] * len(texts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def chunk_and_embed_document(db: AsyncSession, document_id: str, markdown: str):
    """Chunk markdown text, embed chunks, and store DocumentChunk records."""
    from sqlalchemy import delete
    from models import DocumentChunk

    await db.execute(
        delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
    )
    await db.commit()

    chunks = chunk_text(markdown)
    if not chunks:
        return

    batch_size = 20
    for batch_start in range(0, len(chunks), batch_size):
        batch = chunks[batch_start: batch_start + batch_size]
        embeddings = await _embed_texts(batch)

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

