import os
import logging
from typing import Optional

import tiktoken
from sqlalchemy.ext.asyncio import AsyncSession

from models import DocumentChunk

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
EMBEDDING_MODEL = "text-embedding-3-small"


def _get_encoding():
    try:
        return tiktoken.encoding_for_model(EMBEDDING_MODEL)
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
        chunk_tokens = tokens[start:end]
        chunks.append(enc.decode(chunk_tokens))
        if end == len(tokens):
            break
        start += chunk_size - overlap

    return chunks


async def _embed_texts(texts: list[str]) -> list[Optional[list[float]]]:
    """Embed a batch of texts using OpenAI. Returns None embeddings if key not set."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set, skipping embeddings")
        return [None] * len(texts)

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=api_key)

    try:
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts,
        )
        return [item.embedding for item in response.data]
    except Exception as exc:
        logger.error("Embedding failed: %s", exc)
        return [None] * len(texts)


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
