#!/bin/bash

# CodeSage Setup Script
# This script automates the initial setup of CodeSage

set -e

echo "🚀 CodeSage Setup Script"
echo "========================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}❌ Please do not run as root${NC}"
   exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check Node.js
if command_exists node; then
    NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_VERSION" -ge 18 ]; then
        echo -e "${GREEN}✓${NC} Node.js $(node -v) installed"
    else
        echo -e "${RED}✗${NC} Node.js 18+ required (found $(node -v))"
        exit 1
    fi
else
    echo -e "${RED}✗${NC} Node.js not found. Please install Node.js 18+"
    exit 1
fi

# Check Python
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION installed"
else
    echo -e "${RED}✗${NC} Python3 not found. Please install Python 3.10+"
    exit 1
fi

# Check Docker (optional)
if command_exists docker; then
    echo -e "${GREEN}✓${NC} Docker $(docker --version | cut -d' ' -f3 | tr -d ',') installed"
    DOCKER_AVAILABLE=true
else
    echo -e "${YELLOW}⚠${NC} Docker not found (optional but recommended)"
    DOCKER_AVAILABLE=false
fi

# Check PostgreSQL
if command_exists psql; then
    echo -e "${GREEN}✓${NC} PostgreSQL installed"
    POSTGRES_AVAILABLE=true
else
    echo -e "${YELLOW}⚠${NC} PostgreSQL not found"
    POSTGRES_AVAILABLE=false
fi

# Check Redis
if command_exists redis-cli; then
    echo -e "${GREEN}✓${NC} Redis installed"
    REDIS_AVAILABLE=true
else
    echo -e "${YELLOW}⚠${NC} Redis not found"
    REDIS_AVAILABLE=false
fi

echo ""

# Ask user for setup method
echo "Choose setup method:"
echo "1) Docker (Recommended - all services in containers)"
echo "2) Manual (PostgreSQL, Redis, and services on host)"
echo ""
read -p "Enter choice [1-2]: " SETUP_METHOD

if [ "$SETUP_METHOD" = "1" ]; then
    if [ "$DOCKER_AVAILABLE" = false ]; then
        echo -e "${RED}❌ Docker not installed. Please install Docker first.${NC}"
        exit 1
    fi
    
    echo ""
    echo "🐳 Setting up with Docker..."
    echo ""
    
    # Copy environment files
    echo "📝 Setting up environment files..."
    cp backend/.env.example backend/.env
    cp analyzer/.env.example analyzer/.env
    cp frontend/.env.example frontend/.env
    
    echo ""
    echo "⚙️  Please configure the following environment files:"
    echo "  - backend/.env (GitHub OAuth, JWT secret)"
    echo "  - analyzer/.env (OpenAI/Anthropic API keys)"
    echo "  - frontend/.env (if needed)"
    echo ""
    read -p "Press Enter when you've configured the environment files..."
    
    # Start services
    echo ""
    echo "🚀 Starting services with Docker Compose..."
    docker-compose up -d
    
    # Wait for services to be ready
    echo "⏳ Waiting for services to be ready..."
    sleep 10
    
    # Check service status
    echo ""
    echo "📊 Service Status:"
    docker-compose ps
    
    echo ""
    echo -e "${GREEN}✅ Setup complete!${NC}"
    echo ""
    echo "Services are running at:"
    echo "  - Frontend: http://localhost:3000"
    echo "  - Backend API: http://localhost:5000"
    echo "  - Analyzer API: http://localhost:8000"
    echo ""
    echo "View logs with: docker-compose logs -f"
    echo "Stop services with: docker-compose down"
    
elif [ "$SETUP_METHOD" = "2" ]; then
    echo ""
    echo "🔧 Setting up manually..."
    echo ""
    
    # Check for required services
    if [ "$POSTGRES_AVAILABLE" = false ] || [ "$REDIS_AVAILABLE" = false ]; then
        echo -e "${RED}❌ PostgreSQL and Redis are required for manual setup${NC}"
        echo "Please install them first:"
        echo "  sudo apt install postgresql redis-server"
        exit 1
    fi
    
    # Setup PostgreSQL
    echo "📦 Setting up PostgreSQL database..."
    read -p "Enter PostgreSQL username (default: codesage): " DB_USER
    DB_USER=${DB_USER:-codesage}
    
    read -sp "Enter PostgreSQL password: " DB_PASSWORD
    echo ""
    
    sudo -u postgres psql << EOF
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
CREATE DATABASE codesage OWNER $DB_USER;
GRANT ALL PRIVILEGES ON DATABASE codesage TO $DB_USER;
EOF
    
    echo -e "${GREEN}✓${NC} Database created"
    
    # Initialize schema
    echo "Initializing database schema..."
    PGPASSWORD=$DB_PASSWORD psql -U $DB_USER -d codesage -f database/schema.sql
    echo -e "${GREEN}✓${NC} Schema initialized"
    
    # Setup environment files
    echo ""
    echo "📝 Setting up environment files..."
    
    cp backend/.env.example backend/.env
    cp analyzer/.env.example analyzer/.env
    cp frontend/.env.example frontend/.env
    
    # Update DATABASE_URL in env files
    sed -i "s|postgresql://.*|postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/codesage|g" backend/.env
    sed -i "s|postgresql://.*|postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/codesage|g" analyzer/.env
    
    echo -e "${GREEN}✓${NC} Environment files created"
    
    # Backend setup
    echo ""
    echo "🔨 Setting up Backend..."
    cd backend
    npm install
    cd ..
    echo -e "${GREEN}✓${NC} Backend dependencies installed"
    
    # Analyzer setup
    echo ""
    echo "🐍 Setting up Python Analyzer..."
    cd analyzer
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    deactivate
    cd ..
    echo -e "${GREEN}✓${NC} Analyzer dependencies installed"
    
    # Frontend setup
    echo ""
    echo "⚛️  Setting up Frontend..."
    cd frontend
    npm install
    cd ..
    echo -e "${GREEN}✓${NC} Frontend dependencies installed"
    
    echo ""
    echo -e "${GREEN}✅ Setup complete!${NC}"
    echo ""
    echo "⚠️  Don't forget to configure:"
    echo "  - GitHub OAuth credentials in backend/.env"
    echo "  - OpenAI/Anthropic API keys in analyzer/.env"
    echo ""
    echo "To start the services:"
    echo "  1. Backend: cd backend && npm run dev"
    echo "  2. Analyzer: cd analyzer && source venv/bin/activate && uvicorn src.api.app:app --reload"
    echo "  3. Frontend: cd frontend && npm run dev"
    echo ""
    echo "Or use PM2 for production:"
    echo "  npm install -g pm2"
    echo "  pm2 start ecosystem.config.js"
    
else
    echo -e "${RED}❌ Invalid choice${NC}"
    exit 1
fi

echo ""
echo "📚 Next steps:"
echo "  1. Configure GitHub OAuth at: https://github.com/settings/developers"
echo "  2. Get LLM API keys (OpenAI or Anthropic)"
echo "  3. Update environment files with your credentials"
echo "  4. Start using CodeSage!"
echo ""
echo "📖 Documentation: ./docs/"
echo "❓ Issues: https://github.com/yourusername/codesage/issues"