from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Document
from schemas import ChatRequest, ChatResponse, ChatSource
from services.vector_service import similarity_search
from services.llm_service import generate_chat_response

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    chunks = await similarity_search(db, request.message, limit=5)

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
    answer = await generate_chat_response(
        message=request.message,
        context=context,
        conversation_history=request.conversation_history,
    )

    return ChatResponse(answer=answer, sources=sources)
