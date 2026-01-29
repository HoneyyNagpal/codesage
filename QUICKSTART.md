# CodeSage - Quick Start Guide

Get up and running with CodeSage in under 5 minutes!

## 🚀 Fastest Start (Docker)

**Prerequisites**: Docker and Docker Compose installed

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/codesage.git
cd codesage

# 2. Copy environment files
cp backend/.env.example backend/.env
cp analyzer/.env.example analyzer/.env
cp frontend/.env.example frontend/.env

# 3. Add your API keys to analyzer/.env
# OPENAI_API_KEY=your-key-here
# or
# ANTHROPIC_API_KEY=your-key-here

# 4. Start all services
docker-compose up -d

# 5. Check status
docker-compose ps

# 6. View logs (optional)
docker-compose logs -f
```

**Access the application**:
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000
- API Docs: http://localhost:8000/docs

## 🛠️ Manual Setup

**Prerequisites**: Node.js 18+, Python 3.10+, PostgreSQL 15+, Redis 7+

### Step 1: Setup Database

```bash
# Start PostgreSQL and Redis
sudo systemctl start postgresql redis

# Create database
sudo -u postgres psql << EOF
CREATE USER codesage WITH PASSWORD 'your_password';
CREATE DATABASE codesage OWNER codesage;
GRANT ALL PRIVILEGES ON DATABASE codesage TO codesage;
EOF

# Initialize schema
psql -U codesage -d codesage -f database/schema.sql
```

### Step 2: Configure Environment

```bash
# Backend
cp backend/.env.example backend/.env
# Edit backend/.env with your database credentials

# Analyzer  
cp analyzer/.env.example analyzer/.env
# Add your OpenAI or Anthropic API key

# Frontend
cp frontend/.env.example frontend/.env
```

### Step 3: Install Dependencies

```bash
# Backend
cd backend
npm install

# Analyzer
cd ../analyzer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
cd ..
```

### Step 4: Start Services

**Terminal 1 - Backend:**
```bash
cd backend
npm run dev
```

**Terminal 2 - Analyzer:**
```bash
cd analyzer
source venv/bin/activate
uvicorn src.api.app:app --reload --port 8000
```

**Terminal 3 - Celery Worker:**
```bash
cd analyzer
source venv/bin/activate
celery -A src.workers.analysis_worker worker --loglevel=info
```

**Terminal 4 - Frontend:**
```bash
cd frontend
npm run dev
```

## 🔐 GitHub OAuth Setup

1. Go to: https://github.com/settings/developers
2. Click "New OAuth App"
3. Fill in:
   - **Application name**: CodeSage Local
   - **Homepage URL**: `http://localhost:3000`
   - **Authorization callback URL**: `http://localhost:5000/api/github/callback`
4. Copy Client ID and Client Secret
5. Add to `backend/.env`:
   ```
   GITHUB_CLIENT_ID=your_client_id
   GITHUB_CLIENT_SECRET=your_client_secret
   ```

## 📝 First Analysis

1. **Open**: http://localhost:3000
2. **Sign in** with GitHub (if OAuth configured) or continue as guest
3. **Add Repository**: 
   - Click "Add Repository"
   - Enter a GitHub URL (e.g., `https://github.com/facebook/react`)
   - Or use a test repository
4. **Start Analysis**:
   - Click "Analyze" button
   - Watch real-time progress
   - View results when complete

## 🧪 Test the APIs

### Backend API
```bash
# Health check
curl http://localhost:5000/health

# Get repositories (requires auth)
curl http://localhost:5000/api/repositories \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Analyzer API
```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs
```

## 🐛 Troubleshooting

### Port already in use
```bash
# Find and kill process on port 5000
lsof -ti:5000 | xargs kill -9

# Or change port in .env files
```

### Database connection failed
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
psql -U codesage -d codesage -h localhost
```

### Redis connection failed
```bash
# Check Redis status
sudo systemctl status redis

# Test connection
redis-cli ping
```

### Docker issues
```bash
# Reset everything
docker-compose down -v
docker-compose up -d --build

# View specific service logs
docker-compose logs backend
```

## 📚 Next Steps

1. **Configure Settings**: Customize analysis rules in the UI
2. **Read Documentation**: Check out `/docs` folder
3. **Set up Webhooks**: Enable automatic analysis on commits
4. **Explore API**: Use the API documentation at `/docs/API.md`

## 🆘 Getting Help

- **Documentation**: `/docs` directory
- **API Reference**: http://localhost:8000/docs
- **Issues**: https://github.com/yourusername/codesage/issues
- **Discussions**: https://github.com/yourusername/codesage/discussions

## 🎉 You're Ready!

CodeSage is now running locally. Start analyzing your code and improving quality!

**Useful Commands**:
```bash
# Docker
docker-compose up -d          # Start
docker-compose down           # Stop
docker-compose logs -f        # View logs
docker-compose restart        # Restart

# Development
npm run dev                   # Frontend/Backend dev mode
pytest                        # Run Python tests
npm test                      # Run JavaScript tests
```

Happy coding! 🚀