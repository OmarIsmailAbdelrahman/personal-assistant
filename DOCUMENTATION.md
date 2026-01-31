# LangGraph Chat Backend - Complete Documentation

## Table of Contents
1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [Setup Guide](#setup-guide)
5. [API Reference](#api-reference)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)
8. [Development](#development)

---

## Overview

A production-ready FastAPI backend for an Android-first chat application with asynchronous LangGraph agent execution.

**Key Features:**
- ✅ Async message processing (202 Accepted pattern)
- ✅ Background job processing with Redis + RQ
- ✅ JWT authentication (email/password)
- ✅ Gemini AI integration (LangGraph-ready)
- ✅ Automatic visualization generation
- ✅ External system integration with retries
- ✅ Structured JSON logging with correlation IDs
- ✅ VM-ready networking configuration

**Tech Stack:**
- **API**: FastAPI + Uvicorn
- **Database**: PostgreSQL 15
- **Cache/Queue**: Redis 7
- **Jobs**: RQ (python-rq)
- **AI**: Gemini API (Google Generative AI)
- **Charts**: Matplotlib
- **Auth**: JWT (PyJWT + passlib)

---

## Quick Start

### Prerequisites
- Docker & Docker Compose installed
- (Optional) Gemini API key

### 1. Initial Setup

```powershell
# Navigate to project
cd "e:\Work\personal projects\personal-assistant"

# Copy environment template
cp .env.example .env

# Edit .env and add your Gemini API key (optional)
notepad .env
```

### 2. Start All Services

```powershell
docker-compose up --build
```

**Wait for startup logs:**
- ✅ PostgreSQL: `database system is ready to accept connections`
- ✅ Redis: `Ready to accept connections`
- ✅ API: `Application startup complete`
- ✅ Worker: `RQ worker listening on 'default' queue`

### 3. Access the API

**Local access:** `http://localhost:8000`
**VM access:** `http://<VM_IP>:8000`

To find VM IP:
```powershell
ipconfig  # Look for IPv4 Address
```

### 4. Test Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy"}
```

---

## Architecture

### System Overview

```
┌─────────────┐
│Android App  │
└──────┬──────┘
       │ HTTP/REST
       ↓
┌─────────────────────────────────────────┐
│         FastAPI API (:8000)             │
│  ┌──────────┐  ┌──────────┐            │
│  │   Auth   │  │ Endpoints│            │
│  │  (JWT)   │  │          │            │
│  └──────────┘  └──────────┘            │
└────┬────────────────┬───────────────┬──┘
     │                │               │
     ↓                ↓               ↓
┌──────────┐    ┌──────────┐   ┌──────────┐
│PostgreSQL│    │  Redis   │   │   Data   │
│  :5432   │    │  :6379   │   │  /media  │
└──────────┘    └────┬─────┘   └──────────┘
                     │
                     ↓
              ┌─────────────┐
              │ RQ Worker   │
              │ (Background)│
              └──────┬──────┘
                     │
        ┌────────────┼────────────┐
        ↓            ↓            ↓
   ┌────────┐  ┌─────────┐  ┌──────────┐
   │ Gemini │  │Matplotlib│  │External  │
   │  API   │  │ Charts  │  │  System  │
   └────────┘  └─────────┘  └──────────┘
```

### Message Flow

1. **Client POST** `/v1/conversations/{id}/messages` with user text
2. **API** creates Message record, AgentRun record, returns **202 Accepted** + run_id
3. **API** enqueues job to Redis
4. **Worker** picks up job from Redis queue
5. **Agent Runner** loads conversation context and executes agent
6. **Agent** calls Gemini API, optionally generates charts
7. **Agent** stores assistant response(s) in database
8. **Agent** calls external system (if configured)
9. **Client** polls `/v1/conversations/{id}/messages` to get responses

### Database Schema

**users**
- `id` (UUID, PK)
- `email` (string, unique)
- `password_hash` (string)
- `external_auth_id` (string)
- `created_at` (timestamp)

**conversations**
- `id` (UUID, PK)
- `user_id` (UUID, FK → users)
- `title` (string, nullable)
- `created_at` (timestamp)

**messages**
- `id` (UUID, PK)
- `conversation_id` (UUID, FK → conversations)
- `sender` (enum: "user" | "assistant" | "system")
- `content_json` (JSONB) - flexible content structure
- `created_at` (timestamp)

**agent_runs**
- `id` (UUID, PK)
- `conversation_id` (UUID, FK → conversations)
- `trigger_message_id` (UUID, FK → messages)
- `status` (enum: "queued" | "running" | "succeeded" | "failed")
- `started_at` (timestamp, nullable)
- `finished_at` (timestamp, nullable)
- `last_error` (text, nullable)

**media**
- `id` (UUID, PK)
- `conversation_id` (UUID, FK → conversations)
- `message_id` (UUID, FK → messages, nullable)
- `media_type` (string, e.g., "image/png")
- `storage_path` (text)
- `created_at` (timestamp)

**integration_deliveries**
- `id` (UUID, PK)
- `run_id` (UUID, FK → agent_runs)
- `status` (enum: "pending" | "succeeded" | "failed")
- `attempts` (integer)
- `last_error` (text, nullable)
- `created_at` (timestamp)
- `updated_at` (timestamp)

---

## Setup Guide

### Environment Variables

Edit `.env` file with these values:

```bash
# Database
DATABASE_URL=postgresql://chatuser:chatpass@localhost:5432/chatdb

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT Authentication
JWT_SECRET=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=10080  # 7 days

# External Integration (optional)
INTEGRATION_URL=

# Gemini API
GEMINI_API_KEY=your-gemini-api-key-here

# Media Storage
MEDIA_DIR=./data/media
```

### VM Access Configuration

For accessing from your Android device when running in a VM:

#### 1. VM Network Settings
- Set VM to **Bridged mode** (not NAT)
- This gives VM its own IP on your network

#### 2. Firewall Rules (on VM)
```powershell
New-NetFirewallRule -DisplayName "Chat API" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

#### 3. Find VM IP
```powershell
ipconfig
# Look for "IPv4 Address" on your active adapter
```

#### 4. Test from Device
```bash
# From your Android device or another computer
curl http://<VM_IP>:8000/health
```

### Project Structure

```
personal-assistant/
├── app/
│   ├── main.py                    # FastAPI application
│   ├── core/
│   │   ├── config.py              # Settings (Pydantic)
│   │   ├── logging.py             # Structured logging
│   │   └── security.py            # JWT auth
│   ├── db/
│   │   ├── models.py              # SQLAlchemy models
│   │   └── session.py             # DB session
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   └── run.py
│   ├── api/routes/
│   │   ├── auth.py                # /v1/auth/*
│   │   ├── conversations.py       # /v1/conversations
│   │   ├── messages.py            # /v1/conversations/{id}/messages
│   │   ├── runs.py                # /v1/runs/{id}
│   │   └── media.py               # /v1/media/{id}
│   ├── services/
│   │   ├── enqueue.py             # Job enqueue
│   │   ├── agent_runner.py        # Agent execution
│   │   ├── visuals.py             # Chart generation
│   │   └── integration.py         # External API calls
│   └── worker/
│       ├── worker.py              # RQ worker
│       └── jobs.py                # Job functions
├── tests/
│   └── test_smoke.py              # End-to-end tests
├── data/media/                    # Generated images (auto-created)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## API Reference

Base URL: `http://<VM_IP>:8000` or `http://localhost:8000`

### Authentication Endpoints

#### POST `/v1/auth/register`
Register a new user.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response (201):**
```json
{
  "access_token": "eyJ0eXAi...",
  "token_type": "bearer",
  "user_id": "uuid"
}
```

#### POST `/v1/auth/login`
Login existing user.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJ0eXAi...",
  "token_type": "bearer",
  "user_id": "uuid"
}
```

### Conversation Endpoints

#### POST `/v1/conversations`
Create a new conversation.

**Headers:**
```
Authorization: Bearer <token>
```

**Request:**
```json
{
  "title": "My Chat"  // optional
}
```

**Response (201):**
```json
{
  "id": "conv-uuid",
  "user_id": "user-uuid",
  "title": "My Chat",
  "created_at": "2026-01-31T12:00:00"
}
```

### Message Endpoints

#### POST `/v1/conversations/{conversation_id}/messages`
Post a user message (triggers async agent processing).

**Headers:**
```
Authorization: Bearer <token>
```

**Request:**
```json
{
  "text": "Hello, agent!",
  "metadata": {}  // optional
}
```

**Response (202 Accepted):**
```json
{
  "message_id": "msg-uuid",
  "run_id": "run-uuid",
  "status": "queued"
}
```

**Special Keywords:**
- `"plot:"` or `"chart:"` in text → triggers visualization generation

#### GET `/v1/conversations/{conversation_id}/messages`
Poll messages in a conversation.

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
- `after_id` (UUID): Get messages after this message ID
- `since` (ISO timestamp): Get messages since this time
- `limit` (int): Max messages to return (default: 100, max: 500)

**Response (200):**
```json
[
  {
    "id": "msg-uuid",
    "conversation_id": "conv-uuid",
    "sender": "user",
    "content_json": {
      "type": "text",
      "text": "Hello!"
    },
    "created_at": "2026-01-31T12:00:00"
  },
  {
    "id": "msg-uuid-2",
    "conversation_id": "conv-uuid",
    "sender": "assistant",
    "content_json": {
      "type": "text",
      "text": "Hello! How can I help?"
    },
    "created_at": "2026-01-31T12:00:02"
  },
  {
    "id": "msg-uuid-3",
    "conversation_id": "conv-uuid",
    "sender": "assistant",
    "content_json": {
      "type": "image",
      "url": "/v1/media/media-uuid",
      "caption": "Generated visualization"
    },
    "created_at": "2026-01-31T12:00:03"
  }
]
```

### Run Status Endpoints

#### GET `/v1/runs/{run_id}`
Get agent run status.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "id": "run-uuid",
  "conversation_id": "conv-uuid",
  "trigger_message_id": "msg-uuid",
  "status": "succeeded",
  "started_at": "2026-01-31T12:00:01",
  "finished_at": "2026-01-31T12:00:03",
  "last_error": null,
  "created_at": "2026-01-31T12:00:00"
}
```

**Status values:**
- `queued`: Job is waiting in Redis queue
- `running`: Worker is currently processing
- `succeeded`: Agent completed successfully
- `failed`: Agent encountered an error (see `last_error`)

### Media Endpoints

#### GET `/v1/media/{media_id}`
Download a generated image.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
- Content-Type: `image/png`
- Binary PNG data

### Utility Endpoints

#### GET `/health`
Health check (no auth required).

**Response (200):**
```json
{
  "status": "healthy"
}
```

#### GET `/`
API info (no auth required).

**Response (200):**
```json
{
  "message": "LangGraph Chat Backend API",
  "version": "1.0.0",
  "docs": "/docs"
}
```

#### GET `/docs`
Interactive API documentation (Swagger UI).

---

## Testing

### Automated Tests

Run the smoke test suite:

```powershell
# Install pytest in the API container
docker-compose exec api pip install pytest

# Run tests
docker-compose exec api pytest tests/test_smoke.py -v
```

**Tests included:**
- Health check
- Complete message flow (register → conversation → message → poll)
- Visualization flow (plot keyword → image generation → download)

### Manual Testing via PowerShell

Save this as `test_flow.ps1`:

```powershell
$VM_IP = "localhost"  # Or your VM IP
$BASE_URL = "http://${VM_IP}:8000"

Write-Host "=== 1. Register User ===" -ForegroundColor Cyan
$response = Invoke-RestMethod -Uri "$BASE_URL/v1/auth/register" `
  -Method Post `
  -Body '{"email":"test@example.com","password":"test123"}' `
  -ContentType "application/json"
$TOKEN = $response.access_token
Write-Host "Token: $TOKEN`n"

Write-Host "=== 2. Create Conversation ===" -ForegroundColor Cyan
$conv = Invoke-RestMethod -Uri "$BASE_URL/v1/conversations" `
  -Method Post `
  -Headers @{Authorization="Bearer $TOKEN"} `
  -Body '{"title":"Test Chat"}' `
  -ContentType "application/json"
$CONV_ID = $conv.id
Write-Host "Conversation ID: $CONV_ID`n"

Write-Host "=== 3. Post Message ===" -ForegroundColor Cyan
$msg = Invoke-RestMethod -Uri "$BASE_URL/v1/conversations/$CONV_ID/messages" `
  -Method Post `
  -Headers @{Authorization="Bearer $TOKEN"} `
  -Body '{"text":"plot: create a sample chart"}' `
  -ContentType "application/json"
$RUN_ID = $msg.run_id
Write-Host "Run ID: $RUN_ID`n"

Write-Host "=== 4. Wait for Processing ===" -ForegroundColor Cyan
Start-Sleep -Seconds 5

Write-Host "=== 5. Check Run Status ===" -ForegroundColor Cyan
$run = Invoke-RestMethod -Uri "$BASE_URL/v1/runs/$RUN_ID" `
  -Headers @{Authorization="Bearer $TOKEN"}
Write-Host "Status: $($run.status)`n"

Write-Host "=== 6. Get Messages ===" -ForegroundColor Cyan
$messages = Invoke-RestMethod -Uri "$BASE_URL/v1/conversations/$CONV_ID/messages" `
  -Headers @{Authorization="Bearer $TOKEN"}
Write-Host "Total messages: $($messages.Count)"
$messages | ForEach-Object { 
  Write-Host "  - $($_.sender): $($_.content_json.type)" 
}

Write-Host "`n✅ Test Complete!" -ForegroundColor Green
```

Run it:
```powershell
.\test_flow.ps1
```

### Manual Testing via cURL

```bash
# 1. Register
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# Save the token from response

# 2. Create conversation
curl -X POST http://localhost:8000/v1/conversations \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test"}'

# Save the conversation_id

# 3. Post message
curl -X POST http://localhost:8000/v1/conversations/CONV_ID/messages \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello, agent!"}'

# Save the run_id

# 4. Check status (wait a few seconds)
curl http://localhost:8000/v1/runs/RUN_ID \
  -H "Authorization: Bearer YOUR_TOKEN"

# 5. Poll messages
curl http://localhost:8000/v1/conversations/CONV_ID/messages \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Troubleshooting

### Cannot connect from Android device

**Symptoms:** `Connection refused` or timeout from your device

**Solutions:**
1. Check VM network mode is **Bridged** (not NAT)
2. Verify firewall allows port 8000:
   ```powershell
   New-NetFirewallRule -DisplayName "Chat API" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
   ```
3. Test from VM itself:
   ```bash
   curl http://localhost:8000/health
   ```
4. Test from device:
   ```bash
   curl http://<VM_IP>:8000/health
   ```
5. Verify VM IP:
   ```powershell
   ipconfig
   ```

### Worker not processing jobs

**Symptoms:** Messages stuck in `queued` status

**Solutions:**
1. Check worker logs:
   ```powershell
   docker-compose logs worker
   ```
2. Check Redis connection:
   ```powershell
   docker-compose logs redis
   ```
3. Restart worker:
   ```powershell
   docker-compose restart worker
   ```
4. Check queue status:
   ```powershell
   docker-compose exec api python -c "from app.services.enqueue import job_queue; print(f'Jobs in queue: {job_queue.count}')"
   ```

### Database errors

**Symptoms:** `relation does not exist` or connection errors

**Solutions:**
1. Reset database completely:
   ```powershell
   docker-compose down -v
   docker-compose up --build
   ```
2. Check database logs:
   ```powershell
   docker-compose logs postgres
   ```

### Gemini API not responding

**Symptoms:** Echo responses instead of AI responses

**Solutions:**
1. Check `GEMINI_API_KEY` in `.env`
2. Verify key is valid (test at https://ai.google.dev/)
3. Check worker logs for API errors:
   ```powershell
   docker-compose logs worker | Select-String "gemini"
   ```

**Note:** System will gracefully fall back to echo if key is missing (this is intentional for MVP).

### Image generation failing

**Symptoms:** No image message after using "plot:" keyword

**Solutions:**
1. Check worker logs for matplotlib errors:
   ```powershell
   docker-compose logs worker | Select-String "chart"
   ```
2. Verify media directory exists:
   ```powershell
   docker-compose exec api ls -la /app/data/media
   ```
3. Check file permissions

### External integration failing

**Symptoms:** Integration deliveries showing "failed" status

**Solutions:**
1. Verify `INTEGRATION_URL` is set correctly in `.env`
2. Check integration delivery records:
   ```powershell
   docker-compose exec postgres psql -U chatuser -d chatdb -c "SELECT * FROM integration_deliveries ORDER BY created_at DESC LIMIT 5;"
   ```
3. Check worker logs for HTTP errors:
   ```powershell
   docker-compose logs worker | Select-String "integration"
   ```

**Note:** If `INTEGRATION_URL` is empty, integration is skipped (not an error).

### View all container logs

```powershell
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f postgres
docker-compose logs -f redis

# Last 100 lines
docker-compose logs --tail=100 api
```

---

## Development

### Running Locally (without Docker)

For development, you can run services directly:

```powershell
# Start PostgreSQL and Redis in Docker
docker-compose up postgres redis

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with local URLs:
# DATABASE_URL=postgresql://chatuser:chatpass@localhost:5432/chatdb
# REDIS_URL=redis://localhost:6379/0

# Run API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, run worker
python -m app.worker.worker
```

### Adding New Endpoints

1. Create route in `app/api/routes/your_route.py`
2. Add Pydantic schemas in `app/schemas/your_schema.py`
3. Register router in `app/main.py`

Example:
```python
# app/api/routes/your_route.py
from fastapi import APIRouter, Depends
from app.core.security import get_current_user

router = APIRouter(prefix="/v1/your_endpoint", tags=["your_tag"])

@router.get("")
async def your_endpoint(current_user = Depends(get_current_user)):
    return {"message": "Hello"}
```

```python
# app/main.py
from app.api.routes import your_route

app.include_router(your_route.router)
```

### LangGraph Integration

To replace Gemini with LangGraph:

**Current implementation:**
```python
# app/services/agent_runner.py
def _run_gemini_agent(conversation_context, user_text):
    # Gemini API call
    return response.text
```

**Replace with:**
```python
from langgraph import StateGraph

def _run_langgraph_agent(conversation_context, user_text):
    # Initialize your LangGraph
    graph = StateGraph(...)
    
    # Add nodes, edges
    graph.add_node("agent", your_agent_function)
    
    # Execute
    result = graph.invoke({
        "messages": conversation_context,
        "input": user_text
    })
    
    return result["output"]
```

**Then update the call in `execute_agent_run()`:**
```python
# Old:
response_text = _run_gemini_agent(conversation_context, user_text)

# New:
response_text = _run_langgraph_agent(conversation_context, user_text)
```

All other code (context loading, result storage, integration) remains unchanged!

### Database Migrations

Currently using `create_all()` for simplicity. To add Alembic:

```powershell
# Install alembic
pip install alembic

# Initialize
alembic init alembic

# Configure alembic.ini and env.py

# Create migration
alembic revision --autogenerate -m "Initial migration"

# Apply migration
alembic upgrade head
```

### Code Quality

```powershell
# Format code
pip install black
black app/

# Lint
pip install flake8
flake8 app/

# Type checking
pip install mypy
mypy app/
```

---

## Notes & Future Enhancements

### Current Implementation Notes

- **Auth**: Simple JWT with email/password (Firebase auth planned for later)
- **Migrations**: Using `create_all()` (Alembic can be added later)
- **Storage**: Local filesystem for images (GCS/S3 can be added later)
- **Agent**: Gemini API (designed for easy LangGraph swap)
- **VM Access**: Configured with `0.0.0.0` binding and CORS `*`

### Roadmap

**P1 (Next Priority):**
- [ ] Rate limiting per user
- [ ] Enhanced visual generation (parse user intent)
- [ ] Automated integration tests
- [ ] Health check endpoint for worker/Redis

**P2 (Later):**
- [ ] LangGraph integration
- [ ] SSE/WebSocket for real-time updates
- [ ] Outbox pattern for reliable integration
- [ ] Cloud storage (GCS/S3) for media
- [ ] Vector DB (pgvector) for semantic search
- [ ] Firebase auth
- [ ] Advanced RBAC
- [ ] Conversation sharing
- [ ] Multi-language support

---

## License

MIT

---

**Questions or Issues?**
Check the logs first: `docker-compose logs -f`
