import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
from starlette.responses import StreamingResponse

from app.agent import AgentWorkflow
from app.backend_client import BackendClient
from app.models import ChatRequest, ChatResponse

app = FastAPI(title="IWOA Agent Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

workflow = AgentWorkflow()
backend_client = BackendClient()


@app.get("/health")
async def health() -> dict[str, object]:
    backend_reachable = False
    backend_status = "down"

    try:
        backend = await backend_client.health()
        backend_status = backend.get("status", "unknown")
        backend_reachable = backend_status.lower() == "up"
    except httpx.HTTPError:
        backend_status = "down"

    return {
        "status": "ok" if workflow.llm_client else "degraded",
        "model": workflow.settings.model,
        "model_configured": workflow.settings.is_configured,
        "backend_reachable": backend_reachable,
        "backend_status": backend_status,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    intent, answer, tool_calls = await workflow.run(request.message, request.user_id)
    return ChatResponse(intent=intent, answer=answer, tool_calls=tool_calls)


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    async def event_stream():
        async for event in workflow.stream(request.message, request.user_id):
            yield json.dumps(event, ensure_ascii=False) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")
