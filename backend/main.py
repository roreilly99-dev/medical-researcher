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
from config import (
    get_llm_provider,
    OLLAMA_BASE_URL, OLLAMA_LLM_MODEL, OLLAMA_EMBED_MODEL,
    OPENAI_LLM_MODEL, OPENAI_EMBED_MODEL, EMBEDDING_DIMENSIONS,
)

load_dotenv()

logger = logging.getLogger(__name__)


async def _pull_ollama_models() -> None:
    """Ensure required Ollama models are present, pulling them if needed."""
    import httpx

    models = [OLLAMA_LLM_MODEL, OLLAMA_EMBED_MODEL]

    # Wait for Ollama to be reachable (up to 30 s)
    async with httpx.AsyncClient(timeout=10) as probe:
        for attempt in range(6):
            try:
                resp = await probe.get(f"{OLLAMA_BASE_URL}/api/tags")
                if resp.status_code == 200:
                    break
            except (httpx.HTTPError, httpx.TransportError, OSError) as exc:
                logger.debug("Ollama probe attempt %d failed: %s", attempt + 1, exc)
            if attempt < 5:
                logger.info("Waiting for Ollama to be ready… (%d/6)", attempt + 1)
                await asyncio.sleep(5)
        else:
            logger.warning("Ollama not reachable at %s — skipping model pull", OLLAMA_BASE_URL)
            return

    # Pull each model (non-streaming, waits until complete)
    async with httpx.AsyncClient(timeout=600) as client:
        for model in models:
            try:
                tags_resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
                if tags_resp.status_code == 200:
                    present = [m.get("name", "") for m in tags_resp.json().get("models", [])]
                    # Compare base names (strip tag suffix) for exact match
                    model_base = model.split(":")[0]
                    if any(p.split(":")[0] == model_base for p in present):
                        logger.info("Ollama model '%s' already present", model)
                        continue

                logger.info("Pulling Ollama model '%s' (this may take a few minutes)…", model)
                pull_resp = await client.post(
                    f"{OLLAMA_BASE_URL}/api/pull",
                    json={"model": model, "stream": False},
                    timeout=600,
                )
                if pull_resp.status_code == 200:
                    logger.info("Ollama model '%s' ready", model)
                else:
                    logger.warning("Pull returned %s for model '%s'", pull_resp.status_code, model)

            except Exception as exc:
                logger.warning("Could not pull Ollama model '%s': %s", model, exc)


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


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/v1/providers")
async def provider_info():
    """Return the active LLM / embedding provider configuration."""
    provider = get_llm_provider()
    if provider == "openai":
        return {
            "provider": "openai",
            "llm_model": OPENAI_LLM_MODEL,
            "embed_model": OPENAI_EMBED_MODEL,
            "embed_dimensions": EMBEDDING_DIMENSIONS,
        }
    return {
        "provider": "ollama",
        "ollama_base_url": OLLAMA_BASE_URL,
        "llm_model": OLLAMA_LLM_MODEL,
        "embed_model": OLLAMA_EMBED_MODEL,
        "embed_dimensions": EMBEDDING_DIMENSIONS,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
