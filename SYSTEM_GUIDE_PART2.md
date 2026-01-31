## Module Deep Dive

### 1. FastAPI API Server (`app/`)

**Location**: `app/main.py`, `app/api/`

**Purpose**: HTTP server that handles incoming requests from Android app

**Current Implementation**:
```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Chat API")

# CORS middleware - allows all origins for VM access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
app.include_router(conversations.router, prefix="/v1/conversations", tags=["conversations"])
app.include_router(messages.router, prefix="/v1", tags=["messages"])
app.include_router(runs.router, prefix="/v1/runs", tags=["runs"])
app.include_router(media.router, prefix="/v1/media", tags=["media"])
```

**How It Works**:
1. Uvicorn starts the server on port 8000 (exposed as 60100)
2. Middleware processes requests (CORS, exception handling)
3. Request routed to appropriate handler based on path
4. Handler uses dependency injection for DB, authentication
5. Response returned to client

**Enhancement Opportunities**:

#### A. Add Rate Limiting
**Why**: Prevent abuse and API overload

```python
# Install: pip install slowapi
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# On endpoint
@router.post("/messages")
@limiter.limit("10/minute")  # Max 10 messages per minute
async def post_message(...):
    ...
```

#### B. Add Request ID Middleware
**Why**: Track requests across services for debugging

```python
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

app.add_middleware(RequestIDMiddleware)
```

#### C. Add API Versioning
**Why**: Support multiple API versions for backward compatibility

```python
# app/api/v2/routes.py
@router.post("/conversations/{id}/stream")  # New endpoint
async def stream_message(...):
    # Streaming implementation
    ...

# Include in main
app.include_router(v2_conversations.router, prefix="/v2/conversations")
```

---

### 2. Authentication Module (`app/api/routes/auth.py`, `app/core/security.py`)

**Purpose**: Handle user registration, login, JWT generation/validation

**Current Implementation**:
```python
# JWT creation
def create_access_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=24)
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

# Dependency for protected routes
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401)
        return user
    except JWTError:
        raise HTTPException(status_code=401)
```

**Enhancement Opportunities**:

#### A. Integrate Firebase Auth
**Why**: Production-ready authentication with social login

```python
# Install: pip install firebase-admin
import firebase_admin
from firebase_admin import auth, credentials

# Initialize
cred = credentials.Certificate("firebase-credentials.json")
firebase_admin.initialize_app(cred)

@router.post("/auth/firebase")
async def firebase_login(token: str, db: Session):
    # Verify Firebase token
    decoded_token = auth.verify_id_token(token)
    firebase_uid = decoded_token['uid']
    email = decoded_token.get('email')
    
    # Find or create user
    user = db.query(User).filter(User.external_auth_id == firebase_uid).first()
    if not user:
        user = User(
            email=email,
            external_auth_id=firebase_uid,
            password_hash=None  # No password for external auth
        )
        db.add(user)
        db.commit()
    
    # Generate your own JWT for internal use
    token = create_access_token(str(user.id))
    return {"access_token": token, "user_id": str(user.id)}
```

#### B. Add Refresh Tokens
**Why**: Better UX - users don't need to relogin every 24 hours

```python
def create_tokens(user_id: str) -> dict:
    access_token = create_access_token(user_id, expire_minutes=15)  # Short-lived
    refresh_token = create_refresh_token(user_id, expire_days=30)   # Long-lived
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/auth/refresh")
async def refresh_access_token(refresh_token: str):
    # Verify refresh token
    payload = jwt.decode(refresh_token, settings.JWT_SECRET)
    user_id = payload.get("sub")
    
    # Generate new access token
    new_access_token = create_access_token(user_id, expire_minutes=15)
    return {"access_token": new_access_token}
```

#### C. Add Password Reset Flow
**Why**: Essential for production apps

```python
@router.post("/auth/forgot-password")
async def forgot_password(email: str, db: Session):
    user = db.query(User).filter(User.email == email).first()
    if user:
        # Generate reset token (short expiry)
        reset_token = create_reset_token(str(user.id), expire_minutes=30)
        
        # Send email (integrate with SendGrid/AWS SES)
        send_reset_email(email, reset_token)
    
    # Always return success to prevent email enumeration
    return {"message": "If email exists, reset link was sent"}

@router.post("/auth/reset-password")
async def reset_password(token: str, new_password: str, db: Session):
    payload = jwt.decode(token, settings.JWT_SECRET)
    user_id = payload.get("sub")
    
    user = db.query(User).filter(User.id == user_id).first()
    user.password_hash = hash_password(new_password)
    db.commit()
    
    return {"message": "Password reset successful"}
```

---

### 3. Database Layer (`app/db/`)

**Purpose**: Persistent storage for all application data

**Current Implementation**:
```python
# SQLAlchemy models
class User(Base):
    __tablename__ = "users"
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=True)
    external_auth_id = Column(String, nullable=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")

class Message(Base):
    __tablename__ = "messages"
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID, ForeignKey("conversations.id"))
    sender = Column(String, nullable=False)  # 'user', 'assistant', 'system'
    content_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Enhancement Opportunities**:

#### A. Add Database Migrations (Alembic)
**Why**: Version control for database schema

```bash
# Install
pip install alembic

# Initialize
alembic init migrations

# Create migration
alembic revision --autogenerate -m "Add user preferences table"

# Apply migrations
alembic upgrade head
```

```python
# Example migration
def upgrade():
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id')),
        sa.Column('theme', sa.String(), default='light'),
        sa.Column('language', sa.String(), default='en'),
        sa.Column('notification_enabled', sa.Boolean(), default=True)
    )

def downgrade():
    op.drop_table('user_preferences')
```

#### B. Add Message Search with Full-Text Search
**Why**: Let users search conversation history

```python
# Add to Message model
__table_args__ = (
    Index('idx_message_content_fts',
          func.to_tsvector('english', cast(content_json['text'], String)),
          postgresql_using='gin'),
)

# Search endpoint
@router.get("/conversations/{id}/search")
async def search_messages(
    id: UUID,
    query: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    results = db.query(Message).filter(
        Message.conversation_id == id,
        func.to_tsvector('english', cast(Message.content_json['text'], String))
        .match(query)
    ).all()
    
    return results
```

#### C. Add Vector Embeddings for Semantic Search
**Why**: Find similar messages using AI embeddings

```bash
# Install pgvector extension
docker exec -it chat-postgres psql -U chatuser -d chatdb -c "CREATE EXTENSION vector;"
```

```python
from pgvector.sqlalchemy import Vector

class Message(Base):
    # ... existing fields
    embedding = Column(Vector(768))  # For embedding models like all-MiniLM-L6-v2

# When saving message
import openai

def create_embedding(text: str) -> list[float]:
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

# Save with embedding
message.embedding = create_embedding(message.content_json['text'])

# Semantic search
@router.get("/conversations/{id}/similar")
async def find_similar_messages(
    id: UUID,
    query: str,
    limit: int = 5,
    db: Session = Depends(get_db)
):
    query_embedding = create_embedding(query)
    
    results = db.query(Message).filter(
        Message.conversation_id == id
    ).order_by(
        Message.embedding.cosine_distance(query_embedding)
    ).limit(limit).all()
    
    return results
```

---

### 4. Background Worker (`app/worker/`, `app/services/`)

**Purpose**: Process agent runs asynchronously

**Current Implementation**:
```python
# app/worker/jobs.py
from rq import get_current_job

def run_agent_job(run_id: str):
    """Main worker job - executes agent run"""
    job = get_current_job()
    
    with SessionLocal() as db:
        # Execute the agent
        execute_agent_run(run_id, db)

# app/services/enqueue.py
from redis import Redis
from rq import Queue

redis_conn = Redis.from_url(settings.REDIS_URL)
job_queue = Queue('default', connection=redis_conn)

def enqueue_agent_run(run_id: str) -> str:
    job = job_queue.enqueue(
        'app.worker.jobs.run_agent_job',
        args=(run_id,),
        job_timeout='10m',
        result_ttl='1h'
    )
    return job.id
```

**Enhancement Opportunities**:

#### A. Add Multiple Workers for Parallel Processing
**Why**: Handle more requests simultaneously

```yaml
# docker-compose.yml
services:
  worker-1:
    build: .
    command: rq worker --url redis://redis:6379/0 default
    environment:
      - WORKER_ID=worker-1
    depends_on:
      - redis
      - postgres
  
  worker-2:
    build: .
    command: rq worker --url redis://redis:6379/0 default
    environment:
      - WORKER_ID=worker-2
    depends_on:
      - redis
      - postgres
  
  worker-3:
    build: .
    command: rq worker --url redis://redis:6379/0 default
    environment:
      - WORKER_ID=worker-3
    depends_on:
      - redis
      - postgres
```

#### B. Add Priority Queues
**Why**: Process important jobs first

```python
# Create queues with priorities
high_priority = Queue('high', connection=redis_conn)
default_priority = Queue('default', connection=redis_conn)
low_priority = Queue('low', connection=redis_conn)

# Enqueue based on user tier
def enqueue_agent_run(run_id: str, user: User):
    if user.is_premium:
        queue = high_priority
    else:
        queue = default_priority
    
    job = queue.enqueue(...)
    return job.id

# Worker listens to multiple queues in order
# docker run ... rq worker high default low
```

#### C. Add Job Progress Tracking
**Why**: Show "AI is thinking..." with progress bar

```python
from rq import get_current_job

def run_agent_job(run_id: str):
    job = get_current_job()
    
    with SessionLocal() as db:
        # Step 1: Load conversation
        job.meta['progress'] = 20
        job.meta['status'] = 'Loading conversation...'
        job.save_meta()
        ...
        
        # Step 2: Call AI
        job.meta['progress'] = 50
        job.meta['status'] = 'Thinking...'
        job.save_meta()
        ...
        
        # Step 3: Generate visuals
        job.meta['progress'] = 80
        job.meta['status'] = 'Creating visualization...'
        job.save_meta()
        ...
        
        # Step 4: Done
        job.meta['progress'] = 100
        job.meta['status'] = 'Complete'
        job.save_meta()

# New endpoint
@router.get("/runs/{id}/progress")
async def get_job_progress(id: UUID, db: Session):
    run = db.query(AgentRun).filter(AgentRun.id == id).first()
    # Get job from Redis
    job = job_queue.fetch_job(run.job_id)
    return {
        "progress": job.meta.get('progress', 0),
        "status": job.meta.get('status', 'queued')
    }
```

---

### 5. Agent Runner (`app/services/agent_runner.py`)

**Purpose**: Execute AI agent logic and orchestrate workflow

**Current Implementation**:
```python
def execute_agent_run(run_id: str, db: Session):
    # 1. Load conversation history
    messages = db.query(Message).filter(...).all()
    
    # 2. Build context for Gemini
    conversation_context = [
        {"role": "user", "parts": [msg.content_json['text']]}
        for msg in messages if msg.sender == 'user'
    ]
    
    # 3. Call Gemini API
    response_text = _run_gemini_agent(conversation_context, user_text)
    
    # 4. Store response
    assistant_message = Message(...)
    db.add(assistant_message)
    
    # 5. Generate visualization if requested
    if "plot:" in user_text or "chart:" in user_text:
        media_id = generate_chart(...)
    
    # 6. Call external integration
    send_to_external_system(...)
    
    # 7. Mark run as complete
    agent_run.status = 'succeeded'
    db.commit()
```

**This is where LangGraph will go!**

---

