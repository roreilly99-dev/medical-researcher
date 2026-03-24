import os
import re
import json
import logging
from typing import Any

from openai import AsyncOpenAI

from config import (
    get_llm_provider,
    OLLAMA_BASE_URL, OLLAMA_LLM_MODEL,
    OPENAI_LLM_MODEL,
)

logger = logging.getLogger(__name__)

EXTRACTION_FIELDS = [
    "title", "authors", "abstract", "study_type", "methods", "results",
    "conclusions", "keywords", "sample_size", "key_findings", "limitations",
    "publication_year", "journal",
]

EXTRACTION_PROMPT = """You are a medical research analyst. Extract the following fields from the provided medical paper text and return a valid JSON object.

Fields to extract:
- title: The full title of the paper
- authors: List of author names
- abstract: The paper abstract
- study_type: Type of study (e.g., RCT, cohort, case-control, meta-analysis, review)
- methods: Summary of methods used
- results: Key results summary
- conclusions: Main conclusions
- keywords: List of keywords or MeSH terms
- sample_size: Number of participants/samples (as string)
- key_findings: List of the most important findings
- limitations: Study limitations mentioned
- publication_year: Year of publication (as integer or null)
- journal: Name of the journal

Return ONLY a valid JSON object with these exact keys. If a field cannot be found, use null for strings/integers or [] for lists.

Paper text:
{text}"""


# ---------------------------------------------------------------------------
# Client helpers
# ---------------------------------------------------------------------------

def _get_llm_client() -> tuple[AsyncOpenAI, str]:
    """Return (AsyncOpenAI-compatible client, model_name) for the active provider."""
    provider = get_llm_provider()
    if provider == "openai":
        return AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")), OPENAI_LLM_MODEL
    # Ollama exposes an OpenAI-compatible REST API at /v1
    return AsyncOpenAI(
        base_url=f"{OLLAMA_BASE_URL}/v1",
        api_key="ollama",          # Ollama ignores the key; the library requires a non-empty value
    ), OLLAMA_LLM_MODEL


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _parse_json_response(raw: str) -> dict:
    """Parse JSON from an LLM response, handling extra prose around the object."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


def _mock_extraction(markdown: str) -> dict[str, Any]:
    """Placeholder extraction when no LLM is available."""
    lines = [line.strip() for line in markdown.split("\n") if line.strip()]
    title = lines[0].lstrip("#").strip() if lines else "Unknown Title"
    return {
        "title": title,
        "authors": [],
        "abstract": "LLM extraction unavailable. Configure OPENAI_API_KEY or ensure Ollama is running.",
        "study_type": None,
        "methods": None,
        "results": None,
        "conclusions": None,
        "keywords": [],
        "sample_size": None,
        "key_findings": [],
        "limitations": None,
        "publication_year": None,
        "journal": None,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def extract_medical_fields(markdown: str) -> dict[str, Any]:
    """Extract structured medical fields from markdown text using the active LLM."""
    client, model = _get_llm_client()
    provider = get_llm_provider()
    text_snippet = markdown[:12000]
    prompt = EXTRACTION_PROMPT.format(text=text_snippet)

    try:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }
        # OpenAI and recent Ollama (llama3.2+) both support json_object mode
        if provider == "openai":
            kwargs["response_format"] = {"type": "json_object"}

        response = await client.chat.completions.create(**kwargs)
        raw = response.choices[0].message.content or "{}"
        data = _parse_json_response(raw)
        return {field: data.get(field) for field in EXTRACTION_FIELDS}

    except Exception as exc:
        logger.error("LLM extraction failed (%s / %s): %s", provider, model, exc)
        return _mock_extraction(markdown)


async def generate_chat_response(
    message: str,
    context: str,
    conversation_history: list,
) -> str:
    """Generate a RAG chat response using the active LLM provider."""
    client, model = _get_llm_client()
    provider = get_llm_provider()

    system_prompt = (
        "You are a helpful medical research assistant. Answer the user's question "
        "based on the provided research paper excerpts. Be accurate and cite the "
        "sources when relevant. If the context doesn't contain enough information, "
        "say so clearly.\n\n"
        f"Relevant context from research papers:\n\n{context}"
    )

    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for msg in conversation_history[-10:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": message})

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3,
        )
        return response.choices[0].message.content or "No response generated."

    except Exception as exc:
        logger.error("Chat generation failed (%s / %s): %s", provider, model, exc)
        return f"An error occurred while generating the response: {exc}"

