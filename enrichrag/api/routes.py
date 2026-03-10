"""API routes with SSE streaming."""

import asyncio
import json
import re
from queue import Empty, Queue

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from enrichrag.core.pipeline import run_pipeline

router = APIRouter()


def _parse_genes(raw: str) -> list[str]:
    """Split gene string by commas, spaces, or newlines."""
    return [g.strip().upper() for g in re.split(r"[,\s\n]+", raw) if g.strip()]


@router.get("/api/health")
async def health():
    return {"status": "ok"}


@router.get("/api/analyze/stream")
async def analyze_stream(
    genes: str = Query(..., description="Gene symbols"),
    disease: str = Query("cancer"),
    pval: float = Query(0.05, ge=0.0, le=1.0),
):
    gene_list = _parse_genes(genes)
    if not gene_list:
        return StreamingResponse(
            iter(["data: " + json.dumps({"event": "error", "message": "No genes"}) + "\n\n"]),
            media_type="text/event-stream",
        )

    progress_queue: Queue = Queue()

    def on_progress(step: str, message: str):
        progress_queue.put({"event": step, "message": message})

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
                    yield f"data: {json.dumps(msg)}\n\n"
            except Empty:
                pass

            if task.done():
                # Drain remaining
                while not progress_queue.empty():
                    msg = progress_queue.get_nowait()
                    yield f"data: {json.dumps(msg)}\n\n"

                try:
                    result = task.result()
                    yield f"data: {json.dumps({'event': 'result', 'data': result})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
                break

            await asyncio.sleep(0.3)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
