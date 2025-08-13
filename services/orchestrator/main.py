import logging
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

instance_id = os.getenv('INSTANCE_ID', 'unknown')

logging.basicConfig(
    level=logging.INFO,
    format=f'%(asctime)s - {instance_id} - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title=f"Orchestrator - {instance_id}")
llm = ChatOpenAI()

sessions = {} # TODO: add redis

class ChatRequest(BaseModel):
    message: str
    session_id: str

class ChatResponse(BaseModel):
    response: str
    session_id: str

@app.post("/chat")
def chat(request: ChatRequest):
    try:
        if request.session_id not in sessions:
            sessions[request.session_id] = []
        
        sessions[request.session_id].append({"role": "user", "content": request.message})
        response = llm.invoke(sessions[request.session_id])
        sessions[request.session_id].append({"role": "assistant", "content": response.content})
        
        logger.info(f"Successfully processed session {request.session_id}")
        return ChatResponse(
            response=str(response.content), # TODO: update types
            session_id=request.session_id
        )
    except Exception as e:
        logger.error(f"Error processing session {request.session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))