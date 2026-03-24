from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import ChatRequest, ChatResponse
from exceptions import LLMError, VectorSearchError
from services.chat_service import ChatService

router = APIRouter()
_chat_service = ChatService()


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        answer, sources = await _chat_service.chat(
            message=request.message,
            conversation_history=request.conversation_history,
            db=db,
        )
    except VectorSearchError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return ChatResponse(answer=answer, sources=sources)

