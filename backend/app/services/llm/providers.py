from __future__ import annotations

import asyncio

from app.core.config import settings
from app.services.llm.json_util import extract_json, normalize_analysis
from app.services.llm.schema import RawAnalysis

SYSTEM_PROMPT = (
    "You are a precise meeting analyst. Respond ONLY with a JSON object matching the "
    "requested schema. Every insight and action item must cite transcript segment indices."
)


class GeminiProvider:
    """Primary provider. Uses Gemini structured JSON output."""

    name = "gemini"

    def __init__(self) -> None:
        self._key = settings.gemini_api_key
        self._model = settings.gemini_model

    def is_configured(self) -> bool:
        return bool(self._key)

    async def analyze(self, prompt: str) -> RawAnalysis:
        import google.generativeai as genai

        genai.configure(api_key=self._key)
        model = genai.GenerativeModel(
            self._model,
            generation_config={"temperature": 0.1, "response_mime_type": "application/json"},
        )
        # The SDK call is blocking; run it in a thread to stay async-friendly.
        response = await asyncio.to_thread(model.generate_content, prompt)
        return normalize_analysis(extract_json(response.text))


class GroqProvider:
    """Fallback provider. Uses Groq JSON mode for fast structured output."""

    name = "groq"

    def __init__(self) -> None:
        self._key = settings.groq_api_key
        self._model = settings.groq_model

    def is_configured(self) -> bool:
        return bool(self._key)

    async def analyze(self, prompt: str) -> RawAnalysis:
        from groq import AsyncGroq

        client = AsyncGroq(api_key=self._key)
        completion = await client.chat.completions.create(
            model=self._model,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        content = completion.choices[0].message.content or ""
        return normalize_analysis(extract_json(content))
