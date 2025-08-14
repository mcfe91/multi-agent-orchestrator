import json
import socket
import uuid
import logging
import os
import time
from typing import TypedDict

from fastapi import FastAPI, HTTPException
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from pydantic import BaseModel
import redis.asyncio as redis
from dotenv import load_dotenv

from shared.models import AgentState, ChatRequest, ChatResponse

load_dotenv(override=True)

instance_id = os.getenv('INSTANCE_ID', 'unknown')
logging.basicConfig(
    level=logging.INFO,
    format=f'%(asctime)s - {instance_id} - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title=f"Orchestrator - {instance_id}")

redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    decode_responses=True
)

class AgentOrchestrator:
    def __init__(self, instance_id):
        self.instance_id = instance_id
        self.active_sessions = {}
        self.llm = ChatOpenAI()

    def get_or_create_agent(self, session_id: str):
        if session_id not in self.active_sessions:
            logger.info(f"Creating new agent workflow for session {session_id}")

            agent = self.create_agent_graph()

            self.active_sessions[session_id] = {
                "agent": agent,
                "last_used": time.time(),
                "created_at": time.time(),
                "message_count": 0
            }
        
        self.active_sessions[session_id]["last_used"] = time.time()
        self.active_sessions[session_id]["message_count"] += 1

        return self.active_sessions[session_id]["agent"]
    
    def create_agent_graph(self):
        def reasoning_node(state: AgentState) -> AgentState:
            messages = state["messages"]
            response = self.llm.invoke(messages)
            return AgentState(
                result=str(response.content), # TODO: update types
                messages=messages
            )
        
        workflow = StateGraph(AgentState)
        workflow.add_node("reasoning", reasoning_node)
        workflow.set_entry_point("reasoning")
        workflow.add_edge("reasoning", END)

        return workflow.compile()
    
    def cleanup_inactive_sessions(self):
        pass # TODO: clean up old sessions with redis state ttl or not when we use real DB
    
agent_manager = AgentOrchestrator(instance_id)

# TODO: move to shared redis client module
async def get_session_state(session_id: str):
    state = await redis_client.get(f"session:{session_id}")
    if state:
        return json.loads(state)
    return {"messages": [], "created_at": None}

async def save_session_state(session_id: str, state):
    await redis_client.setex(
        f"session:{session_id}",
        3600,
        json.dumps(state, default=str)
    )

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        session_state = await get_session_state(request.session_id)

        agent_orchestrator = agent_manager.get_or_create_agent(request.session_id)
        
        session_state["messages"].append({
            "role": "user",
            "content": request.message
        })

        agent_state: AgentState = {
            "messages": session_state["messages"],
            "result": ""
        }

        result = agent_orchestrator.invoke(agent_state)

        session_state["messages"].append({
            "role": "assistant",
            "content": result["result"]
        })

        await save_session_state(request.session_id, session_state)

        logger.info(f"Successfully processed session {request.session_id}")
        
        return ChatResponse(
            response=result["result"],
            session_id=request.session_id
        )
    except Exception as e:
        logger.error(f"Error processing session {request.session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))