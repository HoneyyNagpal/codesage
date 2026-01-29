# CodeSage API Documentation

## Base URL
```
Development: http://localhost:5000/api
Production: https://api.codesage.io/api
```

## Authentication

Most endpoints require authentication using JWT tokens.

### Headers
```http
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

## Endpoints

### Authentication

#### POST /github/auth
Start GitHub OAuth flow
- **Response**: Redirect URL for GitHub OAuth

#### GET /github/callback
GitHub OAuth callback handler
- **Query Params**: `code`, `state`
- **Response**: JWT token

---

### Repositories

#### GET /repositories
Get user's repositories
- **Auth**: Required
- **Query Params**:
  - `page` (number, default: 1)
  - `limit` (number, default: 20)
- **Response**:
```json
{
  "success": true,
  "data": {
    "repositories": [
      {
        "id": "uuid",
        "name": "my-repo",
        "fullName": "username/my-repo",
        "url": "https://github.com/username/my-repo",
        "language": "JavaScript",
        "stars": 42,
        "lastAnalyzedAt": "2024-01-15T10:30:00Z"
      }
    ],
    "pagination": {
      "total": 50,
      "page": 1,
      "limit": 20,
      "totalPages": 3
    }
  }
}
```

#### POST /repositories
Add a new repository
- **Auth**: Required
- **Body**:
```json
{
  "url": "https://github.com/username/repo",
  "name": "My Repository"
}
```
- **Response**:
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "My Repository",
    "fullName": "username/repo"
  }
}
```

#### GET /repositories/:id
Get repository details
- **Auth**: Required
- **Response**: Repository object with latest analysis

#### DELETE /repositories/:id
Delete a repository
- **Auth**: Required
- **Response**: Success message

---

### Analysis

#### POST /analysis
Start a new code analysis
- **Auth**: Required
- **Body**:
```json
{
  "repositoryId": "uuid",
  "branch": "main",
  "commitSha": "abc123" // optional
}
```
- **Response**:
```json
{
  "success": true,
  "data": {
    "analysisId": "uuid",
    "jobId": "12345",
    "status": "pending"
  }
}
```

#### GET /analysis/:id
Get analysis results
- **Auth**: Required
- **Response**:
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "status": "completed",
    "qualityScore": 85.5,
    "maintainabilityIndex": 78.2,
    "complexityScore": 12.5,
    "securityRating": "A",
    "filesAnalyzed": 45,
    "issuesFound": 23,
    "linesOfCode": 5420,
    "createdAt": "2024-01-15T10:30:00Z",
    "completedAt": "2024-01-15T10:35:00Z",
    "Issues": [...],
    "Metrics": [...],
    "summary": {
      "issuesBySeverity": {
        "critical": 2,
        "high": 5,
        "medium": 10,
        "low": 6
      },
      "issuesByCategory": {
        "complexity": 8,
        "security": 3,
        "performance": 5,
        "maintainability": 7
      }
    }
  }
}
```

#### GET /analysis/:id/issues
Get issues for an analysis
- **Auth**: Required
- **Query Params**:
  - `severity` (string): Filter by severity
  - `category` (string): Filter by category
  - `page` (number)
  - `limit` (number)
- **Response**:
```json
{
  "success": true,
  "data": {
    "issues": [
      {
        "id": "uuid",
        "filePath": "src/components/App.jsx",
        "lineNumber": 45,
        "severity": "high",
        "category": "complexity",
        "title": "High cyclomatic complexity",
        "description": "Function has complexity of 15",
        "codeSnippet": "function complexFunc() { ... }",
        "suggestion": "Consider breaking into smaller functions",
        "llmExplanation": "This function has multiple nested conditions..."
      }
    ],
    "pagination": {...}
  }
}
```

#### GET /analysis/:id/metrics
Get metrics for an analysis
- **Auth**: Required
- **Query Params**:
  - `metricType` (string): Filter by metric type
  - `filePath` (string): Filter by file
- **Response**:
```json
{
  "success": true,
  "data": {
    "metrics": [
      {
        "id": "uuid",
        "filePath": "src/index.js",
        "metricType": "cyclomatic_complexity",
        "value": 8.5,
        "threshold": 10.0
      }
    ],
    "grouped": {
      "cyclomatic_complexity": [...],
      "cognitive_complexity": [...],
      "lines_of_code": [...]
    }
  }
}
```

#### DELETE /analysis/:id
Cancel an ongoing analysis
- **Auth**: Required
- **Response**: Success message

#### GET /analysis/stats
Get user's analysis statistics
- **Auth**: Required
- **Response**:
```json
{
  "success": true,
  "data": {
    "totalAnalyses": 50,
    "activeRepositories": 12,
    "totalIssues": 245,
    "averageQualityScore": 82.5,
    "recentTrend": "improving"
  }
}
```

---

### Webhooks

#### POST /webhooks/github
GitHub webhook handler
- **Headers**: `X-GitHub-Event`, `X-Hub-Signature-256`
- **Body**: GitHub webhook payload
- **Response**: Acknowledgment

---

## WebSocket Events

Connect to: `ws://localhost:5000`

### Client → Server

#### `subscribe_analysis`
Subscribe to analysis updates
```json
{
  "analysisId": "uuid"
}
```

### Server → Client

#### `analysis_progress`
Analysis progress update
```json
{
  "analysisId": "uuid",
  "status": "processing",
  "progress": 45,
  "currentFile": "src/components/App.jsx",
  "filesProcessed": 20,
  "totalFiles": 45
}
```

#### `analysis_complete`
Analysis completed
```json
{
  "analysisId": "uuid",
  "status": "completed",
  "qualityScore": 85.5,
  "issuesFound": 23
}
```

#### `analysis_error`
Analysis failed
```json
{
  "analysisId": "uuid",
  "status": "failed",
  "error": "Error message"
}
```

---

## Error Responses

All errors follow this format:
```json
{
  "success": false,
  "message": "Error description",
  "error": "Detailed error (development only)"
}
```

### Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `409` - Conflict
- `422` - Validation Error
- `429` - Too Many Requests
- `500` - Internal Server Error

---

## Rate Limiting

- **Limit**: 100 requests per 15 minutes per IP
- **Headers**:
  - `X-RateLimit-Limit`: Total limit
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Reset timestamp

---

## Pagination

All list endpoints support pagination:
- `page` (default: 1)
- `limit` (default: 20, max: 100)

Response includes:
```json
{
  "pagination": {
    "total": 150,
    "page": 2,
    "limit": 20,
    "totalPages": 8
  }
}
```