from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..ai.provider import get_ai_provider
from ..database import get_db
from ..models import ChatMessage, Voyage
from ..schemas import AgentRunOut, ChatMessageOut, ChatRequest, ChatResponse
from ..services.agent import recent_runs, run_agent

router = APIRouter(tags=["agent"])


@router.post("/agent/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    if payload.voyage_id and not db.get(Voyage, payload.voyage_id):
        raise HTTPException(status_code=404, detail=f"Voyage {payload.voyage_id} not found")
    result = run_agent(
        db,
        message=payload.message.strip(),
        session_id=payload.session_id or "default",
        voyage_id=payload.voyage_id,
    )
    return ChatResponse(**result)


@router.get("/agent/runs", response_model=list[AgentRunOut])
def agent_runs(limit: int = 20, db: Session = Depends(get_db)):
    return recent_runs(db, limit)


@router.get("/agent/messages", response_model=list[ChatMessageOut])
def agent_messages(session_id: str = "default", limit: int = 50, db: Session = Depends(get_db)):
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(desc(ChatMessage.id))
        .limit(limit)
        .all()
    )
    return list(reversed(rows))


@router.get("/agent/provider")
def agent_provider():
    provider = get_ai_provider()
    return {"provider": provider.name, "model": provider.model}
