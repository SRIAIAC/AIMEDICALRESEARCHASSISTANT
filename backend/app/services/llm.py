import json
from abc import ABC, abstractmethod
from typing import Any

from app.core.config import get_settings


def _drop_lone_surrogates(value: Any) -> Any:
    """Strip unpaired \\uXXXX surrogates a model may emit when paraphrasing
    special characters (e.g. "≥", "μ"). `json.loads` accepts a lone
    surrogate codepoint without complaint, but re-encoding it to UTF-8
    later (e.g. FastAPI serializing the HTTP response) raises
    UnicodeEncodeError, so this is cleaned up right after parsing.
    """
    if isinstance(value, str):
        return value.encode("utf-16", "surrogatepass").decode("utf-16", "replace")
    if isinstance(value, list):
        return [_drop_lone_surrogates(item) for item in value]
    if isinstance(value, dict):
        return {key: _drop_lone_surrogates(item) for key, item in value.items()}
    return value


class LLMClient(ABC):
    @abstractmethod
    async def complete(self, system: str, prompt: str, max_tokens: int = 1024, json_mode: bool = False) -> str: ...

    async def complete_json(self, system: str, prompt: str, max_tokens: int = 1024) -> dict[str, Any]:
        """Call `complete` and parse the response as JSON.

        Raises `ValueError` if the model didn't return valid JSON, since a
        stray sentence around the object is a real failure for callers that
        need structured data, not something to silently paper over.
        """
        raw = await self.complete(system, prompt, max_tokens=max_tokens, json_mode=True)
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        try:
            parsed = json.loads(text.strip())
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM did not return valid JSON: {raw!r}") from exc
        return _drop_lone_surrogates(parsed)


class AnthropicLLMClient(LLMClient):
    def __init__(self, api_key: str | None, model: str) -> None:
        self._api_key = api_key
        self._model = model

    async def complete(self, system: str, prompt: str, max_tokens: int = 1024, json_mode: bool = False) -> str:
        if not self._api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")

        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self._api_key)
        response = await client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in response.content if block.type == "text")


class OllamaLLMClient(LLMClient):
    """Talks to a local Ollama server — no API key required."""

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def complete(self, system: str, prompt: str, max_tokens: int = 1024, json_mode: bool = False) -> str:
        import httpx

        # Ollama defaults num_ctx to 2048 regardless of what the model can
        # actually handle, which silently truncates input for agents that
        # stuff in many search results (e.g. a dozen+ trial records) — size
        # the context window to the request instead of leaving it fixed.
        estimated_input_tokens = (len(system) + len(prompt)) // 4
        num_ctx = min(max(estimated_input_tokens + max_tokens + 512, 4096), 32768)

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {"num_predict": max_tokens, "num_ctx": num_ctx},
        }
        if json_mode:
            # Grammar-constrained decoding: guarantees syntactically valid
            # JSON output, which small local models otherwise often ignore
            # in favor of chatty prose despite explicit prompt instructions.
            payload["format"] = "json"

        # Local CPU/GPU-constrained inference on larger contexts can take a
        # while — generous timeout so a slow machine doesn't look "broken".
        async with httpx.AsyncClient(base_url=self._base_url, timeout=300.0) as client:
            try:
                response = await client.post("/api/chat", json=payload)
                response.raise_for_status()
            except httpx.ConnectError as exc:
                raise RuntimeError(
                    f"Could not reach Ollama at {self._base_url} — is `ollama serve` running?"
                ) from exc
            return response.json()["message"]["content"]


def get_llm_client() -> LLMClient:
    settings = get_settings()
    if settings.llm_provider == "anthropic":
        return AnthropicLLMClient(api_key=settings.anthropic_api_key, model=settings.anthropic_model)
    if settings.llm_provider == "ollama":
        return OllamaLLMClient(base_url=settings.ollama_base_url, model=settings.ollama_model)
    raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider!r}")
