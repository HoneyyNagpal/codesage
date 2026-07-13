from typing import Dict, List, Optional, Any
import asyncio
import structlog
import json
from groq import AsyncGroq

from ..config.settings import settings

logger = structlog.get_logger()


class CodeReviewer:
    """LLM-powered code reviewer using Groq"""
    
    def __init__(self):
        self.logger = logger.bind(service="code_reviewer", provider="groq")
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = "llama-3.3-70b-versatile"
    
    async def review_code(self, code, file_path, language, static_issues, metrics):
        try:
            prompt = self._build_review_prompt(code, file_path, language, static_issues, metrics)
            response = await self._call_groq(prompt)
            return self._parse_review_response(response)
        except Exception as e:
            self.logger.error("Error reviewing code", error=str(e), file=file_path)
            return {"success": False, "error": str(e)}
    
    async def generate_refactoring_suggestions(self, code, issue, context=None):
        try:
            prompt = self._build_refactoring_prompt(code, issue, context)
            response = await self._call_groq(prompt)
            return self._parse_refactoring_response(response)
        except Exception as e:
            self.logger.error("Error generating refactoring", error=str(e))
            return []
    
    async def analyze_architecture(self, files, dependencies, project_structure):
        try:
            prompt = self._build_architecture_prompt(files, dependencies, project_structure)
            response = await self._call_groq(prompt, max_tokens=4000)
            return self._parse_architecture_response(response)
        except Exception as e:
            self.logger.error("Error analyzing architecture", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _call_groq(self, prompt, max_tokens=2000):
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert code reviewer. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.3
        )
        return response.choices[0].message.content
    
    def _build_review_prompt(self, code, file_path, language, static_issues, metrics):
        issues_summary = "\n".join([
            f"- {issue.get('severity', 'unknown').upper()}: {issue.get('title', 'Unknown issue')} (Line {issue.get('line', 'N/A')})"
            for issue in static_issues[:10]
        ])
        
        return f"""You are an expert code reviewer. Analyze the following {language} code and provide detailed feedback.

File: {file_path}

Code Metrics:
- Lines of Code: {metrics.get('lines_of_code', 'N/A')}
- Cyclomatic Complexity: {metrics.get('max_function_complexity', 'N/A')}
- Function Count: {metrics.get('function_count', 'N/A')}
- Class Count: {metrics.get('class_count', 'N/A')}

Static Analysis Issues Found:
{issues_summary if issues_summary else "None"}

Code:
```{language}
{code[:3000]}
```

Respond ONLY with this JSON structure, no other text:
{{
    "quality_score": <number 1-10>,
    "strengths": ["<strength1>", "<strength2>"],
    "critical_issues": [{{"title": "<title>", "description": "<desc>", "severity": "<high|medium|low>", "line_hint": <number or null>}}],
    "performance_concerns": ["<concern1>"],
    "security_risks": ["<risk1>"],
    "maintainability_issues": ["<issue1>"],
    "recommendations": [{{"title": "<title>", "description": "<desc>", "severity": "<high|medium|low>"}}]
}}"""

    def _build_refactoring_prompt(self, code, issue, context=None):
        return f"""You are an expert software engineer. Provide refactoring for this issue.

Issue: {issue.get('title', 'Code Issue')}
Description: {issue.get('description', 'No description')}
Severity: {issue.get('severity', 'medium')}

Current Code:
Respond ONLY with this JSON structure:
{{
    "explanation": "<detailed explanation>",
    "steps": ["<step1>", "<step2>"],
    "refactored_code": "<complete refactored code>",
    "benefits": ["<benefit1>"],
    "considerations": ["<consideration1>"],
    "impact": "<high|medium|low>",
    "effort": "<high|medium|low>"
}}"""

    def _build_architecture_prompt(self, files, dependencies, project_structure):
        files_summary = "\n".join([
            f"- {f.get('path', 'unknown')}: {f.get('lines_of_code', 0)} LOC, {len(f.get('functions', []))} functions"
            for f in files[:20]
        ])
        
        return f"""You are a software architect. Analyze this project structure.

Total Files: {len(files)}
Languages: {', '.join(set(f.get('language', 'unknown') for f in files))}

Key Files:
{files_summary}

Respond ONLY with this JSON structure:
{{
    "architecture_score": <1-10>,
    "patterns_identified": ["<pattern1>"],
    "strengths": ["<strength1>"],
    "concerns": [{{"title": "<title>", "description": "<desc>", "severity": "<high|medium|low>"}}],
    "modularity_score": <1-10>,
    "scalability_assessment": "<string>",
    "recommendations": ["<recommendation1>"]
}}"""

    def _parse_review_response(self, response):
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(response[start:end])
            return {"raw_response": response, "quality_score": 5}
        except Exception as e:
            return {"raw_response": response, "error": "Failed to parse response"}

    def _parse_refactoring_response(self, response):
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                return [json.loads(response[start:end])]
            return [{"explanation": response, "refactored_code": "", "benefits": []}]
        except Exception as e:
            return []

    def _parse_architecture_response(self, response):
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(response[start:end])
            return {"raw_response": response, "architecture_score": 5}
        except Exception as e:
            return {"raw_response": response, "error": "Failed to parse response"}