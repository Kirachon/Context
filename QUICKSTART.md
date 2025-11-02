# 🚀 Context - Quick Start Guide

Get Context running in **under 5 minutes** with full monitoring and observability.

---

## Prerequisites

- Docker & Docker Compose installed
- 8GB RAM minimum (16GB recommended)
- 10GB free disk space

**Check prerequisites:**
```bash
docker --version
docker-compose --version
```

---

## Step 1: Clone and Configure (1 minute)

```bash
# Clone repository
git clone https://github.com/Kirachon/Context.git
cd Context

# Copy environment template
cp deployment/docker/.env.example deployment/docker/.env

# Edit .env and set secure passwords
# Required: POSTGRES_PASSWORD, API_KEY
nano deployment/docker/.env  # or use your preferred editor
```

**Minimum required changes in `.env`:**
```bash
POSTGRES_PASSWORD=your-secure-password-here
API_KEY=your-secure-api-key-here
```

---

## Step 2: Start Services (2 minutes)

```bash
cd deployment/docker
docker-compose up -d
```

**Services starting:**
- PostgreSQL (port 5432)
- Redis (port 6379)
- Qdrant (port 6333)
- Context Server (port 8000)
- Prometheus (port 9090)
- Grafana (port 3000)
- Alertmanager (port 9093)

---

## Step 3: Verify Deployment (1 minute)

```bash
# Check all containers are running
docker-compose ps

# Health check
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","version":"0.1.0",...}
```

---

## Step 4: Access UIs (1 minute)

| Service | URL | Credentials |
|---------|-----|-------------|
| **Context API** | http://localhost:8000/docs | API key (if enabled) |
| **Grafana** | http://localhost:3000 | admin / admin |
| **Prometheus** | http://localhost:9090 | None |
| **Alertmanager** | http://localhost:9093 | None |

**First login to Grafana:**
1. Go to http://localhost:3000
2. Login: `admin` / `admin`
3. Change password when prompted
4. Dashboard "Context - Overview" is auto-loaded

---

---

## Step 5: First-time Codebase Indexing (optional)

If you plan to use the MCP tools (e.g., via Claude Code), perform an initial bulk index of your project so context-aware prompts can retrieve relevant code immediately.

Examples (from your MCP client):

```
initialize_codebase()                 # index default paths from settings.indexed_paths
initialize_codebase(paths=["./src"])  # index a specific directory
```


## Verification Checklist

- [ ] All 7 containers running (`docker-compose ps`)
- [ ] Health endpoint returns `{"status":"healthy"}`
- [ ] Grafana dashboard shows metrics
- [ ] Prometheus shows target "context-server" as UP
- [ ] API docs accessible at http://localhost:8000/docs

---

## Quick Troubleshooting

### Container won't start
```bash
# View logs
docker-compose logs context-server

# Restart specific service
docker-compose restart context-server
```

### Database connection failed
```bash
# Check PostgreSQL is ready
docker-compose logs postgres | grep "ready to accept"

# Reinitialize if needed
docker-compose exec context-server python -m alembic upgrade head
```

### Metrics not showing in Grafana
```bash
# Check Prometheus is scraping
curl http://localhost:9090/api/v1/targets

# Restart Grafana
docker-compose restart grafana
```

---

## Next Steps

- **Enable API Authentication**: Set `API_AUTH_ENABLED=true` in `.env`
- **Configure Backups**: Run `bash scripts/backup_postgres.sh` and `bash scripts/backup_qdrant.sh`
- **Set up Alerts**: Edit `deployment/docker/alertmanager.yml` for Slack/email notifications
- **Review Documentation**: See [PRODUCTION_READINESS_ASSESSMENT.md](PRODUCTION_READINESS_ASSESSMENT.md)

---

## Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose down -v
```

---

## Support

- **Documentation**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Production Readiness**: [PRODUCTION_READINESS_ASSESSMENT.md](PRODUCTION_READINESS_ASSESSMENT.md)
- **Issues**: https://github.com/Kirachon/Context/issues

---

**🎉 You're ready to use Context!**

