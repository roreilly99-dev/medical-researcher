# Deployment Guide

This guide covers deploying your Medical Researcher app to free/open-source platforms.

## Architecture Requirements

| Component | Requirement |
|-----------|-------------|
| Frontend | Next.js 15 (Node.js 20+) |
| Backend | Python 3.12, FastAPI |
| Database | PostgreSQL 16 with **pgvector** extension |
| LLM | OpenAI API key OR self-hosted Ollama |

> **Note**: Free tiers typically don't support Ollama (requires GPU). Use OpenAI API for cloud deployments.

---

## Option 1: Railway (Recommended)

Railway offers the simplest full-stack deployment with PostgreSQL + pgvector support.

### Quick Deploy

1. **Create Railway Account**: https://railway.app

2. **Deploy Database First**:
   ```bash
   # In Railway dashboard:
   # New Project → Add PostgreSQL → Select "PostgreSQL with pgvector"
   ```

3. **Deploy Backend**:
   ```bash
   # Connect your GitHub repo, select the /backend directory
   # Or use Railway CLI:
   cd backend
   railway init
   railway up
   ```

4. **Deploy Frontend**:
   ```bash
   cd frontend
   railway init
   railway up
   ```

5. **Set Environment Variables** in Railway dashboard:
   - `DATABASE_URL`: Auto-populated from PostgreSQL service
   - `OPENAI_API_KEY`: Your OpenAI key
   - `LLM_PROVIDER`: `openai`
   - `NEXT_PUBLIC_API_URL`: Your backend Railway URL

### Cost
- Free tier: $5/month credits (usually sufficient for personal projects)
- Hobby: $5/month for more resources

---

## Option 2: Vercel (Frontend) + Render (Backend + DB)

Best for maximizing free resources.

### Frontend on Vercel

1. **Install Vercel CLI**:
   ```bash
   npm i -g vercel
   ```

2. **Deploy**:
   ```bash
   cd frontend
   vercel
   ```

3. **Set Environment Variable**:
   - `NEXT_PUBLIC_API_URL`: Your Render backend URL

### Backend + Database on Render

1. **One-Click Deploy**:
   - Push to GitHub
   - Go to https://render.com/deploy
   - Select your repo
   - Render will auto-detect `render.yaml` blueprint

2. **Or Manual Setup**:
   - Create PostgreSQL database (free tier)
   - Enable pgvector: Run `CREATE EXTENSION vector;` in SQL console
   - Create Web Service from `./backend` directory
   - Set environment variables

### Environment Variables for Render Backend
```
DATABASE_URL=<from Render PostgreSQL>
OPENAI_API_KEY=<your key>
LLM_PROVIDER=openai
```

---

## Option 3: Fly.io

More control, slightly more complex setup.

### Install Fly CLI
```bash
# Windows (PowerShell as Admin)
pwsh -Command "iwr https://fly.io/install.ps1 -useb | iex"
```

### Deploy Backend
```bash
cd backend
fly launch --dockerfile Dockerfile
fly postgres create --name medical-db
fly postgres attach medical-db
fly secrets set OPENAI_API_KEY=your_key LLM_PROVIDER=openai
fly deploy
```

### Deploy Frontend
```bash
cd frontend
fly launch --dockerfile Dockerfile
fly secrets set NEXT_PUBLIC_API_URL=https://your-backend.fly.dev
fly deploy
```

### Enable pgvector
```bash
fly postgres connect -a medical-db
CREATE EXTENSION vector;
```

---

## Option 4: Self-Hosted (Coolify / CapRover)

For your own VPS (DigitalOcean, Hetzner, etc.)

### Using Coolify (Open-Source Vercel Alternative)

1. **Install Coolify** on a VPS:
   ```bash
   curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
   ```

2. **Add Your Repo** in Coolify dashboard

3. **Deploy Services**:
   - Coolify auto-detects `docker-compose.yaml`
   - Configure environment variables
   - Deploy!

### Using CapRover

Similar process - CapRover reads Dockerfiles and deploys automatically.

---

## Database Setup: pgvector Extension

Most platforms require manually enabling pgvector:

```sql
-- Connect to your database and run:
CREATE EXTENSION IF NOT EXISTS vector;
```

**Platform-specific:**
- **Railway**: Auto-enabled with "PostgreSQL + pgvector" template
- **Render**: Run in SQL console from dashboard
- **Supabase**: Run in SQL Editor
- **Neon**: Enable in dashboard under "Extensions"

---

## Environment Variables Reference

### Backend
| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@host:5432/db` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `LLM_PROVIDER` | `openai` or `ollama` | `openai` |
| `OPENAI_MODEL` | Chat model | `gpt-4o-mini` |
| `OPENAI_EMBED_MODEL` | Embedding model | `text-embedding-3-small` |
| `CORS_ORIGINS` | Comma-separated allowed origins | `https://myapp.vercel.app,https://myapp.com` |

### Frontend
| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `https://api.example.com` |

---

## Cost Comparison

| Platform | Frontend | Backend | Database | Total/Month |
|----------|----------|---------|----------|-------------|
| Railway | $0 | $0 | $0 | $0-5* |
| Vercel + Render | $0 | $0 | $0 | $0 |
| Fly.io | $0 | $0 | $0 | $0** |
| Coolify (VPS) | - | - | - | ~$5 (VPS cost) |

*Railway gives $5 free credits/month  
**Fly.io free tier has resource limits

---

## Troubleshooting

### "pgvector extension not found"
Run `CREATE EXTENSION vector;` in your database.

### Backend can't connect to database
- Check `DATABASE_URL` format: `postgresql+asyncpg://...` (note the `+asyncpg`)
- Ensure database allows external connections

### CORS errors
Backend already has CORS configured. Ensure `NEXT_PUBLIC_API_URL` points to correct backend URL.

### Ollama not working
Ollama requires significant compute resources. Use `LLM_PROVIDER=openai` for cloud deployments.
