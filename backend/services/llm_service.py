import os
import json
import logging
from typing import Any

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


def _get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    from openai import AsyncOpenAI
    return AsyncOpenAI(api_key=api_key)


def _mock_extraction(markdown: str) -> dict[str, Any]:
    """Return a placeholder extraction when OpenAI is not configured."""
    lines = [l.strip() for l in markdown.split("\n") if l.strip()]
    title = lines[0].lstrip("#").strip() if lines else "Unknown Title"
    return {
        "title": title,
        "authors": [],
        "abstract": "OpenAI API key not configured. Extraction unavailable.",
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


async def extract_medical_fields(markdown: str) -> dict[str, Any]:
    """Extract structured medical fields from markdown text using GPT-4o-mini."""
    client = _get_openai_client()
    if client is None:
        logger.warning("OPENAI_API_KEY not set, using mock extraction")
        return _mock_extraction(markdown)

    text_snippet = markdown[:12000]
    prompt = EXTRACTION_PROMPT.format(text=text_snippet)

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)
        return {field: data.get(field) for field in EXTRACTION_FIELDS}
    except Exception as exc:
        logger.error("LLM extraction failed: %s", exc)
        return _mock_extraction(markdown)


async def generate_chat_response(
    message: str,
    context: str,
    conversation_history: list,
) -> str:
    """Generate a chat response using retrieved context."""
    client = _get_openai_client()
    if client is None:
        return (
            "I cannot answer questions at this time because the OpenAI API key "
            "is not configured. Please set the OPENAI_API_KEY environment variable."
        )

    system_prompt = (
        "You are a helpful medical research assistant. Answer the user's question "
        "based on the provided research paper excerpts. Be accurate and cite the "
        "sources when relevant. If the context doesn't contain enough information, "
        "say so clearly.\n\n"
        f"Relevant context from research papers:\n\n{context}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    for msg in conversation_history[-10:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": message})

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.3,
        )
        return response.choices[0].message.content or "No response generated."
    except Exception as exc:
        logger.error("Chat generation failed: %s", exc)
        return f"An error occurred while generating the response: {exc}"
