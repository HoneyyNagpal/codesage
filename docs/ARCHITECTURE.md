# CodeSage Implementation Guide

This guide will help you understand the architecture and implement key features of CodeSage.

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [Data Flow](#data-flow)
4. [Key Features Implementation](#key-features-implementation)
5. [Best Practices](#best-practices)

---

## Architecture Overview

CodeSage follows a microservices architecture with three main components:

```
┌─────────────────────────────────────────────────────────────┐
│                        Client (Browser)                      │
│                      React + WebSocket                       │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ HTTP/WS
                 │
┌────────────────▼────────────────────────────────────────────┐
│                      Backend (Node.js)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Express    │  │  Socket.IO   │  │  Bull Queue  │     │
│  │     API      │  │  WebSocket   │  │    Redis     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ HTTP + Queue Jobs
                 │
┌────────────────▼────────────────────────────────────────────┐
│                     Analyzer (Python)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   FastAPI    │  │  AST Parser  │  │  LLM Client  │     │
│  │     API      │  │   tree-sitter│  │  Claude/GPT  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│  ┌──────────────┐  ┌──────────────┐                       │
│  │    Celery    │  │   Analysis   │                       │
│  │    Worker    │  │   Engines    │                       │
│  └──────────────┘  └──────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Frontend (React)

**Location**: `/frontend/src`

**Key Technologies**:
- React 18 with Hooks
- React Query for data fetching
- Zustand for state management
- Socket.io-client for real-time updates
- Monaco Editor for code viewing
- Recharts for visualizations

**Main Components**:

```jsx
src/
├── components/
│   ├── dashboard/          # Main dashboard
│   ├── analysis/           # Analysis views
│   ├── repository/         # Repo management
│   └── common/             # Shared components
├── pages/                  # Route pages
├── services/               # API clients
├── hooks/                  # Custom hooks
└── utils/                  # Helper functions
```

**Example Custom Hook**:
```javascript
// src/hooks/useAnalysis.js
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

export const useAnalysis = (analysisId) => {
  return useQuery({
    queryKey: ['analysis', analysisId],
    queryFn: () => api.get(`/api/analysis/${analysisId}`),
    refetchInterval: (data) => {
      // Poll while processing
      if (data?.status === 'processing') return 5000;
      return false;
    }
  });
};
```

### 2. Backend (Node.js)

**Location**: `/backend/src`

**Architecture Pattern**: MVC + Services

```javascript
// Controller handles HTTP requests
exports.startAnalysis = async (req, res, next) => {
  try {
    const analysis = await Analysis.create({...});
    await queueService.addAnalysisJob(analysis);
    res.json({ success: true, data: analysis });
  } catch (error) {
    next(error);
  }
};

// Service handles business logic
class AnalysisService {
  async processAnalysis(analysisId) {
    const analysis = await Analysis.findByPk(analysisId);
    const result = await analyzerClient.analyze(analysis);
    await this.saveResults(analysis, result);
  }
}
```

**Queue System**:
```javascript
// Using Bull for job queue
const analysisQueue = new Bull('analysis', {
  redis: redisConfig
});

analysisQueue.process(async (job) => {
  const { analysisId } = job.data;
  await analysisService.processAnalysis(analysisId);
});
```

### 3. Analyzer (Python)

**Location**: `/analyzer/src`

**Core Functionality**:

1. **AST Parsing**:
```python
from tree_sitter import Language, Parser

class JavaScriptParser:
    def __init__(self):
        self.parser = Parser()
        # Load language
        
    def parse(self, code: str) -> Dict:
        tree = self.parser.parse(bytes(code, "utf8"))
        return self.extract_metrics(tree.root_node)
```

2. **Static Analysis**:
```python
class ComplexityAnalyzer:
    def calculate_cyclomatic_complexity(self, node):
        complexity = 1  # Base
        for child in node.children:
            if child.type in ['if', 'while', 'for']:
                complexity += 1
        return complexity
```

3. **LLM Integration**:
```python
class CodeReviewer:
    async def review_code(self, code, issues):
        prompt = self._build_prompt(code, issues)
        response = await self.llm_client.complete(prompt)
        return self._parse_response(response)
```

---

## Data Flow

### Analysis Request Flow

```
1. User clicks "Analyze" in Frontend
   └─> POST /api/analysis

2. Backend creates Analysis record
   └─> Adds job to Bull queue
   └─> Returns analysisId to frontend

3. Frontend subscribes to WebSocket
   └─> socket.emit('subscribe_analysis', { analysisId })

4. Celery worker picks up job
   └─> Clones repository
   └─> Parses each file with tree-sitter
   └─> Runs static analysis
   └─> Sends code + issues to LLM
   └─> Saves results to database

5. Backend emits progress via WebSocket
   └─> 'analysis_progress' events
   └─> 'analysis_complete' when done

6. Frontend updates UI in real-time
   └─> Shows progress bar
   └─> Displays results when complete
```

### WebSocket Events

```javascript
// Frontend
const socket = io(WS_URL);

socket.on('connect', () => {
  socket.emit('subscribe_analysis', { analysisId });
});

socket.on('analysis_progress', (data) => {
  updateProgress(data.progress);
});

socket.on('analysis_complete', (data) => {
  showResults(data);
});
```

```javascript
// Backend
io.on('connection', (socket) => {
  socket.on('subscribe_analysis', ({ analysisId }) => {
    socket.join(`analysis:${analysisId}`);
  });
});

// Emit from service
io.to(`analysis:${analysisId}`).emit('analysis_progress', {
  progress: 45,
  currentFile: 'src/App.jsx'
});
```

---

## Key Features Implementation

### 1. Repository Import with GitHub API

```javascript
// Backend: githubService.js
class GitHubService {
  async importRepository(userId, repoUrl) {
    // Parse GitHub URL
    const { owner, repo } = this.parseUrl(repoUrl);
    
    // Fetch repo info from GitHub API
    const repoData = await this.githubClient.repos.get({
      owner, repo
    });
    
    // Save to database
    return Repository.create({
      userId,
      githubId: repoData.id,
      name: repoData.name,
      fullName: repoData.full_name,
      cloneUrl: repoData.clone_url,
      language: repoData.language,
      stars: repoData.stargazers_count
    });
  }
  
  async setupWebhook(repositoryId) {
    // Create GitHub webhook for automatic analysis
    const webhook = await this.githubClient.repos.createWebhook({
      owner, repo,
      config: {
        url: `${BACKEND_URL}/api/webhooks/github`,
        content_type: 'json'
      },
      events: ['push', 'pull_request']
    });
    
    return webhook;
  }
}
```

### 2. Multi-Language AST Parsing

```python
# analyzer/src/parsers/base_parser.py
class BaseParser:
    """Base class for language parsers"""
    
    def parse(self, code: str) -> Dict:
        raise NotImplementedError
    
    def extract_functions(self, tree) -> List[Function]:
        raise NotImplementedError

# analyzer/src/parsers/javascript_parser.py
class JavaScriptParser(BaseParser):
    def __init__(self):
        self.parser = Parser()
        # Load JavaScript grammar
        
    def parse(self, code: str) -> Dict:
        tree = self.parser.parse(bytes(code, "utf8"))
        
        return {
            "functions": self.extract_functions(tree),
            "classes": self.extract_classes(tree),
            "imports": self.extract_imports(tree),
            "complexity": self.calculate_complexity(tree)
        }
```

### 3. Incremental Analysis with Caching

```python
# analyzer/src/utils/cache.py
class AnalysisCache:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def get_cached_result(
        self, 
        file_path: str, 
        file_hash: str
    ) -> Optional[Dict]:
        """Get cached analysis if file unchanged"""
        cache_key = f"analysis:{file_hash}"
        cached = await self.redis.get(cache_key)
        
        if cached:
            return json.loads(cached)
        return None
    
    async def cache_result(
        self, 
        file_hash: str, 
        result: Dict,
        ttl: int = 3600
    ):
        """Cache analysis result"""
        cache_key = f"analysis:{file_hash}"
        await self.redis.setex(
            cache_key,
            ttl,
            json.dumps(result)
        )
```

### 4. LLM-Powered Code Review

```python
# analyzer/src/llm/code_reviewer.py
class CodeReviewer:
    async def review_code(
        self, 
        code: str,
        static_issues: List[Dict]
    ) -> Dict:
        # Build context-aware prompt
        prompt = f"""
        Analyze this code and the following issues:
        
        Issues found:
        {self._format_issues(static_issues)}
        
        Code:
        ```
        {code}
        ```
        
        Provide:
        1. Severity assessment
        2. Root cause analysis
        3. Refactoring suggestions
        """
        
        # Call LLM
        response = await self.llm_client.complete(
            prompt,
            max_tokens=2000,
            temperature=0.3
        )
        
        return self._parse_response(response)
```

### 5. Real-Time Progress Updates

```python
# analyzer/src/workers/analysis_worker.py
@celery_app.task(bind=True)
def analyze_repository(self, analysis_id: str):
    """Celery task for repository analysis"""
    
    # Update progress
    def update_progress(progress: int, message: str):
        self.update_state(
            state='PROGRESS',
            meta={'progress': progress, 'message': message}
        )
        # Also emit to WebSocket
        emit_websocket_event(analysis_id, {
            'type': 'progress',
            'progress': progress,
            'message': message
        })
    
    # Clone repo
    update_progress(10, 'Cloning repository...')
    repo_path = clone_repository(repo_url)
    
    # Analyze files
    files = get_source_files(repo_path)
    total_files = len(files)
    
    for i, file_path in enumerate(files):
        progress = 10 + (80 * (i / total_files))
        update_progress(progress, f'Analyzing {file_path}...')
        
        result = analyze_file(file_path)
        save_results(analysis_id, result)
    
    # Generate insights
    update_progress(95, 'Generating insights...')
    insights = generate_insights(analysis_id)
    
    update_progress(100, 'Complete!')
```

---

## Best Practices

### 1. Error Handling

```javascript
// Backend
app.use((err, req, res, next) => {
  logger.error('Error:', err);
  
  res.status(err.status || 500).json({
    success: false,
    message: err.message,
    error: process.env.NODE_ENV === 'development' ? err : {}
  });
});
```

### 2. Input Validation

```javascript
// Using Joi
const analysisSchema = Joi.object({
  repositoryId: Joi.string().uuid().required(),
  branch: Joi.string().max(100),
  commitSha: Joi.string().length(40)
});

// In controller
const { error } = analysisSchema.validate(req.body);
if (error) {
  return res.status(400).json({
    success: false,
    message: error.details[0].message
  });
}
```

### 3. Database Optimization

```javascript
// Use indexes
await sequelize.query(`
  CREATE INDEX idx_analyses_repository_status 
  ON analyses(repository_id, status)
`);

// Eager loading
const analysis = await Analysis.findByPk(id, {
  include: [
    { model: Issue, limit: 100 },
    { model: Repository, attributes: ['name'] }
  ]
});
```

### 4. Rate Limiting

```javascript
const rateLimit = require('express-rate-limit');

const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100,
  message: 'Too many requests'
});

app.use('/api/', apiLimiter);
```

### 5. Testing

```javascript
// Backend test example
describe('Analysis API', () => {
  it('should start analysis', async () => {
    const res = await request(app)
      .post('/api/analysis')
      .send({ repositoryId: testRepoId })
      .expect(201);
    
    expect(res.body.success).toBe(true);
    expect(res.body.data.analysisId).toBeDefined();
  });
});
```

```python
# Python test example
@pytest.mark.asyncio
async def test_code_parsing():
    parser = PythonParser()
    code = "def test(): pass"
    result = parser.parse(code)
    
    assert len(result['functions']) == 1
    assert result['functions'][0]['name'] == 'test'
```

---

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Query Guide](https://tanstack.com/query/latest)
- [Bull Queue Patterns](https://github.com/OptimalBits/bull)
- [tree-sitter Documentation](https://tree-sitter.github.io/tree-sitter/)

---

## Getting Help

- GitHub Issues: Report bugs and request features
- Documentation: `/docs` directory
- Examples: `/examples` directory