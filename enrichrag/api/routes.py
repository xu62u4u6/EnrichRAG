"""API routes with SSE streaming."""

import asyncio
import json
import math
import re
from pathlib import Path
from queue import Empty, Queue

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from enrichrag.core.chat_context import build_chat_prompt_inputs
from enrichrag.core.gene_validation import GeneValidationService
from enrichrag.core.pipeline import run_pipeline
from enrichrag.prompts.generator import PromptGenerator
from enrichrag.settings import settings
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from .models import ChatRequest

router = APIRouter()


def _json_safe(value):
    """Recursively convert NaN/Infinity values into JSON-safe nulls."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _sse_payload(payload: dict) -> str:
    safe_payload = _json_safe(payload)
    return "data: " + json.dumps(safe_payload, ensure_ascii=False, allow_nan=False) + "\n\n"


def _parse_genes(raw: str) -> list[str]:
    """Split gene string by commas, spaces, or newlines."""
    return [g.strip().upper() for g in re.split(r"[,\s\n]+", raw) if g.strip()]


@router.get("/api/health")
async def health():
    return {"status": "ok"}


@router.post("/api/genes/validate")
async def validate_genes(payload: dict):
    service = GeneValidationService()
    genes = _parse_genes(payload.get("genes", ""))
    return _json_safe(service.validate(genes))


@router.get("/api/genes/{symbol}")
async def gene_profile(symbol: str):
    service = GeneValidationService()
    profile = service.get_profile(symbol)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Gene profile not found: {symbol}")
    return _json_safe(profile)


@router.get("/api/analyze/stream")
async def analyze_stream(
    genes: str = Query(..., description="Gene symbols"),
    disease: str = Query("cancer"),
    pval: float = Query(0.05, ge=0.0, le=1.0),
):
    service = GeneValidationService()
    gene_list = service.normalize_genes(_parse_genes(genes))
    if not gene_list:
        return StreamingResponse(
            iter([_sse_payload({"event": "error", "message": "No genes"})]),
            media_type="text/event-stream",
        )

    progress_queue: Queue = Queue()

    def on_progress(step, message, **kwargs):
        msg = {"event": step, "message": message}
        if kwargs.get("data") is not None:
            msg["data"] = kwargs["data"]
        progress_queue.put(msg)

    async def event_generator():
        loop = asyncio.get_event_loop()
        task = loop.run_in_executor(
            None, lambda: run_pipeline(gene_list, disease, pval, on_progress)
        )

        while True:
            # Drain progress messages
            try:
                while True:
                    msg = progress_queue.get_nowait()
                    yield _sse_payload(msg)
            except Empty:
                pass

            if task.done():
                # Drain remaining
                while not progress_queue.empty():
                    msg = progress_queue.get_nowait()
                    yield _sse_payload(msg)

                try:
                    result = task.result()
                    yield _sse_payload({"event": "result", "data": result})
                except Exception as e:
                    yield _sse_payload({"event": "error", "message": str(e)})
                break

            await asyncio.sleep(0.3)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/api/chat")
async def chat_stream(request: ChatRequest):
    if not settings.openai_api_key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY is not configured.")
    if not request.result:
        raise HTTPException(status_code=400, detail="Pipeline result payload is required.")

    async def event_generator():
        try:
            llm = ChatOpenAI(
                model=settings.llm_model_report,
                temperature=0.2,
                api_key=settings.openai_api_key,
                streaming=True,
            )
            prompt_path = Path(__file__).parent.parent / "prompts" / "templates" / "chat_qa.yaml"
            generator = PromptGenerator(template_path=str(prompt_path))
            chain = generator.prompt_template | llm | StrOutputParser()
            prompt_inputs = build_chat_prompt_inputs(request.result, request.query)

            async for chunk in chain.astream(prompt_inputs):
                yield _sse_payload({"event": "chunk", "data": chunk})

            yield _sse_payload({"event": "done", "data": ""})
        except Exception as e:
            yield _sse_payload({"event": "error", "message": str(e)})

    return StreamingResponse(event_generator(), media_type="text/event-stream")
