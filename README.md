# API Test Command

```bash
curl -X POST http://localhost:8000/chat \
 -H "Content-Type: application/json" \
 -d '{"message": "hello", "session_id": "session123"}'
```

# Docker
```bash
alias dcr="docker compose down && docker compose up -d --build"
```