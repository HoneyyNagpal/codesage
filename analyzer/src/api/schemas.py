from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class AnalysisRequest(BaseModel):
    """Request to start a code analysis"""
    repository_url: str = Field(..., description="Git repository URL")
    branch: Optional[str] = Field("main", description="Branch to analyze")
    commit_sha: Optional[str] = Field(None, description="Specific commit SHA")
    

class AnalysisResponse(BaseModel):
    """Response after starting analysis"""
    analysis_id: str
    status: str
    message: str


class IssueSchema(BaseModel):
    """Code issue found during analysis"""
    file_path: str
    line_number: Optional[int] = None
    severity: str
    category: str
    title: str
    description: Optional[str] = None
    suggestion: Optional[str] = None


class MetricSchema(BaseModel):
    """Code metric"""
    metric_type: str
    value: float
    file_path: Optional[str] = None


class AnalysisResultSchema(BaseModel):
    """Complete analysis results"""
    analysis_id: str
    status: str
    quality_score: Optional[float] = None
    maintainability_index: Optional[float] = None
    complexity_score: Optional[float] = None
    issues: List[IssueSchema] = []
    metrics: List[MetricSchema] = []
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None