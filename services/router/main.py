import hashlib
import json
import logging
import os
import socket
from typing import List
from dotenv import load_dotenv
import httpx

from fastapi import FastAPI, HTTPException
import redis.asyncio as redis

from shared.models import ChatRequest, RouteRequest

load_dotenv(override=True)

instance_id = os.getenv('INSTANCE_ID', 'unknown')
logging.basicConfig(
    level=logging.INFO,
    format=f'%(asctime)s - {instance_id} - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title=f"Router - {instance_id}")

redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    decode_responses=True
)

class AgentInstance:
    def __init__(self, host: str, port: int, agent_type: str = "general"):
        self.host = host
        self.port = port
        self.agent_type = agent_type
        self.base_url = f"http://{host}:{port}" # TODO: https, move transport to configs
        self.healthy = True

    async def health_check(self):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health", timeout=5.0) # TODO: move to configs
                self.healthy = response.status_code == 200 # TODO: harden
        except:
            self.healthy = False

        return self.healthy

class AgentRouter:
    def __init__(self):
        self.instances = self.discover_agent_services()

    def discover_agent_services(self) -> List[AgentInstance]:
        # TODO: hard coded
        return  [
            AgentInstance("orchestrator-1", 8000, "general"),
            AgentInstance("orchestrator-2", 8000, "general"),
        ]

    async def get_agent_orchestrator_for_session(self, session_id: str, agent_type: str = "general"):
        assigned_instance = await redis_client.get(f"session_route:{session_id}") # TODO: deserialized redis data types

        if assigned_instance:
            instance_config = json.loads(assigned_instance) # TODO: handle failure, use pydantic types!
            for instance in self.instances:
                if (instance.host == instance_config["host"] and
                    instance.port == instance_config["port"] and
                    instance.healthy):
                    return instance
                
        healthy_instances = [i for i in self.instances if i.healthy and i.agent_type == agent_type]

        logger.info(f"{healthy_instances[0], healthy_instances[1]}")

        if not healthy_instances:
            raise HTTPException(status_code=503, detail="No healthy agents available")

        hash_value = int(hashlib.md5(session_id.encode()).hexdigest(), 16)
        selected_instance = healthy_instances[hash_value % len(healthy_instances)]

        await redis_client.setex(
            f"session_route:{session_id}",
            3600,
            json.dumps({"host": selected_instance.host, "port": selected_instance.port}) # TODO: deserialized redis data types
        )

        # TODO: handle redis failures

        return selected_instance

router = AgentRouter()

@app.post("/route")
async def route_request(request: RouteRequest):
    try:
        instance = await router.get_agent_orchestrator_for_session(request.session_id)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{instance.base_url}/chat",
                json={"message": request.message, "session_id": request.session_id} # TODO: fix message types
            )      
            return response.json()
        
        logger.info(f"Successfully routed session {request.session_id} to instance: {instance.base_url}/chat")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))