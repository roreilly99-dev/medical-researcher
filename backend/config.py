"""
Centralised LLM provider configuration.

Priority:
  1. Explicit LLM_PROVIDER env var ("openai" | "ollama" | "google")
  2. Auto-detect: use Google when GOOGLE_API_KEY is present,
     OpenAI when OPENAI_API_KEY is present, otherwise Ollama
"""

import os

# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------

def get_llm_provider() -> str:
    """Return the active LLM provider: 'openai', 'ollama', or 'google'."""
    explicit = os.getenv("LLM_PROVIDER", "").lower()
    if explicit in ("openai", "ollama", "google"):
        return explicit
    # Auto-detect based on available API keys
    if os.getenv("GOOGLE_API_KEY"):
        return "google"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    return "ollama"


# ---------------------------------------------------------------------------
# Ollama settings
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_LLM_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_EMBED_MODEL: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# ---------------------------------------------------------------------------
# OpenAI settings
# ---------------------------------------------------------------------------

OPENAI_LLM_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_EMBED_MODEL: str = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

# ---------------------------------------------------------------------------
# Google AI Studio (Gemini) settings
# ---------------------------------------------------------------------------

GOOGLE_LLM_MODEL: str = os.getenv("GOOGLE_MODEL", "gemini-1.5-flash")
GOOGLE_EMBED_MODEL: str = os.getenv("GOOGLE_EMBED_MODEL", "text-embedding-004")

# ---------------------------------------------------------------------------
# Shared embedding dimension
# Compatible with:
#   - Ollama nomic-embed-text (768 dims natively)
#   - OpenAI text-embedding-3-small (truncated to 768 via dimensions= param)
#   - Google text-embedding-004 (768 dims natively)
# ---------------------------------------------------------------------------

EMBEDDING_DIMENSIONS: int = 768
