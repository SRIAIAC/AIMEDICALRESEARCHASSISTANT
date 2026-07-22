import hashlib
import math
from abc import ABC, abstractmethod

from app.core.config import get_settings


class Embedder(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashEmbedder(Embedder):
    """Deterministic bag-of-words embedder with no model download or GPU
    requirement. Used as the default so the app runs out of the box;
    swap to SentenceTransformerEmbedder for production-quality retrieval.
    """

    def __init__(self, dims: int = 256) -> None:
        self._dims = dims

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self._dims
        for token in text.lower().split():
            index = int(hashlib.sha256(token.encode()).hexdigest(), 16) % self._dims
            vector[index] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]


class SentenceTransformerEmbedder(Embedder):
    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts).tolist()


class OllamaEmbedder(Embedder):
    """Real semantic embeddings via a local Ollama model (e.g.
    `nomic-embed-text`) — no extra Python ML stack to install since it's
    just an HTTP call to the same Ollama server the LLM client already
    talks to.
    """

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        import httpx

        with httpx.Client(base_url=self._base_url, timeout=60.0) as client:
            try:
                response = client.post("/api/embed", json={"model": self._model, "input": texts})
                response.raise_for_status()
            except httpx.ConnectError as exc:
                raise RuntimeError(
                    f"Could not reach Ollama at {self._base_url} — is `ollama serve` running?"
                ) from exc
            return response.json()["embeddings"]


def get_embedder() -> Embedder:
    settings = get_settings()
    if settings.embedding_provider == "sentence_transformers":
        return SentenceTransformerEmbedder(settings.embedding_model)
    if settings.embedding_provider == "ollama":
        return OllamaEmbedder(base_url=settings.ollama_base_url, model=settings.ollama_embedding_model)
    return HashEmbedder()
