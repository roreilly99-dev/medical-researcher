"""
Centralised LLM provider configuration for chat only.

For embeddings, we use local sentence-transformers models.
"""

import os

# ---------------------------------------------------------------------------
# Provider selection for LLM (chat only)
# ---------------------------------------------------------------------------

def get_llm_provider() -> str:
    """Return the active LLM provider for chat: 'google' only."""
    # Only Google Gemini is supported for chat/LLM operations
    if os.getenv("GOOGLE_API_KEY"):
        return "google"
    raise ValueError("GOOGLE_API_KEY environment variable is required for LLM operations")


# ---------------------------------------------------------------------------
# Google AI Studio (Gemini) settings for LLM
# ---------------------------------------------------------------------------

GOOGLE_LLM_MODEL: str = os.getenv("GOOGLE_MODEL", "gemini-1.5-flash")
GOOGLE_EMBED_MODEL: str = os.getenv(
    "GOOGLE_EMBED_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)

# ---------------------------------------------------------------------------
# Embedding dimensions (for sentence-transformers all-MiniLM-L6-v2)
# ---------------------------------------------------------------------------

EMBEDDING_DIMENSIONS: int = 384  # all-MiniLM-L6-v2 produces 384-dimensional embeddings
