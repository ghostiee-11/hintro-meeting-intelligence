from dataclasses import dataclass

from app.core.errors import AppError
from app.core.logging import get_logger
from app.services.llm.providers import GeminiProvider, GroqProvider
from app.services.llm.schema import RawAnalysis

logger = get_logger("llm")


@dataclass
class LlmRunResult:
    analysis: RawAnalysis
    provider: str


class LlmService:
    """Resilient multi-provider orchestrator.

    Tries Gemini first, then Groq. A transient outage or quota limit on the
    primary provider therefore does not break the live demo, which is exactly when
    evaluators are hitting the deployment.
    """

    def __init__(self) -> None:
        self._providers = [GeminiProvider(), GroqProvider()]

    def has_provider(self) -> bool:
        return any(p.is_configured() for p in self._providers)

    async def analyze(self, prompt: str) -> LlmRunResult:
        configured = [p for p in self._providers if p.is_configured()]
        if not configured:
            raise AppError.upstream(
                "No LLM provider is configured. Set GEMINI_API_KEY or GROQ_API_KEY."
            )

        last_error: Exception | None = None
        for provider in configured:
            try:
                logger.info("llm_attempt", provider=provider.name)
                analysis = await provider.analyze(prompt)
                return LlmRunResult(analysis=analysis, provider=provider.name)
            except Exception as exc:  # noqa: BLE001 - provider isolation is intentional
                last_error = exc
                logger.warning("llm_provider_failed", provider=provider.name, error=str(exc))

        raise AppError.upstream(
            "All LLM providers failed to analyze the transcript",
            details=str(last_error) if last_error else None,
        )


llm_service = LlmService()
