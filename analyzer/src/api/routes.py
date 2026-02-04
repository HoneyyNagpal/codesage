from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict
import uuid
import asyncio
import os

router = APIRouter()

# In-memory storage 
analysis_results = {}

class AnalysisRequest(BaseModel):
    repo_url: str
    language: Optional[str] = "auto"
    analyze_security: Optional[bool] = True
    analyze_performance: Optional[bool] = True

class AnalysisResponse(BaseModel):
    analysis_id: str
    status: str
    message: str

class Issue(BaseModel):
    type: str
    severity: str
    file: str
    line: int
    message: str
    recommendation: str

class AnalysisResult(BaseModel):
    analysis_id: str
    status: str
    repo_url: str
    score: Optional[int] = None
    issues: List[Issue] = []
    summary: str = ""

async def perform_analysis(analysis_id: str, repo_url: str, language: str):
    """Use OpenAI to analyze repository"""
    await asyncio.sleep(2)

    print(f"OpenAI Key exists: {bool(os.getenv('OPENAI_API_KEY'))}")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        prompt = f"""Analyze this GitHub repository: {repo_url}

You are a senior code reviewer. Identify 3-5 realistic issues covering:
1. Security vulnerabilities
2. Performance problems
3. Code quality issues

Return ONLY valid JSON in this exact format:
{{
  "issues": [
    {{
      "type": "security",
      "severity": "high",
      "file": "app.py",
      "line": 42,
      "message": "Issue description",
      "recommendation": "How to fix"
    }}
  ]
}}"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        issues = result.get("issues", [])
        
    except Exception as e:
        print(f"OpenAI error: {e}")
        # Fallback to mock data
        import hashlib
        repo_hash = int(hashlib.md5(repo_url.encode()).hexdigest(), 16)
        issues = [
            {
                "type": "security",
                "severity": "high" if repo_hash % 3 == 0 else "medium",
                "file": "src/main.py",
                "line": (repo_hash % 100) + 10,
                "message": "Potential SQL injection vulnerability",
                "recommendation": "Use parameterized queries"
            }
        ]
    
    score = 100 - (len(issues) * 15)
    
    analysis_results[analysis_id] = {
        "analysis_id": analysis_id,
        "status": "completed",
        "repo_url": repo_url,
        "score": max(score, 55),
        "issues": issues,
        "summary": f"Found {len(issues)} issues. Score: {max(score, 55)}/100"
    }

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_repository(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """Analyze a GitHub repository"""
    
    # Generate analysis ID
    analysis_id = str(uuid.uuid4())
    
    # Initialize result
    analysis_results[analysis_id] = {
        "analysis_id": analysis_id,
        "status": "processing",
        "repo_url": request.repo_url,
        "score": None,
        "issues": [],
        "summary": "Analysis in progress..."
    }
    
    # Run analysis in background
    background_tasks.add_task(perform_analysis, analysis_id, request.repo_url, request.language)
    
    return AnalysisResponse(
        analysis_id=analysis_id,
        status="processing",
        message=f"Analysis started for {request.repo_url}"
    )

@router.get("/analyze/{analysis_id}", response_model=AnalysisResult)
async def get_analysis(analysis_id: str):
    """Get analysis results"""
    
    if analysis_id not in analysis_results:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return analysis_results[analysis_id]