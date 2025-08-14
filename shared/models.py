from typing import TypedDict
from pydantic import BaseModel


# Router
class RouteRequest(BaseModel):
    session_id: str
    message: str

# Agent Orchestrator
class ChatRequest(BaseModel):
    message: str
    session_id: str

class ChatResponse(BaseModel):
    response: str
    session_id: str

class AgentState(TypedDict):
    messages: list
    result: str