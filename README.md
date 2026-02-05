# CodeSage - Code Analysis Platform

A microservices-based web application for analyzing GitHub repositories and identifying code quality issues.

## Live Demo
**Frontend:** https://codesage-frontend.vercel.app

## Features
- GitHub OAuth authentication
- Repository analysis submission
- Real-time status tracking
- Detailed issue reporting with recommendations
- Code quality scoring (0-100)
- Analysis history for authenticated users

## Tech Stack

### Frontend
- React 18
- Vite
- Tailwind CSS
- Axios
- React Router

### Backend
- Node.js
- Express
- Sequelize ORM
- PostgreSQL
- Passport.js (GitHub OAuth)
- Express Session

### Analyzer
- Python 3.12
- FastAPI
- Pydantic
- Uvicorn

## Architecture
```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   React     │────▶ │   Node.js   │────▶ │   Python    │
│  Frontend   │      │   Backend   │      │  Analyzer   │
└─────────────┘      └─────────────┘      └─────────────┘
                            │
                            ▼
                     ┌─────────────┐
                     │ PostgreSQL  │
                     └─────────────┘
```

## Local Development

### Prerequisites
- Node.js 18+
- Python 3.12+
- PostgreSQL 15+

### Setup

1. **Clone repository**
```bash
git clone https://github.com/HoneyyNagpal/codesage.git
cd codesage
```

2. **Backend setup**
```bash
cd backend
npm install
createdb codesage

# Create .env file
cat > .env << EOF
PORT=5001
NODE_ENV=development
DATABASE_URL=postgresql://username@localhost:5432/codesage
JWT_SECRET=your-secret-key
GITHUB_CLIENT_ID=your-github-oauth-id
GITHUB_CLIENT_SECRET=your-github-oauth-secret
GITHUB_CALLBACK_URL=http://localhost:5001/api/v1/auth/github/callback
FRONTEND_URL=http://localhost:3000
ANALYZER_URL=http://localhost:8000
SESSION_SECRET=your-session-secret
EOF

npm run dev
```

3. **Analyzer setup**
```bash
cd analyzer
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

uvicorn src.api.app:app --reload --port 8000
```

4. **Frontend setup**
```bash
cd frontend
npm install

# Create .env file
echo "VITE_API_URL=http://localhost:5001" > .env

npm run dev
```

5. **Access application**
- Frontend: http://localhost:3000
- Backend: http://localhost:5001
- Analyzer API docs: http://localhost:8000/docs

## GitHub OAuth Setup

1. Go to https://github.com/settings/developers
2. Create new OAuth App
3. Set Homepage URL: `http://localhost:3000`
4. Set Callback URL: `http://localhost:5001/api/v1/auth/github/callback`
5. Copy Client ID and Secret to backend `.env`

## Deployment

### Frontend (Vercel)
```bash
cd frontend
vercel
```

### Backend & Analyzer (Render)
1. Connect GitHub repository
2. Create Web Service for backend (Node environment)
3. Create Web Service for analyzer (Python environment)
4. Create PostgreSQL database
5. Configure environment variables
6. Deploy

## Database Schema

### Users Table
- id (UUID, primary key)
- githubId (unique)
- username
- email
- avatarUrl
- accessToken
- timestamps

### Analyses Table
- id (UUID, primary key)
- userId (foreign key)
- repoUrl
- status (pending/processing/completed/failed)
- language
- score (0-100)
- issues (JSONB array)
- recommendations (JSONB array)
- timestamps

## API Endpoints

### Authentication
- `GET /api/v1/auth/github` - Initiate OAuth
- `GET /api/v1/auth/github/callback` - OAuth callback
- `GET /api/v1/auth/user` - Get current user
- `POST /api/v1/auth/logout` - Logout

### Analysis
- `POST /api/v1/analysis` - Submit analysis
- `GET /api/v1/analysis` - List all analyses
- `GET /api/v1/analysis/:id` - Get specific analysis

### Analyzer
- `POST /api/v1/analyze` - Start analysis
- `GET /api/v1/analyze/:id` - Get results

## Contributing
Pull requests welcome. For major changes, open an issue first.

## License
MIT

## Author
Honey Nagpal
- LinkedIn: [www.linkedin.com/in/honey-nagpal]