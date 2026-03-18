import os
import json
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch
from langchain.chains import RetrievalQA

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

def build_rag_chain() -> RetrievalQA:
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    search_key = os.getenv("AZURE_SEARCH_KEY")
    if not search_endpoint or not search_key:
        raise RuntimeError("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be configured")

    embeddings = AzureOpenAIEmbeddings(
        azure_deployment=os.getenv("EMBEDDING_DEPLOYMENT", "text-embedding-3-large"),
        openai_api_version=os.getenv("OPENAI_API_VERSION", "2024-05-13"),
    )

    vector_store = AzureSearch(
        azure_search_endpoint=search_endpoint,
        azure_search_key=search_key,
        index_name=os.getenv("AZURE_SEARCH_INDEX", "manuals-index"),
        embedding_function=embeddings.embed_query,
    )

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
