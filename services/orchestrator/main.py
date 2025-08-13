import json
import logging
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import redis.asyncio as redis

load_dotenv(override=True)

instance_id = os.getenv('INSTANCE_ID', 'unknown')

logging.basicConfig(
    level=logging.INFO,
    format=f'%(asctime)s - {instance_id} - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title=f"Orchestrator - {instance_id}")
llm = ChatOpenAI()

redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    decode_responses=True
)

class ChatRequest(BaseModel):
    message: str
    session_id: str

class ChatResponse(BaseModel):
    response: str
    session_id: str

async def get_session_state(session_id: str):
    state = await redis_client.get(f"session:{session_id}")
    if state:
        return json.loads(state)
    return {"messages": [], "created_at": None}

def save_session_state(session_id: str, state):
    redis_client.setex(
        f"session:{session_id}",
        3600,
        json.dumps(state, default=str)
    )

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        session_state = await get_session_state(request.session_id)
        
        session_state["messages"].append({
            "role": "user",
            "content": request.message
        })

        response = llm.invoke(session_state["messages"])

        session_state["messages"].append({
            "role": "assistant",
            "content": response.content
        })

        save_session_state(request.session_id, session_state)

        logger.info(f"Successfully processed session {request.session_id}")
        
        return ChatResponse(
            response=str(response.content), # TODO: update types
            session_id=request.session_id
        )
    except Exception as e:
        logger.error(f"Error processing session {request.session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))