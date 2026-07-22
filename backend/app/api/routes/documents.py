from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.agents.document_qa import DocumentQAAgent
from app.models.schemas import DocumentQARequest
from app.services.cache import cached
from app.services.embeddings import get_embedder
from app.services.pdf_ingestion import ingest_pdf
from app.services.vector_store import get_vector_store

router = APIRouter(prefix="/documents", tags=["documents"])

_MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)) -> dict:
    filename = file.filename or "document.pdf"
    if not filename.lower().endswith(".pdf") and file.content_type not in (
        "application/pdf",
        "application/x-pdf",
    ):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(contents) > _MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 25 MB)")

    try:
        # ingest_pdf uses PyMuPDF + OCR, both blocking/CPU-bound — run off
        # the event loop so one big upload doesn't stall every other request.
        return await run_in_threadpool(ingest_pdf, filename, contents)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not process PDF: {exc}") from exc


class DocumentSearchRequest(BaseModel):
    query: str = Field(..., min_length=2)
    top_k: int = 5


@router.post("/search")
async def search_documents(request: DocumentSearchRequest) -> dict:
    embedder = get_embedder()
    vector_store = get_vector_store()
    [embedding] = embedder.embed([request.query])
    results = vector_store.query(embedding, top_k=request.top_k)
    return {"query": request.query, "results": results}


@router.post("/ask")
async def ask_documents(request: DocumentQARequest) -> dict:
    return await cached(
        "document_qa",
        {"question": request.question, "top_k": request.top_k},
        1800,
        lambda: DocumentQAAgent().run(request.question, {"top_k": request.top_k}),
    )
