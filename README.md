# TODO:
- Implement planner/executor nodes with dynamic graph generation in agent orchestrator
- Separate dependencies per service
- Implement sub-agent services
- Add sub-agent service discovery 

# API Test Command

```bash
curl -X POST http://localhost:8000/chat \
 -H "Content-Type: application/json" \
 -d '{"message": "hello", "session_id": "session123"}'
```

```bash
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{"message": "my name is alice", "session_id": "user456"}'

curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{"message": "what is my name?", "session_id": "user456"}'
```

# Docker
```bash
alias dcr="docker compose down && docker compose up -d --build"
```

# Redis
```bash
docker exec -it $(docker ps -q -f name=redis) redis-cli
> KEYS session_route:*
> GET session_route:user456
> GET session_route:user4516
```