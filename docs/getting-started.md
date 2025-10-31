# Getting Started with Context

This guide will help you set up and start using Context, the 100% offline AI coding assistant.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [First-Time Setup](#first-time-setup)
4. [Verifying Installation](#verifying-installation)
5. [Basic Usage](#basic-usage)
6. [Configuration](#configuration)
7. [Troubleshooting](#troubleshooting)
8. [Next Steps](#next-steps)

## System Requirements

### Minimum Requirements

Before installing Context, ensure your system meets these minimum requirements:

- **RAM:** 8GB minimum (16GB recommended)
- **CPU:** 4 cores minimum (8 cores recommended)
- **Disk Space:** 10GB available (50GB recommended)
- **Operating System:** Linux, macOS, or Windows with WSL2

### Required Software

Context requires the following software to be installed:

- **Docker:** Version 24.0 or later
- **Docker Compose:** Version 2.0 or later
- **Python:** Version 3.11 or later
- **Git:** Latest version (recommended)

### Installing Prerequisites

#### Docker & Docker Compose

**Linux (Ubuntu/Debian):**
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

**macOS:**
```bash
# Install Docker Desktop for Mac
# Download from: https://www.docker.com/products/docker-desktop

# Verify installation
docker --version
docker-compose --version
```

**Windows (WSL2):**
```bash
# Install Docker Desktop for Windows
# Download from: https://www.docker.com/products/docker-desktop
# Enable WSL2 backend in Docker Desktop settings

# Verify installation in WSL2 terminal
docker --version
docker-compose --version
```

#### Python 3.11+

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install python3.11 python3.11-venv python3-pip
```

**macOS:**
```bash
brew install python@3.11
```

**Windows (WSL2):**
```bash
sudo apt-get update
sudo apt-get install python3.11 python3.11-venv python3-pip
```

## Installation

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd Context
```

### Step 2: Run the Setup Script

Context includes an automated setup script that validates your system and configures the environment:

```bash
bash scripts/setup.sh
```

The setup script will:
1. ✓ Check hardware requirements (RAM, CPU, disk space)
2. ✓ Verify required dependencies (Docker, Python, Git)
3. ✓ Create `.env` file from template
4. ✓ Set up project directory structure
5. ⚙️ Optionally pull Docker images and start services

**Note:** The script will prompt you before pulling images and starting services. Answer 'y' to proceed or 'n' to skip and do it manually later.

### Step 3: Review Configuration

After setup, review and customize your `.env` file:

```bash
# Open .env in your editor
nano .env
```

Default configuration works for most development scenarios, but you may want to adjust:
- Log level (`LOG_LEVEL`)
- Service ports if they conflict with existing services
- Database credentials (for production deployments)

## First-Time Setup

### Start Services

If you skipped the automatic start during setup, start all services manually:

```bash
cd deployment/docker
docker-compose up -d
```

This will start:
- **Qdrant** - Vector database (ports 6333, 6334)
- **PostgreSQL** - Relational database (port 5432)
- **Redis** - Caching layer (port 6379)
- **Context Server** - Main application (port 8000)

### Monitor Service Startup

Watch the logs to ensure all services start successfully:

```bash
docker-compose logs -f
```

Press `Ctrl+C` to exit log viewing.

## Verifying Installation

### Check Service Health

Verify that all services are running correctly:

```bash
# Check Docker container status
docker-compose ps

# All services should show "Up" status and "(healthy)"
```

### Test Health Endpoint

The Context server provides a health check endpoint:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2025-10-31T...",
  "environment": "development",
  "services": {
    "postgres": true,
    "redis": true,
    "qdrant": true,
    "ollama": true
  }
}
```

If `status` is "degraded", check the `services` object to see which service is unavailable.

### Access API Documentation

Context provides interactive API documentation:

```bash
# Open in browser (or visit manually)
# Linux/WSL
xdg-open http://localhost:8000/docs

# macOS
open http://localhost:8000/docs

# Windows
start http://localhost:8000/docs
```

You should see the FastAPI Swagger UI with available endpoints.

## Basic Usage

### Understanding Context Architecture

Context operates as a set of microservices:

1. **MCP Server** - Handles communication with Claude Code CLI
2. **Vector Database (Qdrant)** - Stores code embeddings for semantic search
3. **PostgreSQL** - Stores metadata and audit logs
4. **Redis** - Provides caching for performance optimization
5. **Ollama** (optional) - Local LLM for prompt enhancement

### Service Endpoints

| Service | Endpoint | Purpose |
|---------|----------|---------|
| Context Server | http://localhost:8000 | Main API and health checks |
| API Docs | http://localhost:8000/docs | Interactive API documentation |
| Qdrant | http://localhost:6333 | Vector database API |
| PostgreSQL | localhost:5432 | Database connection |
| Redis | localhost:6379 | Cache connection |

### Common Commands

**View running services:**
```bash
docker-compose ps
```

**View service logs:**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f context-server
docker-compose logs -f qdrant
```

**Restart a service:**
```bash
docker-compose restart context-server
```

**Stop all services:**
```bash
docker-compose down
```

**Stop and remove all data (clean slate):**
```bash
docker-compose down -v
```

## Configuration

### Environment Variables

Context uses environment variables for configuration. Key variables in `.env`:

#### Database Configuration
```bash
DATABASE_URL=postgresql://context:password@localhost:5432/context_dev
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
```

#### Redis Configuration
```bash
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50
```

#### Qdrant Vector Database
```bash
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=context
QDRANT_VECTOR_SIZE=768
```

#### Ollama AI Processing
```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=codellama:7b
OLLAMA_TIMEOUT=300
```

#### Server Configuration
```bash
HOST=0.0.0.0
PORT=8000
RELOAD=true  # Enable auto-reload in development
WORKERS=1
```

#### Logging
```bash
LOG_LEVEL=INFO  # DEBUG, INFO, WARN, ERROR
LOG_FORMAT=json
```

### Applying Configuration Changes

After modifying `.env`, restart services:

```bash
docker-compose down
docker-compose up -d
```

## Troubleshooting

### Services Won't Start

**Problem:** Docker services fail to start or show unhealthy status.

**Solutions:**

1. **Check hardware requirements:**
   ```bash
   bash scripts/setup.sh
   ```
   The script will validate RAM, CPU, and disk space.

2. **Verify Docker is running:**
   ```bash
   docker info
   ```

3. **Check port conflicts:**
   ```bash
   # Check if ports are already in use
   # Linux/Mac
   lsof -i :8000  # Context server
   lsof -i :6333  # Qdrant
   lsof -i :5432  # PostgreSQL
   lsof -i :6379  # Redis

   # Windows (PowerShell)
   netstat -ano | findstr :8000
   ```

4. **View detailed error logs:**
   ```bash
   docker-compose logs context-server
   ```

### Health Check Returns "degraded"

**Problem:** `/health` endpoint shows degraded status.

**Solutions:**

1. **Check which service is failing:**
   ```bash
   curl http://localhost:8000/health | jq '.services'
   ```

2. **Verify individual service health:**
   ```bash
   # Qdrant
   curl http://localhost:6333/health

   # PostgreSQL
   docker-compose exec postgres pg_isready -U context

   # Redis
   docker-compose exec redis redis-cli ping
   ```

3. **Check environment variables:**
   ```bash
   docker-compose exec context-server env | grep -E "(DATABASE|REDIS|QDRANT)"
   ```

### Slow Performance

**Problem:** Services respond slowly or timeout.

**Solutions:**

1. **Check system resources:**
   ```bash
   docker stats
   ```

2. **Verify minimum requirements:**
   - At least 8GB RAM available
   - At least 4 CPU cores
   - Sufficient disk space

3. **Review logs for performance warnings:**
   ```bash
   docker-compose logs context-server | grep -i "warn\|error"
   ```

### Cannot Connect to Services

**Problem:** Cannot access http://localhost:8000 or other endpoints.

**Solutions:**

1. **Verify services are running:**
   ```bash
   docker-compose ps
   ```

2. **Check Docker networking:**
   ```bash
   docker network ls
   docker network inspect context-network
   ```

3. **Verify firewall settings:**
   - Ensure ports 8000, 6333, 5432, 6379 are not blocked
   - Check Docker Desktop firewall settings (Windows/Mac)

### Permission Errors

**Problem:** Permission denied errors when running scripts or Docker commands.

**Solutions:**

1. **Linux: Add user to docker group:**
   ```bash
   sudo usermod -aG docker $USER
   newgrp docker
   ```

2. **Make scripts executable:**
   ```bash
   chmod +x scripts/setup.sh
   ```

3. **WSL2: Ensure proper file permissions:**
   ```bash
   # Clone repo directly in WSL2 filesystem, not mounted Windows drive
   cd ~
   git clone <repository-url>
   ```

## Next Steps

Now that Context is installed and running, you can:

1. **Explore the API Documentation**
   - Visit http://localhost:8000/docs
   - Try out the interactive API endpoints

2. **Review the Architecture**
   - Read [Architecture Documentation](./architecture-Context-2025-10-31.md)
   - Understand the microservices design

3. **Read Development Guidelines**
   - Check [CLAUDE.md](../CLAUDE.md) for development workflow
   - Learn about BMad methodology

4. **Run Tests**
   ```bash
   pytest
   ```

5. **Monitor Service Health**
   - Set up monitoring dashboards
   - Configure alerting for production

## Getting Help

If you encounter issues not covered in this guide:

1. Check the [README.md](../README.md) for additional documentation
2. Review service logs for detailed error messages
3. Consult the [Architecture Documentation](./architecture-Context-2025-10-31.md)
4. Check the [PRD](./PRD.md) for requirements and user journeys

---

**Welcome to Context!** You're now ready to use the 100% offline AI coding assistant.
