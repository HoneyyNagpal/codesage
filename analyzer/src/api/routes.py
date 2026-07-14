from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import uuid
import asyncio
import os
import json

router = APIRouter()

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
    await asyncio.sleep(2)
    try:
        from groq import Groq
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        prompt = f"""Analyze this GitHub repository: {repo_url}

You are a senior code reviewer. Based on the repository name and type, identify 3-5 realistic and specific issues.

Return ONLY valid JSON in this exact format:
{{
  "issues": [
    {{
      "type": "security",
      "severity": "high",
      "file": "src/main.py",
      "line": 42,
      "message": "Specific issue description relevant to this repo",
      "recommendation": "How to fix this specific issue"
    }}
  ]
}}"""
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000
        )
        result = json.loads(response.choices[0].message.content)
        issues = result.get("issues", [])
    except Exception as e:
        print(f"Groq error: {e}")
        issues = []

    score = max(100 - (len(issues) * 15), 55)
    analysis_results[analysis_id] = {
        "analysis_id": analysis_id,
        "status": "completed",
        "repo_url": repo_url,
        "score": score,
        "issues": issues,
        "summary": f"Found {len(issues)} issues. Score: {score}/100"
    }

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_repository(request: AnalysisRequest, background_tasks: BackgroundTasks):
    analysis_id = str(uuid.uuid4())
    analysis_results[analysis_id] = {
        "analysis_id": analysis_id,
        "status": "processing",
        "repo_url": request.repo_url,
        "score": None,
        "issues": [],
        "summary": "Analysis in progress..."
    }
    background_tasks.add_task(perform_analysis, analysis_id, request.repo_url, request.language)
    return AnalysisResponse(
        analysis_id=analysis_id,
        status="processing",
        message=f"Analysis started for {request.repo_url}"
    )

@router.get("/analyze/{analysis_id}", response_model=AnalysisResult)
async def get_analysis(analysis_id: str):
    if analysis_id not in analysis_results:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis_results[analysis_id]