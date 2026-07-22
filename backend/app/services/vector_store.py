from abc import ABC, abstractmethod
from typing import Any

from app.core.config import get_settings


class VectorStore(ABC):
    @abstractmethod
    def upsert(self, ids: list[str], embeddings: list[list[float]], metadatas: list[dict[str, Any]]) -> None: ...

    @abstractmethod
    def query(self, embedding: list[float], top_k: int = 5) -> list[dict[str, Any]]: ...


class ChromaVectorStore(VectorStore):
    def __init__(self, persist_dir: str, collection_name: str = "medical_research") -> None:
        import chromadb

        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection = self._client.get_or_create_collection(collection_name)

    def upsert(self, ids: list[str], embeddings: list[list[float]], metadatas: list[dict[str, Any]]) -> None:
        self._collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas)

    def query(self, embedding: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        result = self._collection.query(query_embeddings=[embedding], n_results=top_k)
        return result.get("metadatas", [[]])[0]


def get_vector_store() -> VectorStore:
    settings = get_settings()
    if settings.vector_store_provider == "chroma":
        return ChromaVectorStore(persist_dir=settings.chroma_persist_dir)
    raise NotImplementedError(
        f"Vector store provider '{settings.vector_store_provider}' is not wired up yet"
    )
