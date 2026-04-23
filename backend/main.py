import asyncio
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from database import init_db
from api.documents import router as documents_router
from api.chat import router as chat_router
from api.websocket import router as websocket_router
from config import (
    get_llm_provider,
    EMBEDDING_DIMENSIONS,
    GOOGLE_LLM_MODEL,
    GOOGLE_EMBED_MODEL,
)

load_dotenv()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    if get_llm_provider() == "ollama":
        await _pull_ollama_models()
    yield


app = FastAPI(
    title="Medical Research API",
    description="API for uploading and analyzing medical research papers",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: Allow configured origins or default to localhost for development
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(chat_router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(websocket_router, prefix="/api/v1/ws", tags=["websocket"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/v1/providers")
async def provider_info():
    """Return the active LLM / embedding provider configuration."""
    provider = get_llm_provider()
    return {
        "provider": "google",
        "llm_model": GOOGLE_LLM_MODEL,
        "embed_model": GOOGLE_EMBED_MODEL,
        "embed_dimensions": EMBEDDING_DIMENSIONS,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
