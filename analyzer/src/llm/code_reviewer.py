from typing import Dict, List, Optional, Any
import asyncio
import structlog
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from ..config.settings import settings

logger = structlog.get_logger()


class CodeReviewer:
    """LLM-powered code reviewer using Claude or GPT"""
    
    def __init__(self, provider: str = "anthropic"):
        """
        Initialize code reviewer
        
        Args:
            provider: "anthropic" for Claude or "openai" for GPT
        """
        self.provider = provider
        self.logger = logger.bind(service="code_reviewer", provider=provider)
        
        if provider == "anthropic" and settings.ANTHROPIC_API_KEY:
            self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            self.model = "claude-sonnet-4-20250514"
        elif provider == "openai" and settings.OPENAI_API_KEY:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = "gpt-4-turbo-preview"
        else:
            raise ValueError(f"No API key configured for provider: {provider}")
    
    async def review_code(
        self,
        code: str,
        file_path: str,
        language: str,
        static_issues: List[Dict],
        metrics: Dict
    ) -> Dict[str, Any]:
        """
        Perform AI-powered code review
        
        Args:
            code: Source code to review
            file_path: Path to the file
            language: Programming language
            static_issues: Issues found by static analysis
            metrics: Code metrics
            
        Returns:
            Dictionary containing AI review feedback
        """
        try:
            prompt = self._build_review_prompt(
                code, file_path, language, static_issues, metrics
            )
            
            if self.provider == "anthropic":
                response = await self._review_with_claude(prompt)
            else:
                response = await self._review_with_gpt(prompt)
            
            return self._parse_review_response(response)
            
        except Exception as e:
            self.logger.error(f"Error reviewing code", error=str(e), file=file_path)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_refactoring_suggestions(
        self,
        code: str,
        issue: Dict,
        context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate specific refactoring suggestions for an issue
        
        Args:
            code: Original code snippet
            issue: Issue details
            context: Additional context about the codebase
            
        Returns:
            List of refactoring suggestions with before/after code
        """
        try:
            prompt = self._build_refactoring_prompt(code, issue, context)
            
            if self.provider == "anthropic":
                response = await self._review_with_claude(prompt)
            else:
                response = await self._review_with_gpt(prompt)
            
            return self._parse_refactoring_response(response)
            
        except Exception as e:
            self.logger.error(f"Error generating refactoring", error=str(e))
            return []
    
    async def analyze_architecture(
        self,
        files: List[Dict],
        dependencies: Dict,
        project_structure: Dict
    ) -> Dict[str, Any]:
        """
        Analyze overall architecture and design patterns
        
        Args:
            files: List of analyzed files with metrics
            dependencies: Dependency graph
            project_structure: Project organization info
            
        Returns:
            Architecture insights and recommendations
        """
        try:
            prompt = self._build_architecture_prompt(
                files, dependencies, project_structure
            )
            
            if self.provider == "anthropic":
                response = await self._review_with_claude(prompt, max_tokens=4000)
            else:
                response = await self._review_with_gpt(prompt)
            
            return self._parse_architecture_response(response)
            
        except Exception as e:
            self.logger.error(f"Error analyzing architecture", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    def _build_review_prompt(
        self,
        code: str,
        file_path: str,
        language: str,
        static_issues: List[Dict],
        metrics: Dict
    ) -> str:
        """Build comprehensive code review prompt"""
        
        issues_summary = "\n".join([
            f"- {issue.get('severity', 'unknown').upper()}: {issue.get('title', 'Unknown issue')} "
            f"(Line {issue.get('line', 'N/A')})"
            for issue in static_issues[:10]  # Limit to top 10
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
{code[:3000]}  # Limit code length for context window
```

Please provide:
1. Overall code quality assessment (1-10 scale)
2. Key strengths of the code
3. Critical issues that need immediate attention
4. Performance concerns or bottlenecks
5. Security vulnerabilities or risks
6. Maintainability concerns
7. Best practices violations
8. Specific actionable recommendations

Format your response as JSON with the following structure:
{{
    "quality_score": <number 1-10>,
    "strengths": [<list of strings>],
    "critical_issues": [<list of issue objects>],
    "performance_concerns": [<list of strings>],
    "security_risks": [<list of strings>],
    "maintainability_issues": [<list of strings>],
    "recommendations": [<list of recommendation objects>]
}}

Each issue/recommendation object should have: title, description, severity, line_hint (if applicable)
"""
    
    def _build_refactoring_prompt(
        self,
        code: str,
        issue: Dict,
        context: Optional[str]
    ) -> str:
        """Build refactoring suggestion prompt"""
        
        return f"""You are an expert software engineer. A code issue has been identified that needs refactoring.

Issue: {issue.get('title', 'Code Issue')}
Description: {issue.get('description', 'No description')}
Severity: {issue.get('severity', 'medium')}
Category: {issue.get('category', 'general')}

Current Code:
```
{code}
```

{f"Additional Context: {context}" if context else ""}

Please provide:
1. A clear explanation of why this is an issue
2. Step-by-step refactoring approach
3. Refactored code that fixes the issue
4. Benefits of the refactoring
5. Any trade-offs or considerations

Format your response as JSON:
{{
    "explanation": "<detailed explanation>",
    "steps": [<list of refactoring steps>],
    "refactored_code": "<complete refactored code>",
    "benefits": [<list of benefits>],
    "considerations": [<list of considerations>],
    "impact": "<high|medium|low>",
    "effort": "<high|medium|low>"
}}
"""
    
    def _build_architecture_prompt(
        self,
        files: List[Dict],
        dependencies: Dict,
        project_structure: Dict
    ) -> str:
        """Build architecture analysis prompt"""
        
        files_summary = "\n".join([
            f"- {f.get('path', 'unknown')}: {f.get('lines_of_code', 0)} LOC, "
            f"{len(f.get('functions', []))} functions, "
            f"{len(f.get('classes', []))} classes"
            for f in files[:20]  # Limit to 20 files
        ])
        
        return f"""You are a software architect. Analyze the following project structure and provide architectural insights.

Project Overview:
- Total Files: {len(files)}
- Languages: {', '.join(set(f.get('language', 'unknown') for f in files))}

Key Files:
{files_summary}

Dependency Information:
{str(dependencies)[:500]}  # Truncate for context

Please provide:
1. Overall architecture pattern assessment
2. Design patterns identified (good and bad)
3. Architectural strengths
4. Architectural concerns and anti-patterns
5. Modularity and separation of concerns analysis
6. Scalability considerations
7. Recommendations for improvement

Format as JSON:
{{
    "architecture_score": <1-10>,
    "patterns_identified": [<list of patterns>],
    "strengths": [<list of strings>],
    "concerns": [<list of concern objects>],
    "modularity_score": <1-10>,
    "scalability_assessment": "<string>",
    "recommendations": [<list of recommendations>]
}}
"""
    
    async def _review_with_claude(
        self,
        prompt: str,
        max_tokens: int = 2000
    ) -> str:
        """Send review request to Claude"""
        
        message = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        return message.content[0].text
    
    async def _review_with_gpt(
        self,
        prompt: str,
        max_tokens: int = 2000
    ) -> str:
        """Send review request to GPT"""
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert code reviewer and software architect."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    
    def _parse_review_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM review response"""
        try:
            import json
            # Try to extract JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                # Fallback: return as text
                return {
                    "raw_response": response,
                    "quality_score": 5,
                    "recommendations": [response]
                }
        except Exception as e:
            self.logger.error("Error parsing review response", error=str(e))
            return {
                "raw_response": response,
                "error": "Failed to parse response"
            }
    
    def _parse_refactoring_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse refactoring suggestions response"""
        try:
            import json
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)
                return [data]
            else:
                return [{
                    "explanation": response,
                    "refactored_code": "",
                    "benefits": [],
                    "impact": "medium",
                    "effort": "medium"
                }]
        except Exception as e:
            self.logger.error("Error parsing refactoring response", error=str(e))
            return []
    
    def _parse_architecture_response(self, response: str) -> Dict[str, Any]:
        """Parse architecture analysis response"""
        try:
            import json
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                return {
                    "raw_response": response,
                    "architecture_score": 5
                }
        except Exception as e:
            self.logger.error("Error parsing architecture response", error=str(e))
            return {
                "raw_response": response,
                "error": "Failed to parse response"
            }