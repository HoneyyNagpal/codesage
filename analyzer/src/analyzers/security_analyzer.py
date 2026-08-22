"""
Deterministic security pattern detection. Unlike an LLM guess, every rule here
is a concrete regex match against real source text - if it fires, the pattern
is actually present in the file at that line. False positives are possible
(e.g. a variable named 'password' holding a non-secret test fixture), but
false claims about content that isn't there are not.
"""
import re
from typing import Dict, List, Any

_PLACEHOLDER_RE = re.compile(
    r"^(changeme|change_me|your[-_].*|xxx+|<.*>|example|placeholder|test|todo|dummy|fake|sample|\*+)$",
    re.IGNORECASE,
)

# Each rule tuple: (rule_id, severity, category, title, description, regex, languages)
# languages=None means the rule applies regardless of file extension.
_RULES = [
    (
        "HARDCODED_SECRET", "high", "security",
        "Hardcoded credential or secret",
        "Move this value to an environment variable or a secret manager instead of committing it to source",
        re.compile(
            r"""(?i)\b(api[_-]?key|secret[_-]?key|access[_-]?key|private[_-]?key|
                auth[_-]?token|password|passwd|secret)\s*[:=]\s*
                ["']([A-Za-z0-9+/=_\-\.]{8,})["']""",
            re.VERBOSE,
        ),
        None,
    ),
    (
        "AWS_ACCESS_KEY", "high", "security",
        "AWS access key literal detected",
        "Rotate this key immediately if it is real, and load credentials via environment variables or an IAM role instead",
        re.compile(r"AKIA[0-9A-Z]{16}"),
        None,
    ),
    (
        "UNSAFE_EVAL", "high", "security",
        "Use of eval()/exec() on potentially untrusted input",
        "eval/exec can execute arbitrary code - validate this isn't reachable with user-controlled input, or remove it",
        re.compile(r"\b(eval|exec)\s*\("),
        {"python"},
    ),
    (
        "UNSAFE_JS_EVAL", "high", "security",
        "Use of eval() or new Function() with dynamic code",
        "Dynamic code execution is a common injection vector - avoid eval/new Function on untrusted input",
        re.compile(r"\b(eval|new\s+Function)\s*\("),
        {"javascript", "typescript"},
    ),
    (
        "INSECURE_DESERIALIZATION", "high", "security",
        "Insecure deserialization (pickle)",
        "pickle.loads on untrusted data can execute arbitrary code - use JSON or a safe serialization format instead",
        re.compile(r"\bpickle\.loads?\s*\("),
        {"python"},
    ),
    (
        "UNSAFE_YAML_LOAD", "medium", "security",
        "yaml.load without a safe Loader",
        "yaml.load() without Loader=yaml.SafeLoader can execute arbitrary Python objects - use yaml.safe_load() instead",
        re.compile(r"yaml\.load\s*\((?!.*SafeLoader)"),
        {"python"},
    ),
    (
        "SQL_INJECTION_RISK", "high", "security",
        "Possible SQL injection via string interpolation",
        "Query built with an f-string or string concatenation instead of parameterized query - use placeholders (%s, ?) with bound parameters",
        re.compile(r"\.(execute|executemany)\s*\(\s*f[\"']"),
        {"python"},
    ),
    (
        "SQL_INJECTION_RISK_CONCAT", "high", "security",
        "Possible SQL injection via string concatenation",
        "Query string built with '+' concatenation - use parameterized queries instead",
        re.compile(r"\.(execute|executemany)\s*\([^)]*\+\s*\w"),
        {"python"},
    ),
    (
        "SQL_INJECTION_RISK_JS", "high", "security",
        "Possible SQL injection via template literal",
        "Query built with a template literal containing ${...} - use a parameterized query builder instead",
        re.compile(r"\.(query|execute)\s*\(\s*`[^`]*\$\{"),
        {"javascript", "typescript"},
    ),
    (
        "COMMAND_INJECTION_SHELL_TRUE", "medium", "security",
        "subprocess call with shell=True",
        "shell=True combined with any user-influenced input allows command injection - avoid it or strictly validate input",
        re.compile(r"subprocess\.(run|call|Popen|check_output)\([^)]*shell\s*=\s*True"),
        {"python"},
    ),
    (
        "COMMAND_INJECTION_OS_SYSTEM", "medium", "security",
        "os.system() call",
        "os.system() passes strings to the shell - prefer subprocess with a list of arguments and shell=False",
        re.compile(r"\bos\.system\s*\("),
        {"python"},
    ),
    (
        "COMMAND_INJECTION_JS", "high", "security",
        "exec() with dynamic/unsanitized input",
        "Passing interpolated input to a shell exec call allows command injection - use execFile with an argument array instead",
        re.compile(r"\bexec\s*\(\s*`[^`]*\$\{"),
        {"javascript", "typescript"},
    ),
    (
        "WEAK_HASH", "low", "security",
        "Weak hash algorithm (MD5/SHA1)",
        "MD5 and SHA1 are broken for security purposes - use SHA-256+ for integrity checks, or bcrypt/argon2 for passwords",
        re.compile(r"hashlib\.(md5|sha1)\s*\(|createHash\s*\(\s*[\"'](md5|sha1)[\"']"),
        None,
    ),
]


def scan(file_path: str, content: str) -> List[Dict[str, Any]]:
    """Scan raw source text for concrete security anti-patterns. Returns a list
    of issue dicts, each tied to a real line in the file."""
    issues: List[Dict[str, Any]] = []
    lines = content.split("\n")
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    lang = {"py": "python", "js": "javascript", "jsx": "javascript",
            "ts": "typescript", "tsx": "typescript"}.get(ext)

    for rule_id, severity, category, title, description, pattern, languages in _RULES:
        if languages is not None and lang not in languages:
            continue

        for line_no, line in enumerate(lines, start=1):
            match = pattern.search(line)
            if not match:
                continue

            if rule_id == "HARDCODED_SECRET":
                value = match.group(2)
                if _PLACEHOLDER_RE.match(value) or "getenv" in line or "process.env" in line:
                    continue

            issues.append({
                "severity": severity,
                "category": category,
                "title": title,
                "description": description,
                "file": file_path,
                "line": line_no,
                "rule_id": rule_id,
                "source": "static",
            })

    return issues