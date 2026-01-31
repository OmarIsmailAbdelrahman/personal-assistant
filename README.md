# LangGraph Chat Backend

Backend API for an Android-first chat application with asynchronous agent execution.

## Quick Start

```bash
# 1. Clone and navigate
cd ~/personal-assistant

# 2. Configure environment
cp .env.example .env
nano .env  # Add your GEMINI_API_KEY

# 3. Start services
docker-compose up --build
```

**Wait for these logs:**
- ✅ `database system is ready to accept connections`
- ✅ `Ready to accept connections tcp` (Redis)
- ✅ `Application startup complete` (API)
- ✅ `RQ worker listening on 'default' queue`

## API Access

- **Local**: `http://localhost:60100`
- **From Android Device**: `http://<VM_IP>:60100`

## VM Setup (for Android Access)

```bash
# 1. Find VM IP
ip addr show    # or: hostname -I

# 2. Allow firewall
sudo ufw allow 60100/tcp    # Ubuntu/Debian
# OR
sudo firewall-cmd --permanent --add-port=60100/tcp && sudo firewall-cmd --reload    # RHEL/CentOS

# 3. Test
curl http://localhost:60100/health
curl http://<VM_IP>:60100/health    # From your Android device
```

## Testing the API

### 1. Register User
```bash
curl -X POST http://<VM_IP>:60100/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```
**Save the `access_token`!**

### 2. Login
```bash
curl -X POST http://<VM_IP>:60100/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

### 3. Create Conversation
```bash
curl -X POST http://<VM_IP>:60100/v1/conversations \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"My Chat"}'
```
**Save the conversation `id`!**

### 4. Post Message (Async)
```bash
curl -X POST http://<VM_IP>:60100/v1/conversations/CONV_ID/messages \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello, AI assistant!"}'
```
Returns **202 Accepted** immediately with `run_id`

### 5. Poll Messages
```bash
curl http://<VM_IP>:60100/v1/conversations/CONV_ID/messages \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 6. Generate Visualization
```bash
curl -X POST http://<VM_IP>:60100/v1/conversations/CONV_ID/messages \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"plot: show me a sample chart"}'
```

Wait ~5 seconds, then poll messages - you'll see an image message with `/v1/media/{id}` URL.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/auth/register` | Register new user |
| POST | `/v1/auth/login` | Login user |
| POST | `/v1/conversations` | Create conversation |
| POST | `/v1/conversations/{id}/messages` | Post message (202 Accepted) |
| GET | `/v1/conversations/{id}/messages` | Poll messages |
| GET | `/v1/runs/{id}` | Check agent run status |
| GET | `/v1/media/{id}` | Download generated image |
| GET | `/health` | Health check |

## Environment Variables

```bash
# Required
DATABASE_URL=postgresql://chatuser:chatpass@postgres:5432/chatdb
REDIS_URL=redis://redis:6379/0
JWT_SECRET=your-secret-key-here

# Optional
GEMINI_API_KEY=your-gemini-api-key    # For AI responses (falls back to echo)
INTEGRATION_URL=                       # External webhook URL
```

## Troubleshooting

### Can't connect from Android device
```bash
# Check VM is in bridged mode (not NAT)
# Find IP
ip addr show

# Allow firewall
sudo ufw allow 60100/tcp

# Test
curl http://localhost:60100/health
```

### Worker not processing jobs
```bash
# Check logs
docker-compose logs worker -f

# Check queue
docker-compose exec api python -c "from app.services.enqueue import job_queue; print(job_queue.count)"
```

### Database issues
```bash
# Reset everything
docker-compose down -v
docker-compose up --build
```

## Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f worker
```

## Running Tests

```bash
docker-compose exec api pip install pytest
docker-compose exec api pytest tests/test_smoke.py -v
```

## Commands Reference

```bash
# Start
docker-compose up --build

# Stop
docker-compose down

# Restart (clean slate)
docker-compose down -v && docker-compose up --build

# View running containers
docker-compose ps

# Access database
docker-compose exec postgres psql -U chatuser -d chatdb
```

## Architecture

- **FastAPI** - Web framework
- **PostgreSQL** - Database
- **Redis + RQ** - Background job processing
- **Gemini API** - AI agent (LangGraph-ready)
- **Matplotlib** - Chart generation

See `DOCUMENTATION.md` for complete system documentation.

## Next Steps

1. ✅ Start the backend: `docker-compose up --build`
2. ✅ Test with curl commands above
3. ✅ Build your Android app using the API
4. ✅ Point app to `http://<VM_IP>:60100`

---

**Documentation**: See `DOCUMENTATION.md` for architecture, schemas, and development guide.
