import os
import json
import logging
from io import BytesIO
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch
from langchain.chains import RetrievalQA
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

# 1. initialize Rate Limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Enterprise RAG API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

logger = logging.getLogger("enterprise_rag_api")

# Cache RAG chain after first successful initialization.
rag_chain: Optional[RetrievalQA] = None

evaluator_llm = AzureChatOpenAI(
    azure_deployment=os.getenv("EVALUATOR_AZURE_DEPLOYMENT", "gpt-4o"),
    api_version=os.getenv("EVALUATOR_OPENAI_API_VERSION", "2024-05-13"),
    temperature=0,
)


def get_embeddings_client() -> AzureOpenAIEmbeddings:
    return AzureOpenAIEmbeddings(
        azure_deployment=os.getenv("EMBEDDING_DEPLOYMENT", "text-embedding-3-large"),
        openai_api_version=os.getenv("OPENAI_API_VERSION", "2024-05-13"),
    )


def get_vector_store(embeddings: AzureOpenAIEmbeddings) -> AzureSearch:
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    search_key = os.getenv("AZURE_SEARCH_KEY")
    if not search_endpoint or not search_key:
        raise RuntimeError("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be configured")

    return AzureSearch(
        azure_search_endpoint=search_endpoint,
        azure_search_key=search_key,
        index_name=os.getenv("AZURE_SEARCH_INDEX", "manuals-index"),
        embedding_function=embeddings.embed_query,
    )

def build_rag_chain() -> RetrievalQA:
    embeddings = get_embeddings_client()
    vector_store = get_vector_store(embeddings)

    llm = AzureChatOpenAI(
        azure_deployment=os.getenv("CHAT_DEPLOYMENT", "gpt-4o"),
        api_version=os.getenv("OPENAI_API_VERSION", "2024-05-13"),
        temperature=0,
    )

    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vector_store.as_retriever(),
    )


def get_rag_chain() -> RetrievalQA:
    global rag_chain
    if rag_chain is None:
        rag_chain = build_rag_chain()
    return rag_chain


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/ingest")
@limiter.limit("5/minute")
async def ingest_pdfs(request: Request, files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="At least one PDF file is required")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=int(os.getenv("CHUNK_SIZE", "1200")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
    )

    all_chunks: list[str] = []
    all_metadatas: list[dict] = []
    processed_files = 0

    try:
        for upload in files:
            filename = upload.filename or "unnamed.pdf"
            if not filename.lower().endswith(".pdf"):
                continue

            raw_pdf = await upload.read()
            if not raw_pdf:
                continue

            reader = PdfReader(BytesIO(raw_pdf))
            page_count = len(reader.pages)
            if page_count == 0:
                continue

            processed_files += 1
            for page_num, page in enumerate(reader.pages, start=1):
                page_text = (page.extract_text() or "").strip()
                if not page_text:
                    continue

                chunks = splitter.split_text(page_text)
                if not chunks:
                    continue

                for chunk_idx, chunk in enumerate(chunks, start=1):
                    all_chunks.append(chunk)
                    all_metadatas.append(
                        {
                            "source": filename,
                            "page": page_num,
                            "chunk": chunk_idx,
                        }
                    )
    except Exception as e:
        logger.exception("Failed during PDF extraction")
        raise HTTPException(status_code=400, detail=f"PDF extraction failed: {e}")

    if not all_chunks:
        raise HTTPException(
            status_code=400,
            detail="No extractable text found. Ensure uploaded PDFs contain readable text.",
        )

    try:
        embeddings = get_embeddings_client()
        vector_store = get_vector_store(embeddings)
        doc_ids = vector_store.add_texts(texts=all_chunks, metadatas=all_metadatas)
        return {
            "status": "ok",
            "files_processed": processed_files,
            "chunks_indexed": len(all_chunks),
            "documents_upserted": len(doc_ids),
            "index": os.getenv("AZURE_SEARCH_INDEX", "manuals-index"),
        }
    except RuntimeError as e:
        logger.exception("Ingestion configuration error")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Failed to index documents")
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")

@app.get("/query")
@limiter.limit("20/minute") # Max 20 requests per minute per IP
async def query_rag(request: Request, question: str):
    try:
        chain = get_rag_chain()

        # Execute RAG
        response = chain.invoke(question)
        answer = response["result"]
        
        # 4. Evaluation Layer - Self-evaluation using LLM-as-a-judge
        if os.getenv("EVALUATION_ENABLED") == "true":
            try:
                eval_score = evaluate_answer(question, answer)
            except Exception as eval_error:
                eval_score = f"Evaluation unavailable ({type(eval_error).__name__})"
            return {"answer": answer, "eval_score": eval_score}
            
        return {"answer": answer}
    except RuntimeError as e:
        logger.exception("RAG chain configuration error")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Unhandled query error")
        raise HTTPException(status_code=500, detail=str(e))

def evaluate_answer(q, a):
    prompt = f"""
You are an impartial evaluator for a RAG system answer.
Evaluate the assistant answer for this user question.

Question:
{q}

Answer:
{a}

Return ONLY valid JSON with this schema:
{{
  "overall_score": <float between 0 and 10>,
  "faithfulness": <float between 0 and 10>,
  "relevance": <float between 0 and 10>,
  "reason": "<brief one-sentence justification>"
}}
""".strip()

    eval_result = evaluator_llm.invoke(prompt)
    raw = eval_result.content if isinstance(eval_result.content, str) else str(eval_result.content)

    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json\n", "", 1)

    data = json.loads(raw)
    overall = float(data.get("overall_score", 0.0))
    faithfulness = float(data.get("faithfulness", 0.0))
    relevance = float(data.get("relevance", 0.0))
    reason = str(data.get("reason", "No rationale provided"))

    return (
        f"{overall:.1f}/10 "
        f"(Faithfulness: {faithfulness:.1f}, Relevance: {relevance:.1f}) - {reason}"
    )
