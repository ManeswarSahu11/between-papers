import os
import logging
import secrets
from fastapi.responses import JSONResponse
from functools import lru_cache
from dataclasses import dataclass

from starlette.concurrency import run_in_threadpool

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .pdf_utils import extract_pdf_text
from .rag_pipeline import build_generation_graph, get_embeddings_client, get_llm_client, split_text, to_references
from .schemas import AskRequest, AskResponse, IngestResponse, RecommendedPaper
from .translator_client import detect_language, translate
from .vector_store import ensure_collection, insert_chunks, search_similar


if config.GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY

app = FastAPI(title=config.APP_NAME, version=config.APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def require_api_token(request, call_next):
    if config.API_ACCESS_TOKEN and request.url.path != "/healthz":
        supplied = request.headers.get("X-API-Key", "")
        if not secrets.compare_digest(supplied, config.API_ACCESS_TOKEN):
            return JSONResponse(status_code=401, content={"detail": "Access denied."})
    return await call_next(request)


logger = logging.getLogger(__name__)


@dataclass
class Services:
    embeddings: object
    graph: object
    collection: object


@lru_cache(maxsize=1)
def get_services():
    if not config.GOOGLE_API_KEY:
        raise HTTPException(status_code=503, detail="Research service is not configured. Contact the maintainer.")
    try:
        return Services(get_embeddings_client(), build_generation_graph(get_llm_client()), ensure_collection(index_type=config.MILVUS_INDEX_TYPE))
    except Exception as exc:
        logger.warning("Research initialization failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Research service is unavailable. Please try again later.") from exc


def provider_call(operation, *args, **kwargs):
    try:
        return operation(*args, **kwargs)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Research provider failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=502, detail="A research provider could not complete the request. Please try again.") from exc


def _validate_domain(domain: str) -> None:
    if domain not in config.SUPPORTED_DOMAINS:
        raise HTTPException(status_code=400, detail=f"Unsupported domain '{domain}'. Use one of {sorted(config.SUPPORTED_DOMAINS)}")


def _validate_language(language: str) -> None:
    if language not in config.SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Unsupported language '{language}'. Use one of {sorted(config.SUPPORTED_LANGUAGES)}")


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/readyz")
def readyz():
    get_services()
    return {"ok": True, "scope": "Clients initialized; not an end-to-end provider check"}


@app.post("/ingest", response_model=IngestResponse)
async def ingest_paper(
    file: UploadFile = File(...),
    paper_title: str = Form(...),
    domain: str = Form(...),
    language: str = Form(...),
    exclude_references: bool = Form(True),
):
    _validate_domain(domain)
    _validate_language(language)
    paper_title = paper_title.strip()
    if not paper_title or len(paper_title.encode("utf-8")) > 1024:
        raise HTTPException(status_code=400, detail="Provide a document title up to 1024 UTF-8 bytes.")
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")

    file_bytes = await file.read(config.MAX_UPLOAD_BYTES + 1)
    if len(file_bytes) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="PDF exceeds the upload size limit.")
    if not file_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="The uploaded file is not a PDF.")
    try:
        text = await run_in_threadpool(extract_pdf_text, file_bytes, exclude_references=exclude_references)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not read this PDF. Use an unencrypted, text-based PDF.") from exc
    if not text:
        raise HTTPException(status_code=400, detail="No parseable text found in PDF")

    chunks = split_text(text)
    services = await run_in_threadpool(get_services)
    vectors = await run_in_threadpool(provider_call, services.embeddings.embed_documents, chunks)
    inserted = await run_in_threadpool(provider_call, insert_chunks, services.collection, paper_title=paper_title, domain=domain, language=language, chunks=chunks, embeddings=vectors)

    return IngestResponse(
        paper_title=paper_title,
        domain=domain,
        language=language,
        inserted_chunks=inserted,
    )


@app.post("/ask", response_model=AskResponse)
def ask_question(payload: AskRequest):
    _validate_domain(payload.domain)

    source_language = payload.source_language or provider_call(detect_language, payload.question)
    _validate_language(source_language)

    question_en = payload.question if source_language == "en" else provider_call(translate, payload.question, source_language, "en")
    services = get_services()
    question_vector = provider_call(services.embeddings.embed_query, question_en)
    search_results = provider_call(search_similar, services.collection, query_embedding=question_vector, domain=payload.domain, top_k=config.TOP_K)
    retrieved_chunks = [r.text_chunk for r in search_results]

    if not search_results:
        answer = "No indexed passages were found in this category. Upload a document in this category first."
        if source_language != "en":
            answer = provider_call(translate, answer, "en", source_language)
        return AskResponse(answer=answer, language=source_language, recommended_papers=[], references=[])

    state = provider_call(services.graph.invoke,
        {
            "user_question": payload.question,
            "working_question_en": question_en,
            "retrieved_chunks": retrieved_chunks,
        }
    )
    answer_en = state.get("answer_en", "I could not generate an answer from the indexed context.")
    final_answer = answer_en if source_language == "en" else provider_call(translate, answer_en, "en", source_language)

    references, recommended = to_references(search_results, limit=2)
    return AskResponse(
        answer=final_answer,
        language=source_language,
        recommended_papers=[RecommendedPaper(**item) for item in recommended],
        references=references,
    )
