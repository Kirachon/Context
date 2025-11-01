# 📦 Production Deployment Guide - Context Application

---

## Quick Start (5 minutes)

### Option 1: Docker Compose (Recommended)

```bash
# 1. Clone and navigate
git clone https://github.com/Kirachon/Context.git
cd Context/deployment/docker

# 2. Create environment file
cat > .env << EOF
POSTGRES_DB=context_prod
POSTGRES_USER=context
POSTGRES_PASSWORD=your-secure-password
DATABASE_URL=postgresql://context:your-secure-password@postgres:5432/context_prod
REDIS_URL=redis://redis:6379/0
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION=context_vectors
OLLAMA_BASE_URL=http://ollama:11434
ENVIRONMENT=production
LOG_LEVEL=INFO
API_AUTH_ENABLED=true
API_KEY=your-secure-api-key
MCP_ENABLED=true
EOF

# 3. Start services
docker-compose up -d

# 4. Verify
curl http://localhost:8000/health
```

### Option 2: Manual Setup

```bash
# 1. Install dependencies
pip install -r requirements/base.txt

# 2. Set environment variables
export DATABASE_URL="postgresql://..."
export REDIS_URL="redis://..."
export QDRANT_HOST="localhost"

# 3. Initialize database
python -m alembic upgrade head

# 4. Start server
uvicorn src.mcp_server.server:app --host 0.0.0.0 --port 8000
```

---

## Production Checklist

### Pre-Deployment

- [ ] PostgreSQL 15+ running
- [ ] Redis 7.2+ running
- [ ] Qdrant 1.7.0+ running
- [ ] Ollama running (optional)
- [ ] SSL/TLS certificates ready
- [ ] API keys generated
- [ ] Backup strategy defined
- [ ] Monitoring configured

### Post-Deployment

- [ ] Health check passing
- [ ] Readiness probe passing
- [ ] Metrics endpoint working
- [ ] MCP tools accessible
- [ ] Database connected
- [ ] Redis connected
- [ ] Qdrant connected
- [ ] Logs being collected

---

## Configuration Reference

### Required Environment Variables

```bash
DATABASE_URL              # PostgreSQL connection
REDIS_URL                 # Redis connection
QDRANT_HOST              # Qdrant server host
QDRANT_PORT              # Qdrant server port
ENVIRONMENT              # production/staging/development
```

### Optional Environment Variables

```bash
API_AUTH_ENABLED         # Enable API key auth (default: false)
API_KEY                  # API key for authentication
QUERY_CACHE_REDIS_ENABLED # Enable Redis caching (default: false)
OLLAMA_BASE_URL          # Ollama server URL
OLLAMA_DEFAULT_MODEL     # Default LLM model
LOG_LEVEL                # Logging level (default: INFO)
MCP_ENABLED              # Enable MCP server (default: true)
```

---

## Monitoring & Health Checks

### Health Endpoints

```bash
# Application health
GET /health
Response: {"status": "healthy", "version": "0.1.0"}

# Readiness probe
GET /ready
Response: {"ready": true}

# Metrics
GET /metrics.json
Response: {"counters": {...}, "histograms": {...}}
```

### Docker Health Check

```bash
# Check container health
docker ps | grep context-server

# View logs
docker-compose logs -f context-server

# Execute command in container
docker-compose exec context-server curl http://localhost:8000/health
```

---

## Troubleshooting

### Database Connection Failed

```bash
# Check PostgreSQL
docker-compose logs postgres

# Verify connection
psql postgresql://context:password@localhost:5432/context_prod

# Reinitialize
docker-compose exec context-server python -m alembic upgrade head
```

### Redis Connection Failed

```bash
# Check Redis
docker-compose logs redis

# Test connection
redis-cli -h localhost ping
```

### Qdrant Connection Failed

```bash
# Check Qdrant
docker-compose logs qdrant

# Test connection
curl http://localhost:6333/health
```

---

## Scaling & Performance

### Single Instance (Current)
- Suitable for: Development, testing, small teams
- Capacity: ~100 concurrent users
- Deployment: Docker Compose

### Multi-Instance (Future)
- Add load balancer (nginx, HAProxy)
- Use managed PostgreSQL
- Use managed Redis
- Use managed Qdrant
- Deploy with Kubernetes

---

## Backup & Recovery

### Database Backup

```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U context context_prod > backup.sql

# Restore
psql -U context context_prod < backup.sql
```

### Vector Database Backup

```bash
# Qdrant data is in volume
docker volume inspect context-qdrant_data

# Backup volume
docker run --rm -v context-qdrant_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/qdrant-backup.tar.gz -C /data .
```

---

## Security Hardening

### Enable API Authentication

```bash
# Set in .env
API_AUTH_ENABLED=true
API_KEY=your-very-secure-key-here

# Use in requests
curl -H "x-api-key: your-very-secure-key-here" http://localhost:8000/health
```

### SSL/TLS Configuration

```bash
# Use reverse proxy (nginx)
# Configure SSL certificates
# Update docker-compose to use proxy
```

### Network Security

```bash
# Restrict to internal network only
# Use VPN for remote access
# Enable firewall rules
```

---

## Support & Documentation

- **GitHub**: https://github.com/Kirachon/Context
- **Issues**: https://github.com/Kirachon/Context/issues
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Next Steps

1. Deploy using Docker Compose
2. Configure monitoring
3. Set up backups
4. Enable API authentication
5. Monitor performance
6. Iterate based on usage

