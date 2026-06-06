import asyncio

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("embeddings")

EMBEDDING_DIMS = 768


class EmbeddingsService:
    """Generates 768-dim text embeddings via Gemini for semantic search.

    Requests output_dimensionality=768 so the result fits the pgvector(768) column
    regardless of the model's native size. Degrades gracefully: if no key is
    configured (or a call fails), returns None and callers skip embedding rather
    than failing the request.
    """

    def __init__(self) -> None:
        self._key = settings.gemini_api_key
        self._model = settings.embedding_model

    def is_configured(self) -> bool:
        return bool(self._key)

    async def embed(self, text: str) -> list[float] | None:
        if not self._key:
            return None
        try:
            import google.generativeai as genai

            genai.configure(api_key=self._key)
            result = await asyncio.to_thread(
                genai.embed_content,
                model=self._model,
                content=text,
                output_dimensionality=EMBEDDING_DIMS,
            )
            vector = result["embedding"]
            return vector[:EMBEDDING_DIMS] if len(vector) > EMBEDDING_DIMS else vector
        except Exception as exc:  # noqa: BLE001
            logger.warning("embedding_failed", error=str(exc))
            return None


embeddings_service = EmbeddingsService()
