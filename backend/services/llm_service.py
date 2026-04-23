import os
import re
import json
import logging
from typing import Any, Optional

import google.generativeai as genai

from config import GOOGLE_LLM_MODEL
from exceptions import LLMError

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


class LLMService:
    """Handles Gemini-based medical field extraction and RAG chat generation."""

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_google_model(self) -> genai.GenerativeModel:
        """Return configured Google Generative AI model."""
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        return genai.GenerativeModel(GOOGLE_LLM_MODEL)

    @staticmethod
    def _parse_json_response(raw: str) -> dict:
        """Parse JSON from a Gemini response, handling extra prose around the object."""
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

    @staticmethod
    def _mock_extraction(markdown: str) -> dict[str, Any]:
        """Placeholder extraction returned when Gemini is unavailable."""
        lines = [line.strip() for line in markdown.split("\n") if line.strip()]
        title = lines[0].lstrip("#").strip() if lines else "Unknown Title"
        return {
            "title": title,
            "authors": [],
            "abstract": "Gemini LLM extraction unavailable. Configure GOOGLE_API_KEY.",
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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def extract_medical_fields(self, markdown: str) -> dict[str, Any]:
        """Extract structured medical fields from markdown text using Gemini.

        Falls back to a mock extraction if the Gemini call fails so that the
        processing pipeline can continue.
        """
        text_snippet = markdown[:12000]
        prompt = EXTRACTION_PROMPT.format(text=text_snippet)

        try:
            model = self._get_google_model()
            response = await model.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
            raw = response.text or "{}"
            data = self._parse_json_response(raw)
            return {field: data.get(field) for field in EXTRACTION_FIELDS}

        except Exception as exc:
            logger.error("Gemini extraction failed: %s", exc)
            return self._mock_extraction(markdown)

    async def generate_chat_response(
        self,
        message: str,
        context: str,
        conversation_history: list,
    ) -> str:
        """Generate a RAG chat response using Gemini.

        Raises:
            LLMError: if the Gemini call fails.
        """
        system_prompt = (
            "You are a helpful medical research assistant. Answer the user's question "
            "based on the provided research paper excerpts. Be accurate and cite the "
            "sources when relevant. If the context doesn't contain enough information, "
            "say so clearly.\n\n"
            f"Relevant context from research papers:\n\n{context}"
        )

        try:
            model = self._get_google_model()

            # Build conversation for Gemini
            chat_history = []
            for msg in conversation_history[-10:]:
                role = "user" if msg.role == "user" else "model"
                chat_history.append({"role": role, "parts": [msg.content]})

            # Start chat with system instruction
            chat = model.start_chat(history=chat_history)
            full_prompt = f"{system_prompt}\n\nUser question: {message}"

            response = await chat.send_message_async(
                full_prompt,
                generation_config=genai.GenerationConfig(temperature=0.3),
            )
            return response.text or "No response generated."

        except Exception as exc:
            logger.error("Gemini chat generation failed: %s", exc)
            raise LLMError(f"Chat generation failed: {exc}") from exc

