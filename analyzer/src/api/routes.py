from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import uuid
import os
import json
import re
import httpx

from src.parsers.python_parser import PythonParser
from src.parsers.javascript_parser import JavaScriptParser
from src.analyzers import security_analyzer
from src.metrics import quality_score

router = APIRouter()

analysis_results = {}

MAX_FILES_TO_ANALYZE = 8
MAX_FILE_BYTES = 40_000

# Extension -> language label. Anything not in here still gets a raw
# security_analyzer.scan pass, just no AST-level parsing.
LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
}


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
    source: Optional[str] = "static"

class AnalysisResult(BaseModel):
    analysis_id: str
    status: str
    repo_url: str
    score: Optional[int] = None
    issues: List[Issue] = []
    summary: str = ""
    files_analyzed: List[str] = []


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


async def _fetch_source_files(owner: str, repo: str, client: httpx.AsyncClient):
    """Fetch up to MAX_FILES_TO_ANALYZE real source files (any supported language)
    from the repo's default branch."""
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
        entries = [
            item for item in tree
            if item.get("type") == "blob"
            and os.path.splitext(item.get("path", ""))[1] in LANGUAGE_EXTENSIONS
            and item.get("size", 0) <= MAX_FILE_BYTES
            and "node_modules" not in item["path"]
            and not item["path"].startswith(("dist/", "build/", ".venv/"))
        ]
        # Prioritize non-test files, spread across languages rather than
        # grabbing 8 files of the same type
        entries.sort(key=lambda i: ("test" in i["path"].lower(), i["path"]))
        selected = entries[:MAX_FILES_TO_ANALYZE]

        for entry in selected:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{entry['path']}"
            try:
                file_resp = await client.get(raw_url)
                if file_resp.status_code == 200:
                    ext = os.path.splitext(entry["path"])[1]
                    files.append({
                        "path": entry["path"],
                        "content": file_resp.text,
                        "language": LANGUAGE_EXTENSIONS[ext],
                    })
            except httpx.HTTPError as e:
                print(f"GitHub raw fetch error for {entry['path']}: {e}")

        if files:
            break  # found the right branch

    return files


def _run_static_analysis(files):
    """Run real parser + security analysis on fetched files. Returns
    (issues, metrics_summaries, files_actually_parsed)."""
    py_parser = PythonParser()
    js_parser = JavaScriptParser()

    all_issues = []
    metrics_summaries = []
    parsed_files = []

    for f in files:
        path, content, lang = f["path"], f["content"], f["language"]

        # AST-level parsing where we have a real parser for the language
        parse_result = None
        if lang == "python":
            try:
                parse_result = py_parser.parse(content, path)
            except Exception as e:
                print(f"Python parse error for {path}: {e}")
        elif lang in ("javascript", "typescript"):
            try:
                parse_result = js_parser.parse(content, path)
            except Exception as e:
                print(f"JS parse error for {path}: {e}")

        if parse_result and not parse_result.get("error"):
            parsed_files.append(path)
            for issue in parse_result.get("issues", []):
                all_issues.append({
                    "type": issue.get("category", "quality"),
                    "severity": issue.get("severity", "low"),
                    "file": path,
                    "line": issue.get("line"),
                    "message": issue.get("title", "Code issue"),
                    "recommendation": issue.get("description", ""),
                    "source": "static",
                })
            m = parse_result.get("metrics", {})
            metrics_summaries.append(
                f"- {path} ({lang}): {m.get('lines_of_code', 0)} LOC, "
                f"{m.get('function_count', 0)} functions, "
                f"max complexity {m.get('max_function_complexity', 0)}"
            )
        elif parse_result and parse_result.get("error"):
            # e.g. TypeScript-specific syntax esprima can't handle - still
            # worth running the security scan below, just no AST metrics
            metrics_summaries.append(f"- {path} ({lang}): AST parse unavailable ({parse_result['error'][:80]})")

        # Security pattern scan runs on raw text regardless of AST support,
        # so TS-only syntax files still get real security coverage
        for issue in security_analyzer.scan(path, content):
            all_issues.append({
                "type": issue["category"],
                "severity": issue["severity"],
                "file": path,
                "line": issue["line"],
                "message": issue["title"],
                "recommendation": issue["description"],
                "source": "static",
            })

    return all_issues, metrics_summaries, parsed_files


def _build_code_context(files, limit_chars=6000):
    """Build a trimmed code excerpt block to feed to the LLM for supplementary review."""
    blocks = []
    budget = limit_chars
    for f in files:
        if budget <= 0:
            break
        snippet = f["content"][:budget]
        blocks.append(f"### {f['path']} ({f['language']})\n```\n{snippet}\n```")
        budget -= len(snippet)
    return "\n\n".join(blocks)


def _get_llm_supplementary_issues(repo_url: str, code_context: str, metrics_summaries: list):
    """LLM pass is explicitly supplementary - it runs after real static analysis
    and is tagged source='llm' so it's never confused with a verified finding."""
    try:
        from groq import Groq
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        if code_context:
            user_prompt = (
                f"Review this real code from the GitHub repository {repo_url}.\n\n"
                f"Static analysis already ran and found structural/security issues "
                f"listed below as file metrics. Do NOT repeat generic style issues.\n\n"
                f"File metrics:\n{chr(10).join(metrics_summaries)}\n\n"
                f"Code:\n{code_context}\n\n"
                "Find issues a static AST/regex pass would miss - logic bugs, "
                "race conditions, incorrect error handling, unclear naming, "
                "missing edge case handling. Be conservative: only report what "
                "you can justify from the actual code shown.\n\n"
                "Respond with JSON only: "
                "{\"issues\": [{\"type\": \"logic\", \"severity\": \"medium\", \"file\": \"filename\", "
                "\"line\": 10, \"message\": \"description\", \"recommendation\": \"how to fix\"}]}"
            )
        else:
            return [], " (limited scan: no readable source files found, no supplementary AI review performed)"

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
        issues = result.get("issues", [])
        for issue in issues:
            issue["source"] = "llm"
        return issues, ""

    except Exception as e:
        print(f"Groq error: {e}")
        return [], ""


async def perform_analysis(analysis_id: str, repo_url: str, language: str):
    scan_note = ""
    owner, repo = _parse_owner_repo(repo_url)

    async with httpx.AsyncClient(timeout=20.0) as http_client:
        files = []
        if owner and repo:
            try:
                files = await _fetch_source_files(owner, repo, http_client)
            except RuntimeError:
                scan_note = " (limited scan: GitHub API rate limit reached)"

        if not files and not scan_note:
            scan_note = " (limited scan: no readable source files found)"

    static_issues, metrics_summaries, parsed_files = _run_static_analysis(files) if files else ([], [], [])
    code_context = _build_code_context(files) if files else ""

    llm_issues, llm_note = _get_llm_supplementary_issues(repo_url, code_context, metrics_summaries)
    if llm_note:
        scan_note = scan_note or llm_note

    all_issues = static_issues + llm_issues
    score = quality_score.compute_score(all_issues)

    analysis_results[analysis_id] = {
        "analysis_id": analysis_id,
        "status": "completed",
        "repo_url": repo_url,
        "score": score,
        "issues": all_issues,
        "files_analyzed": [f["path"] for f in files],
        "summary": (
            f"Found {len(static_issues)} static + {len(llm_issues)} AI-suggested issues "
            f"across {len(files)} files in {repo_url.split('/')[-1]}{scan_note}. Score: {score}/100"
        ),
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
        "files_analyzed": [],
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