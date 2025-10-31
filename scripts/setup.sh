#!/bin/bash
set -e

# Context Development Environment Setup Script
# This script validates hardware requirements and sets up the development environment

echo "================================================"
echo "Context - Development Environment Setup"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Hardware requirements
MIN_MEMORY_GB=8
MIN_CPU_CORES=4
MIN_DISK_SPACE_GB=10

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "ℹ $1"
}

# Function to check hardware requirements
check_hardware() {
    echo "Checking hardware requirements..."
    echo ""

    local hardware_ok=true

    # Check RAM
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        total_memory_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
        total_memory_gb=$((total_memory_kb / 1024 / 1024))
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        total_memory_bytes=$(sysctl -n hw.memsize)
        total_memory_gb=$((total_memory_bytes / 1024 / 1024 / 1024))
    else
        print_warning "Cannot detect RAM on this OS. Skipping memory check."
        total_memory_gb=$MIN_MEMORY_GB
    fi

    if [ "$total_memory_gb" -ge "$MIN_MEMORY_GB" ]; then
        print_success "RAM: ${total_memory_gb}GB (minimum: ${MIN_MEMORY_GB}GB)"
    else
        print_error "RAM: ${total_memory_gb}GB - Insufficient (minimum: ${MIN_MEMORY_GB}GB)"
        hardware_ok=false
    fi

    # Check CPU cores
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        cpu_cores=$(nproc)
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        cpu_cores=$(sysctl -n hw.ncpu)
    else
        print_warning "Cannot detect CPU cores on this OS. Skipping CPU check."
        cpu_cores=$MIN_CPU_CORES
    fi

    if [ "$cpu_cores" -ge "$MIN_CPU_CORES" ]; then
        print_success "CPU Cores: ${cpu_cores} (minimum: ${MIN_CPU_CORES})"
    else
        print_error "CPU Cores: ${cpu_cores} - Insufficient (minimum: ${MIN_CPU_CORES})"
        hardware_ok=false
    fi

    # Check disk space
    available_space_gb=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
    if [ "$available_space_gb" -ge "$MIN_DISK_SPACE_GB" ]; then
        print_success "Disk Space: ${available_space_gb}GB available (minimum: ${MIN_DISK_SPACE_GB}GB)"
    else
        print_error "Disk Space: ${available_space_gb}GB - Insufficient (minimum: ${MIN_DISK_SPACE_GB}GB)"
        hardware_ok=false
    fi

    echo ""

    if [ "$hardware_ok" = false ]; then
        print_error "Hardware requirements not met. Please upgrade your system."
        exit 1
    fi

    print_success "All hardware requirements met!"
    echo ""
}

# Function to check dependencies
check_dependencies() {
    echo "Checking dependencies..."
    echo ""

    local deps_ok=true

    # Check Docker
    if command -v docker &> /dev/null; then
        docker_version=$(docker --version | awk '{print $3}' | sed 's/,//')
        print_success "Docker: ${docker_version}"
    else
        print_error "Docker not found. Please install Docker 24.0 or later."
        deps_ok=false
    fi

    # Check Docker Compose
    if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
        print_success "Docker Compose: Installed"
    else
        print_error "Docker Compose not found. Please install Docker Compose."
        deps_ok=false
    fi

    # Check Python
    if command -v python3 &> /dev/null; then
        python_version=$(python3 --version | awk '{print $2}')
        print_success "Python: ${python_version}"
    else
        print_error "Python 3 not found. Please install Python 3.11 or later."
        deps_ok=false
    fi

    # Check Git
    if command -v git &> /dev/null; then
        git_version=$(git --version | awk '{print $3}')
        print_success "Git: ${git_version}"
    else
        print_warning "Git not found. Git is recommended for version control."
    fi

    echo ""

    if [ "$deps_ok" = false ]; then
        print_error "Required dependencies missing. Please install them and try again."
        exit 1
    fi

    print_success "All dependencies installed!"
    echo ""
}

# Function to setup environment
setup_environment() {
    echo "Setting up environment..."
    echo ""

    # Create .env file from template if it doesn't exist
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            print_success "Created .env file from template"
        else
            print_warning ".env.example not found. Skipping .env creation."
        fi
    else
        print_info ".env file already exists. Skipping."
    fi

    # Create necessary directories
    mkdir -p deployment/docker scripts tests/{unit,integration,performance} src/{mcp_server,config,utils}
    print_success "Created project directory structure"

    echo ""
}

# Function to pull Docker images
pull_docker_images() {
    echo "Pulling Docker images (this may take a while)..."
    echo ""

    docker pull qdrant/qdrant:v1.7.0 && print_success "Pulled Qdrant image"
    docker pull postgres:15-alpine && print_success "Pulled PostgreSQL image"
    docker pull redis:7.2-alpine && print_success "Pulled Redis image"

    echo ""
    print_success "Docker images pulled successfully!"
    echo ""
}

# Function to start services
start_services() {
    echo "Starting services with Docker Compose..."
    echo ""

    cd deployment/docker
    docker-compose up -d

    print_success "Services started successfully!"
    echo ""
    print_info "Waiting for services to be healthy (30 seconds)..."
    sleep 30
    echo ""
}

# Function to verify services
verify_services() {
    echo "Verifying services..."
    echo ""

    # Check if Context server is running
    if curl -s http://localhost:8000/health > /dev/null; then
        print_success "Context server is healthy"
    else
        print_warning "Context server health check failed. It may still be starting..."
    fi

    echo ""
}

# Main execution
main() {
    check_hardware
    check_dependencies
    setup_environment

    # Ask user if they want to pull images and start services
    read -p "Do you want to pull Docker images and start services now? (y/n) " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pull_docker_images
        start_services
        verify_services

        print_success "Setup complete!"
        echo ""
        echo "================================================"
        echo "Next steps:"
        echo "  1. Check service status: docker-compose ps"
        echo "  2. View logs: docker-compose logs -f"
        echo "  3. Access Context server: http://localhost:8000"
        echo "  4. View API docs: http://localhost:8000/docs"
        echo "================================================"
    else
        print_success "Environment setup complete!"
        echo ""
        echo "To start services manually, run:"
        echo "  cd deployment/docker"
        echo "  docker-compose up -d"
    fi
}

# Run main function
main
