# Complete System Guide - LangGraph Chat Backend

**Comprehensive Technical Documentation**

This guide provides detailed explanations of every component, workflows, and enhancement guidelines.

---

## Table of Contents

1. [System Architecture Overview](#system-architecture-overview)
2. [Complete Message Flow](#complete-message-flow)
3. [Module Deep Dive](#module-deep-dive)
4. [Database Schema Details](#database-schema-details)
5. [LangGraph Integration Guide](#langgraph-integration-guide)
6. [UI Integration Guide](#ui-integration-guide)
7. [Enhancement Guidelines](#enhancement-guidelines)

---

## System Architecture Overview

<img width="1077" height="1075" alt="image" src="https://github.com/user-attachments/assets/0bb8aba1-9a4d-4412-9d95-325b8f7c3158" />

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ANDROID APPLICATION                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ Auth Screen  │  │  Chat UI     │  │ Message List │             │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘             │
│         │                  │                  │                      │
│         └──────────────────┴──────────────────┘                      │
│                            │                                         │
│                   HTTP/REST over WiFi                                │
└────────────────────────────┼─────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      VM: BACKEND SERVICES                            │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    FASTAPI API (:60100)                        │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │ MIDDLEWARE STACK                                        │ │ │
│  │  │  • CORS (allow all origins for VM access)              │ │ │
│  │  │  • Exception handling                                   │ │ │
│  │  │  • Request logging                                      │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │ ROUTES                                                   │ │ │
│  │  │  /v1/auth/*        → JWT authentication                 │ │ │
│  │  │  /v1/conversations → Conversation CRUD                  │ │ │
│  │  │  /v1/messages      → Message handling + job enqueue    │ │ │
│  │  │  /v1/runs          → Agent run status                   │ │ │
│  │  │  /v1/media         → Image serving                      │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │ SERVICES                                                 │ │ │
│  │  │  • Security (JWT verification)                          │ │ │
│  │  │  • Enqueue (RQ job submission)                          │ │ │
│  │  │  • Logging (structured JSON)                            │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  └────────┬────────────────────────┬─────────────────────┬────────┘ │
│           │                        │                     │           │
│           ▼                        ▼                     ▼           │
│  ┌────────────────┐      ┌────────────────┐   ┌──────────────────┐ │
│  │   PostgreSQL   │      │     Redis      │   │   Local Files    │ │
│  │     :5432      │      │     :6379      │   │   ./data/media   │ │
│  │                │      │                │   │                  │ │
│  │ • users        │      │ • Job Queue    │   │ • Generated PNGs │ │
│  │ • conversations│      │ • Job Results  │   │ • Images         │ │
│  │ • messages     │      │ • Worker State │   │                  │ │
│  │ • agent_runs   │      └────────┬───────┘   └──────────────────┘ │
│  │ • media        │               │                                │
│  │ • integration_ │               │                                │
│  │   deliveries   │               ▼                                │
│  └────────────────┘      ┌────────────────────────────────┐        │
│                          │       RQ WORKER                │        │
│                          │  (Background Processor)        │        │
│                          │                                │        │
│                          │  ┌──────────────────────────┐  │        │
│                          │  │ Job: run_agent_job      │  │        │
│                          │  │                         │  │        │
│                          │  │ 1. Load conversation    │  │        │
│                          │  │ 2. Build context        │  │        │
│                          │  │ 3. Run agent ──────┐    │  │        │
│                          │  │ 4. Store response  │    │  │        │
│                          │  │ 5. Generate visual │    │  │        │
│                          │  │ 6. Call integration│    │  │        │
│                          │  └────────────────────┼────┘  │        │
│                          │                       │       │        │
│                          └───────────────────────┼───────┘        │
│                                                  │                 │
└──────────────────────────────────────────────────┼─────────────────┘
                                                   │
                    ┌──────────────────────────────┼─────────────────┐
                    │                              │                 │
                    ▼                              ▼                 ▼
          ┌──────────────────┐         ┌───────────────┐  ┌──────────────┐
          │   Gemini API     │         │  Matplotlib   │  │  External    │
          │  (AI Responses)  │         │  (Charts)     │  │  Webhook     │
          │                  │         │               │  │  (Optional)  │
          └──────────────────┘         └───────────────┘  └──────────────┘
```

### Component Purposes

| Component | Purpose | Technology | Scalability |
|-----------|---------|------------|-------------|
| **FastAPI API** | Accept HTTP requests, route to handlers | FastAPI + Uvicorn | Horizontal (load balancer) |
| **PostgreSQL** | Persistent data storage | PostgreSQL 15 | Vertical + read replicas |
| **Redis** | Job queue + caching | Redis 7 | Vertical + clustering |
| **RQ Worker** | Background job processing | Python RQ | Horizontal (add workers) |
| **Gemini API** | AI agent responses | Google Generative AI | External (rate limited) |
| **Matplotlib** | Chart generation | Python library | Runs in worker |
| **File Storage** | Media files | Local filesystem | → Cloud (GCS/S3) |

---

## Complete Message Flow

<img width="1128" height="1006" alt="image" src="https://github.com/user-attachments/assets/77411b98-ec0c-419b-98de-d92d5d542357" />

### Detailed Step-by-Step Flow

```
USER ACTION: Posts message "Hello, agent!"
     │
     ▼
┌────────────────────────────────────────────────────────────┐
│ STEP 1: Android App → API Request                         │
│                                                            │
│ POST /v1/conversations/{id}/messages                      │
│ Headers: Authorization: Bearer <JWT_TOKEN>                │
│ Body: {"text": "Hello, agent!"}                          │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│ STEP 2: API - JWT Verification                            │
│                                                            │
│ • Extract token from Authorization header                 │
│ • Decode JWT → get user_id                               │
│ • Check expiration                                         │
│ • Load user from database                                  │
│                                                            │
│ IF INVALID → 401 Unauthorized STOP                        │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│ STEP 3: API - Conversation Verification                   │
│                                                            │
│ • Load conversation by ID                                  │
│ • Verify conversation.user_id == current_user.id          │
│                                                            │
│ IF NOT OWNER → 403 Forbidden STOP                         │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│ STEP 4: API - Create User Message                         │
│                                                            │
│ INSERT INTO messages (                                     │
│   id = UUID,                                              │
│   conversation_id = <conv_id>,                            │
│   sender = 'user',                                         │
│   content_json = {                                         │
│     "type": "text",                                        │
│     "text": "Hello, agent!",                              │
│     "metadata": {}                                         │
│   },                                                       │
│   created_at = NOW()                                       │
│ )                                                          │
│                                                            │
│ → message_id generated                                     │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│ STEP 5: API - Create Agent Run                            │
│                                                            │
│ INSERT INTO agent_runs (                                   │
│   id = UUID,                                              │
│   conversation_id = <conv_id>,                            │
│   trigger_message_id = <message_id>,                      │
│   status = 'queued',                                       │
│   started_at = NULL,                                       │
│   finished_at = NULL,                                      │
│   created_at = NOW()                                       │
│ )                                                          │
│                                                            │
│ → run_id generated                                         │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│ STEP 6: API - Enqueue Background Job                      │
│                                                            │
│ job = queue.enqueue(                                       │
│   func='app.worker.jobs.run_agent_job',                   │
│   args=(run_id,),                                          │
│   job_timeout='10m',                                       │
│   result_ttl='1h',                                         │
│   failure_ttl='24h'                                        │
│ )                                                          │
│                                                            │
│ REDIS LPUSH: "rq:queue:default" → job_id                  │
│                                                            │
│ → job_id generated and stored in Redis                    │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│ STEP 7: API - Return 202 Accepted                         │
│                                                            │
│ HTTP/1.1 202 Accepted                                      │
│ {                                                          │
│   "message_id": "<uuid>",                                  │
│   "run_id": "<uuid>",                                      │
│   "status": "queued"                                       │
│ }                                                          │
│                                                            │
│ ⏱️  Total time: ~50-200ms                                  │
│ Android app receives response IMMEDIATELY                  │
└────────────┬───────────────────────────────────────────────┘
             │
             │ (API request complete - app continues)
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│ PARALLEL: Worker picks up job                             │
│                                                            │
│ Worker polls Redis queue every 100ms                       │
│ REDIS BRPOP "rq:queue:default" → gets job_id              │
│                                                            │
│ ⏱️  Typically <1 second after enqueue                      │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│ STEP 8: Worker - Update Run to 'running'                  │
│                                                            │
│ UPDATE agent_runs SET                                      │
│   status = 'running',                                      │
│   started_at = NOW()                                       │
│ WHERE id = <run_id>                                        │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│ STEP 9: Worker - Load Conversation History                │
│                                                            │
│ SELECT * FROM messages                                     │
│ WHERE conversation_id = <conv_id>                         │
│ ORDER BY created_at ASC                                    │
│                                                            │
│ Example result:                                            │
│ [                                                          │
│   {sender: 'user', text: 'What is AI?'},                  │
│   {sender: 'assistant', text: 'AI is...'},                │
│   {sender: 'user', text: 'Hello, agent!'}  ← trigger     │
│ ]                                                          │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│ STEP 10: Worker - Build Gemini Context                    │
│                                                            │
│ conversation_context = [                                   │
│   {                                                        │
│     "role": "user",                                        │
│     "parts": ["What is AI?"]                              │
│   },                                                       │
│   {                                                        │
│     "role": "model",                                       │
│     "parts": ["AI is..."]                                 │
│   }                                                        │
│ ]                                                          │
│                                                            │
│ Latest message is passed separately: "Hello, agent!"      │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│ STEP 11: Worker - Call Gemini API                         │
│                                                            │
│ model = GenerativeModel('gemini-2.5-flash')               │
│ chat = model.start_chat(history=conversation_context)     │
│ response = chat.send_message("Hello, agent!")             │
│                                                            │
│ ⏱️  Typically 1-4 seconds                                  │
│                                                            │
│ response.text = "Hello! How can I assist you today?"      │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│ STEP 12: Worker - Store Assistant Response                │
│                                                            │
│ INSERT INTO messages (                                     │
│   id = UUID,                                              │
│   conversation_id = <conv_id>,                            │
│   sender = 'assistant',                                    │
│   content_json = {                                         │
│     "type": "text",                                        │
│     "text": "Hello! How can I assist you today?"          │
│   },                                                       │
│   created_at = NOW()                                       │
│ )                                                          │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│ STEP 13: Worker - Check for Visualization Request         │
│                                                            │
│ IF user_text contains "plot:" OR "chart:":                │
│   → generate_visual = True                                 │
│ ELSE:                                                      │
│   → generate_visual = False                                │
│                                                            │
│ In this case: False (no visualization needed)             │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│ STEP 14: Worker - External Integration (Optional)         │
│                                                            │
│ IF settings.INTEGRATION_URL is set:                       │
│   POST to external webhook with payload:                   │
│   {                                                        │
│     "user_id": "<uuid>",                                   │
│     "conversation_id": "<uuid>",                           │
│     "run_id": "<uuid>",                                    │
│     "final_text": "Hello! How can...",                    │
│     "has_visualization": false                             │
│   }                                                        │
│                                                            │
│ With 3 retries: 1s, 2s, 4s backoff                        │
│ Track in integration_deliveries table                     │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│ STEP 15: Worker - Mark Run as 'succeeded'                 │
│                                                            │
│ UPDATE agent_runs SET                                      │
│   status = 'succeeded',                                    │
│   finished_at = NOW(),                                     │
│   last_error = NULL                                        │
│ WHERE id = <run_id>                                        │
│                                                            │
│ ⏱️  Total worker time: ~2-6 seconds                        │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│ STEP 16: Android App - Polling for Messages               │
│                                                            │
│ App polls every 3-5 seconds:                               │
│ GET /v1/conversations/{id}/messages?since=<timestamp>     │
│                                                            │
│ Returns:                                                   │
│ [                                                          │
│   {                                                        │
│     "id": "<uuid>",                                        │
│     "sender": "user",                                      │
│     "content_json": {                                      │
│       "type": "text",                                      │
│       "text": "Hello, agent!"                             │
│     },                                                     │
│     "created_at": "2026-01-31T14:00:00Z"                  │
│   },                                                       │
│   {                                                        │
│     "id": "<uuid>",                                        │
│     "sender": "assistant",                                 │
│     "content_json": {                                      │
│       "type": "text",                                      │
│       "text": "Hello! How can I assist you today?"       │
│     },                                                     │
│     "created_at": "2026-01-31T14:00:04Z"                  │
│   }                                                        │
│ ]                                                          │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│ STEP 17: Android App - Display Messages                   │
│                                                            │
│ RecyclerView updates with new messages                     │
│ User sees their message + AI response                      │
│                                                            │
│ ✅ Complete flow finished                                  │
└────────────────────────────────────────────────────────────┘
```

### Timing Breakdown

| Phase | Time | Blocking? |
|-------|------|-----------|
| API receives request → returns 202 | 50-200ms | Yes (user waits) |
| Job in queue → worker picks up | 0-1s | No (async) |
| Worker processes (Gemini API call) | 2-6s | No (async) |
| App polls and gets response | Next poll cycle | No (background) |
| **Total user-perceived latency** | **50-200ms** | Immediate response! |

---

