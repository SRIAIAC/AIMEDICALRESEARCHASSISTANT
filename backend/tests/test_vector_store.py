from app.services.embeddings import HashEmbedder
from app.services.vector_store import ChromaVectorStore


def test_chroma_upsert_and_query_roundtrip(tmp_path) -> None:
    store = ChromaVectorStore(persist_dir=str(tmp_path), collection_name="test")
    embedder = HashEmbedder(dims=32)

    texts = ["metformin lowers blood glucose", "chemotherapy targets rapidly dividing cells"]
    embeddings = embedder.embed(texts)
    store.upsert(
        ids=["a", "b"],
        embeddings=embeddings,
        metadatas=[{"title": "doc a"}, {"title": "doc b"}],
    )

    results = store.query(embeddings[0], top_k=1)
    assert results[0]["title"] == "doc a"
