from fastapi import FastAPI
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

app = FastAPI()
llm = ChatOpenAI()

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
def chat(request: ChatRequest):
    response = llm.invoke(request.message)
    return {"response": response.content}