import math

from app.services.embeddings import HashEmbedder


def test_hash_embedder_is_deterministic() -> None:
    embedder = HashEmbedder(dims=64)
    first = embedder.embed(["metformin diabetes treatment"])
    second = embedder.embed(["metformin diabetes treatment"])
    assert first == second


def test_hash_embedder_produces_unit_vectors() -> None:
    embedder = HashEmbedder(dims=64)
    [vector] = embedder.embed(["some clinical trial abstract text"])
    norm = math.sqrt(sum(v * v for v in vector))
    assert math.isclose(norm, 1.0, rel_tol=1e-6)


def test_hash_embedder_distinguishes_different_text() -> None:
    embedder = HashEmbedder(dims=64)
    a, b = embedder.embed(["metformin", "chemotherapy"])
    assert a != b
