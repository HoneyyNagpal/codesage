from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import uuid
import os
import json
import re
import httpx

from src.parsers.python_parser import PythonParser

router = APIRouter()

analysis_results = {}

MAX_FILES_TO_ANALYZE = 8
MAX_FILE_BYTES = 40_000
SEVERITY_WEIGHTS = {"high": 20, "medium": 10, "low": 4}

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
    line: Optional[int] = None
    message: str
    recommendation: str

class AnalysisResult(BaseModel):
    analysis_id: str
    status: str
    repo_url: str
    score: Optional[int] = None
    issues: List[Issue] = []
    summary: str = ""


def _parse_owner_repo(repo_url: str):
    match = re.search(r"github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", repo_url.strip())
    if not match:
        return None, None
    return match.group(1), match.group(2)


def _github_headers():
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def _fetch_python_files(owner: str, repo: str, client: httpx.AsyncClient):
    """Fetch up to MAX_FILES_TO_ANALYZE Python files with real content from the repo."""
    files = []
    for branch in ("main", "master"):
        try:
            tree_resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}",
                params={"recursive": "1"},
                headers=_github_headers(),
            )
        except httpx.HTTPError as e:
            print(f"GitHub tree fetch error ({branch}): {e}")
            continue

        if tree_resp.status_code == 403 and "rate limit" in tree_resp.text.lower():
            print("GitHub API rate limit hit while fetching tree")
            raise RuntimeError("github_rate_limited")

        if tree_resp.status_code != 200:
            continue

        tree = tree_resp.json().get("tree", [])
        py_entries = [
            item for item in tree
            if item.get("type") == "blob"
            and item.get("path", "").endswith(".py")
            and item.get("size", 0) <= MAX_FILE_BYTES
        ]
        # Prioritize likely-important files, then take the rest
        py_entries.sort(key=lambda i: ("test" in i["path"].lower(), i["path"]))
        selected = py_entries[:MAX_FILES_TO_ANALYZE]

        for entry in selected:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{entry['path']}"
            try:
                file_resp = await client.get(raw_url)
                if file_resp.status_code == 200:
                    files.append({"path": entry["path"], "content": file_resp.text})
            except httpx.HTTPError as e:
                print(f"GitHub raw fetch error for {entry['path']}: {e}")

        if files:
            break  # found the right branch, no need to try the other

    return files


def _run_static_analysis(files):
    """Run real AST-based analysis on fetched files, return aggregated issues + metrics summary."""
    parser = PythonParser()
    static_issues = []
    file_metrics_summaries = []

    for f in files:
        try:
            result = parser.parse(f["content"], f["path"])
        except Exception as e:
            print(f"Parse error for {f['path']}: {e}")
            continue

        if result.get("error"):
            continue

        for issue in result.get("issues", []):
            static_issues.append({
                "type": issue.get("category", "quality"),
                "severity": issue.get("severity", "low"),
                "file": f["path"],
                "line": issue.get("line"),
                "message": issue.get("title", "Code issue"),
                "recommendation": issue.get("description", ""),
            })

        m = result.get("metrics", {})
        file_metrics_summaries.append(
            f"- {f['path']}: {m.get('lines_of_code', 0)} LOC, "
            f"{m.get('function_count', 0)} functions, "
            f"max complexity {m.get('max_function_complexity', 0)}"
        )

    return static_issues, file_metrics_summaries


def _build_code_context(files, limit_chars=6000):
    """Build a trimmed code excerpt block to feed to the LLM for real review."""
    blocks = []
    budget = limit_chars
    for f in files:
        if budget <= 0:
            break
        snippet = f["content"][:budget]
        blocks.append(f"### {f['path']}\n```python\n{snippet}\n```")
        budget -= len(snippet)
    return "\n\n".join(blocks)


async def perform_analysis(analysis_id: str, repo_url: str, language: str):
    static_issues = []
    llm_issues = []
    scan_note = ""

    owner, repo = _parse_owner_repo(repo_url)

    async with httpx.AsyncClient(timeout=15.0) as http_client:
        files = []
        if owner and repo:
            try:
                files = await _fetch_python_files(owner, repo, http_client)
            except RuntimeError:
                scan_note = " (limited scan: GitHub API rate limit reached, review based on repo metadata only)"

        if files:
            static_issues, metrics_summaries = _run_static_analysis(files)
            code_context = _build_code_context(files)
        else:
            metrics_summaries = []
            code_context = ""
            if not scan_note:
                scan_note = " (limited scan: no readable Python files found, review based on repo metadata only)"

    try:
        from groq import Groq
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        if code_context:
            user_prompt = (
                f"Review this real code from the GitHub repository {repo_url}.\n\n"
                f"File metrics:\n{chr(10).join(metrics_summaries)}\n\n"
                f"Code:\n{code_context}\n\n"
                "Find real issues in this specific code (security, performance, logic, maintainability) "
                "that a static AST parser would miss - things like SQL injection, hardcoded secrets, "
                "unsafe deserialization, missing error handling, race conditions.\n\n"
                "Respond with JSON only: "
                "{\"issues\": [{\"type\": \"security\", \"severity\": \"high\", \"file\": \"filename.py\", "
                "\"line\": 10, \"message\": \"description\", \"recommendation\": \"how to fix\"}]}"
            )
        else:
            user_prompt = (
                f"The repository {repo_url} could not be read directly. Based on the repo name "
                f"'{repo_url.split('/')[-1]}' alone, suggest 2-3 generic best-practice checks a developer "
                "should verify manually. Mark each with \"severity\": \"low\" since this is not a real code review.\n\n"
                "Respond with JSON only: "
                "{\"issues\": [{\"type\": \"quality\", \"severity\": \"low\", \"file\": \"unknown\", "
                "\"line\": null, \"message\": \"description\", \"recommendation\": \"how to fix\"}]}"
            )

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": "You are a precise code reviewer. Only report issues you can justify from the given code. Respond with valid JSON only."},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        result = json.loads(raw)
        llm_issues = result.get("issues", [])

    except Exception as e:
        print(f"Groq error: {e}")

    all_issues = static_issues + llm_issues

    deduction = sum(SEVERITY_WEIGHTS.get(i.get("severity", "low"), 4) for i in all_issues)
    score = max(100 - deduction, 10)

    analysis_results[analysis_id] = {
        "analysis_id": analysis_id,
        "status": "completed",
        "repo_url": repo_url,
        "score": score,
        "issues": all_issues,
        "summary": f"Found {len(all_issues)} issues in {repo_url.split('/')[-1]}{scan_note}. Score: {score}/100",
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