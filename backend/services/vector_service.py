import os
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from models import DocumentChunk

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"


async def _embed_query(query: str) -> Optional[list[float]]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=api_key)

    try:
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[query],
        )
        return response.data[0].embedding
    except Exception as exc:
        logger.error("Query embedding failed: %s", exc)
        return None


async def similarity_search(
    db: AsyncSession, query: str, limit: int = 5
) -> list[DocumentChunk]:
    """Find the most relevant document chunks for a query using cosine similarity."""
    embedding = await _embed_query(query)

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
        rows = result.fetchall()
        chunks = []
        for row in rows:
            c = DocumentChunk()
            c.id = row.id
            c.document_id = row.document_id
            c.chunk_index = row.chunk_index
            c.content = row.content
            c.embedding = None
            chunks.append(c)
        return chunks

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

    rows = result.fetchall()
    chunks = []
    for row in rows:
        c = DocumentChunk()
        c.id = row.id
        c.document_id = row.document_id
        c.chunk_index = row.chunk_index
        c.content = row.content
        c.embedding = None
        chunks.append(c)

    return chunks
