import uuid
from typing import Any

from app.services.embeddings import get_embedder
from app.services.vector_store import get_vector_store

# Pages with less extractable text than this are assumed to be scanned
# images (no text layer) and get OCR'd instead of used as-is.
_MIN_CHARS_PER_PAGE = 20
_CHUNK_SIZE = 1200
_CHUNK_OVERLAP = 150

_ocr_engine: Any = None


def _get_ocr_engine() -> Any:
    """Lazily creates and caches the OCR engine — it loads ONNX models from
    disk on first use, which is too slow to redo on every request."""
    global _ocr_engine
    if _ocr_engine is None:
        from rapidocr_onnxruntime import RapidOCR

        _ocr_engine = RapidOCR()
    return _ocr_engine


def _ocr_page(page: Any) -> str:
    pixmap = page.get_pixmap(dpi=200)
    image_bytes = pixmap.tobytes("png")
    result, _ = _get_ocr_engine()(image_bytes)
    if not result:
        return ""
    return "\n".join(line[1] for line in result)


def _chunk_text(text: str, size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        chunk = text[start : start + size].strip()
        if chunk:
            chunks.append(chunk)
        start += size - overlap
    return chunks


def ingest_pdf(filename: str, file_bytes: bytes) -> dict[str, Any]:
    """Extracts text from a PDF, OCR'ing any page whose text layer is
    missing or too sparse (i.e. a scanned image), then chunks and indexes
    the result into the vector store so it's searchable alongside the
    PubMed abstracts the Literature Review agent already indexes there.
    """
    import fitz

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        page_texts: list[str] = []
        ocr_pages: list[int] = []
        for page_index in range(doc.page_count):
            page = doc[page_index]
            text = page.get_text("text").strip()
            if len(text) < _MIN_CHARS_PER_PAGE:
                ocr_text = _ocr_page(page).strip()
                if len(ocr_text) > len(text):
                    text = ocr_text
                    ocr_pages.append(page_index + 1)
            page_texts.append(text)
        page_count = doc.page_count
    finally:
        doc.close()

    full_text = "\n\n".join(t for t in page_texts if t)
    doc_id = uuid.uuid4().hex[:12]

    chunks = _chunk_text(full_text)
    if chunks:
        embedder = get_embedder()
        vector_store = get_vector_store()
        vector_store.upsert(
            ids=[f"doc:{doc_id}:{i}" for i in range(len(chunks))],
            embeddings=embedder.embed(chunks),
            metadatas=[
                {"source": "document", "doc_id": doc_id, "filename": filename, "chunk_index": i, "text": chunk}
                for i, chunk in enumerate(chunks)
            ],
        )

    return {
        "doc_id": doc_id,
        "filename": filename,
        "page_count": page_count,
        "ocr_pages": ocr_pages,
        "chunks_indexed": len(chunks),
        "text": full_text,
    }
