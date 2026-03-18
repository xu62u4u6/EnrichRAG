"""API routes with SSE streaming."""

import asyncio
import json
import math
import re
from pathlib import Path
from queue import Empty, Queue

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse

from enrichrag.core.chat_context import build_chat_prompt_inputs
from enrichrag.core.gene_validation import GeneValidationService
from enrichrag.core.pipeline import run_pipeline
from enrichrag.prompts.generator import PromptGenerator
from enrichrag.settings import settings
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from enrichrag.auth_store import (
    authenticate_user,
    clear_analysis_runs,
    create_user,
    create_session,
    delete_analysis_run,
    delete_session,
    get_analysis_run,
    get_user_by_session,
    list_analysis_runs,
    save_analysis_run,
)

from .models import ChatRequest, LoginRequest, RegisterRequest

router = APIRouter()


def _cookie_kwargs() -> dict:
    return {
        "httponly": True,
        "samesite": "lax",
        "secure": settings.auth_secure_cookies,
        "path": "/",
    }


def _current_user(request: Request) -> dict:
    token = request.cookies.get(settings.auth_cookie_name)
    user = get_user_by_session(token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user


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


@router.post("/api/auth/login")
async def login(payload: LoginRequest, response: Response):
    user = authenticate_user(payload.email.strip(), payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    token = create_session(user["id"])
    response.set_cookie(settings.auth_cookie_name, token, max_age=7 * 24 * 60 * 60, **_cookie_kwargs())
    return user


@router.post("/api/auth/register")
async def register(payload: RegisterRequest, response: Response):
    try:
        user = create_user(payload.email, payload.password, payload.display_name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    token = create_session(user["id"])
    response.set_cookie(settings.auth_cookie_name, token, max_age=7 * 24 * 60 * 60, **_cookie_kwargs())
    return user


@router.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    delete_session(request.cookies.get(settings.auth_cookie_name))
    response.delete_cookie(settings.auth_cookie_name, path="/")
    return {"ok": True}


@router.get("/api/auth/me")
async def auth_me(request: Request):
    token = request.cookies.get(settings.auth_cookie_name)
    return get_user_by_session(token)


@router.get("/api/history")
async def history(user: dict = Depends(_current_user)):
    return {"items": list_analysis_runs(user["id"])}


@router.get("/api/history/{analysis_id}")
async def history_item(analysis_id: int, user: dict = Depends(_current_user)):
    item = get_analysis_run(user["id"], analysis_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return _json_safe(item)


@router.delete("/api/history/{analysis_id}")
async def delete_history_item(analysis_id: int, user: dict = Depends(_current_user)):
    if not delete_analysis_run(user["id"], analysis_id):
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return {"ok": True}


@router.delete("/api/history")
async def clear_history(user: dict = Depends(_current_user)):
    clear_analysis_runs(user["id"])
    return {"ok": True}


@router.post("/api/genes/validate")
async def validate_genes(payload: dict, user: dict = Depends(_current_user)):
    service = GeneValidationService()
    genes = _parse_genes(payload.get("genes", ""))
    return _json_safe(service.validate(genes))


@router.get("/api/genes/{symbol}")
async def gene_profile(symbol: str, user: dict = Depends(_current_user)):
    service = GeneValidationService()
    profile = service.get_profile(symbol)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Gene profile not found: {symbol}")
    return _json_safe(profile)


@router.get("/api/analyze/stream")
async def analyze_stream(
    request: Request,
    genes: str = Query(..., description="Gene symbols"),
    disease: str = Query("cancer"),
    pval: float = Query(0.05, ge=0.0, le=1.0),
):
    user = _current_user(request)
    service = GeneValidationService()
    parsed_genes = _parse_genes(genes)
    validation_result = service.validate(parsed_genes)
    gene_list = service.normalize_genes(parsed_genes)
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
                    result["gene_validation"] = validation_result
                    save_analysis_run(user["id"], result)
                    yield _sse_payload({"event": "result", "data": result})
                except Exception as e:
                    yield _sse_payload({"event": "error", "message": str(e)})
                break

            await asyncio.sleep(0.3)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/api/chat")
async def chat_stream(request: ChatRequest, user: dict = Depends(_current_user)):
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
