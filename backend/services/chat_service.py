import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import Document
from schemas import ChatSource
from exceptions import LLMError, VectorSearchError
from services.vector_service import VectorService
from services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ChatService:
    """Orchestrates RAG chat: context retrieval, source attribution, and LLM generation."""

    def __init__(self) -> None:
        self._vector = VectorService()
        self._llm = LLMService()

    async def chat(
        self,
        message: str,
        conversation_history: list,
        db: AsyncSession,
    ) -> tuple[str, list[ChatSource]]:
        """Run the full RAG pipeline for *message*.

        1. Embed the query and find the most similar document chunks.
        2. Build a context string and source list from those chunks.
        3. Call the LLM with the context and conversation history.

        Returns:
            A ``(answer, sources)`` tuple.

        Raises:
            VectorSearchError: if the similarity search fails.
            LLMError: if the LLM call fails.
        """
        chunks = await self._vector.similarity_search(db, message, limit=5)

        sources: list[ChatSource] = []
        context_parts: list[str] = []

        for chunk in chunks:
            doc_result = await db.execute(
                select(Document).where(Document.id == chunk.document_id)
            )
            doc = doc_result.scalar_one_or_none()
            filename = doc.original_filename if doc else "Unknown"

            sources.append(
                ChatSource(
                    document_id=chunk.document_id,
                    filename=filename,
                    content=chunk.content[:500],
                )
            )
            context_parts.append(f"[From: {filename}]\n{chunk.content}")

        context = "\n\n---\n\n".join(context_parts)
        answer = await self._llm.generate_chat_response(
            message=message,
            context=context,
            conversation_history=conversation_history,
        )

        return answer, sources
