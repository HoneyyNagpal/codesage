import json
import os
import subprocess
from typing import Dict, List, Any
import structlog

logger = structlog.get_logger()

# js_ast/parse.js lives at analyzer/js_ast/parse.js, this file lives at
# analyzer/src/parsers/javascript_parser.py
_PARSE_SCRIPT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "js_ast", "parse.js")
)

DECISION_TYPES = {
    "IfStatement", "ForStatement", "ForInStatement", "ForOfStatement",
    "WhileStatement", "DoWhileStatement", "CatchClause", "ConditionalExpression",
}
# Babel represents class/object methods as ClassMethod/ObjectMethod rather
# than esprima's plain FunctionExpression - include both so methods actually
# get analyzed instead of silently skipped.
FUNCTION_TYPES = {
    "FunctionDeclaration", "FunctionExpression", "ArrowFunctionExpression",
    "ClassMethod", "ObjectMethod",
}
LOOP_TYPES = {"ForStatement", "ForInStatement", "ForOfStatement", "WhileStatement", "DoWhileStatement"}


def _walk(node):
    """Generic recursive walker over the Babel AST (plain dicts/lists from JSON)."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item)


def _line_span(node):
    loc = node.get("loc") or {}
    start = loc.get("start", {}).get("line", 0)
    end = loc.get("end", {}).get("line", start)
    return start, end


def _cyclomatic_complexity(node) -> int:
    complexity = 1
    for child in _walk(node):
        t = child.get("type")
        if t in DECISION_TYPES:
            complexity += 1
        elif t == "SwitchCase" and child.get("test") is not None:
            complexity += 1
        elif t == "LogicalExpression" and child.get("operator") in ("&&", "||"):
            complexity += 1
    return complexity


def _infer_variable_assigned_names(tree):
    """Babel doesn't attach a name to `const handleSubmit = () => {}` - the
    name lives on the VariableDeclarator, not the function node. Tag it on
    directly (same dict objects, so this mutates the tree in place)."""
    for node in _walk(tree):
        if node.get("type") == "VariableDeclarator":
            init = node.get("init")
            var_name = (node.get("id") or {}).get("name")
            if init and var_name and init.get("type") in ("ArrowFunctionExpression", "FunctionExpression"):
                init["_inferred_name"] = var_name


def _function_name(node) -> str:
    if node.get("_inferred_name"):
        return node["_inferred_name"]
    # FunctionDeclaration/FunctionExpression use 'id', ClassMethod/ObjectMethod use 'key'
    if node.get("id") and node["id"].get("name"):
        return node["id"]["name"]
    if node.get("key") and node["key"].get("name"):
        return node["key"]["name"]
    return "anonymous"


class JavaScriptParser:
    """Real AST-based analysis for JavaScript/JSX/TypeScript via a Node+Babel
    subprocess. Unlike a pure-Python parser (esprima), Babel supports every
    modern syntax feature in active use: optional chaining, nullish
    coalescing, JSX, TypeScript types, decorators, etc."""

    def __init__(self):
        self.logger = logger.bind(parser="javascript")

    def _run_babel(self, code: str) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["node", _PARSE_SCRIPT],
                input=code.encode("utf-8"),
                capture_output=True,
                timeout=10,
            )
        except FileNotFoundError:
            return {"error": "node runtime not available in this environment"}
        except subprocess.TimeoutExpired:
            return {"error": "parse timed out"}

        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")

        if result.returncode != 0 and not stdout:
            return {"error": f"node process failed: {stderr[:300]}"}

        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return {"error": f"could not parse node output: {stdout[:200]}"}

    def parse(self, code: str, file_path: str) -> Dict[str, Any]:
        parsed = self._run_babel(code)

        if parsed.get("error"):
            self.logger.info(f"JS/TS parse failed for {file_path}: {parsed['error']}")
            return {
                "file_path": file_path,
                "error": parsed["error"],
                "functions": [], "classes": [], "issues": [], "metrics": {},
            }

        tree = parsed.get("ast", {})
        _infer_variable_assigned_names(tree)

        functions = self._extract_functions(tree)
        classes = self._extract_classes(tree)
        issues = self._detect_issues(tree, functions)
        metrics = self._calculate_file_metrics(code, functions, classes)

        return {
            "file_path": file_path,
            "language": "javascript",
            "functions": functions,
            "classes": classes,
            "issues": issues,
            "metrics": metrics,
        }

    def _extract_functions(self, tree) -> List[Dict[str, Any]]:
        functions = []
        for node in _walk(tree):
            if node.get("type") in FUNCTION_TYPES:
                start, end = _line_span(node)
                functions.append({
                    "name": _function_name(node),
                    "line_start": start,
                    "line_end": end,
                    "complexity": _cyclomatic_complexity(node),
                    "parameters": len(node.get("params", [])),
                    "lines_of_code": max(end - start + 1, 1),
                })
        return functions

    def _extract_classes(self, tree) -> List[Dict[str, Any]]:
        classes = []
        for node in _walk(tree):
            if node.get("type") in ("ClassDeclaration", "ClassExpression"):
                start, end = _line_span(node)
                body = (node.get("body") or {}).get("body", [])
                methods = sum(1 for m in body if m.get("type") == "ClassMethod")
                classes.append({
                    "name": (node.get("id") or {}).get("name", "anonymous"),
                    "line_start": start,
                    "line_end": end,
                    "methods": methods,
                    "lines_of_code": max(end - start + 1, 1),
                })
        return classes

    def _detect_issues(self, tree, functions) -> List[Dict[str, Any]]:
        issues = []

        for func in functions:
            if func["complexity"] > 10:
                issues.append({
                    "severity": "high" if func["complexity"] > 15 else "medium",
                    "category": "complexity",
                    "title": f"High cyclomatic complexity in function '{func['name']}'",
                    "description": f"Function has complexity of {func['complexity']}, consider refactoring",
                    "line": func["line_start"],
                    "rule_id": "HIGH_COMPLEXITY",
                })
            if func["lines_of_code"] > 50:
                issues.append({
                    "severity": "medium",
                    "category": "maintainability",
                    "title": f"Long function '{func['name']}'",
                    "description": f"Function has {func['lines_of_code']} lines, consider splitting",
                    "line": func["line_start"],
                    "rule_id": "LONG_FUNCTION",
                })

        for node in _walk(tree):
            t = node.get("type")

            if t == "CatchClause":
                body = (node.get("body") or {}).get("body", [])
                if not body:
                    start, _ = _line_span(node)
                    issues.append({
                        "severity": "medium",
                        "category": "style",
                        "title": "Empty catch block",
                        "description": "Catching an error and doing nothing hides real failures",
                        "line": start,
                        "rule_id": "EMPTY_CATCH",
                    })

            if t == "VariableDeclaration" and node.get("kind") == "var":
                start, _ = _line_span(node)
                issues.append({
                    "severity": "low",
                    "category": "style",
                    "title": "Use of 'var'",
                    "description": "Prefer 'let' or 'const' over 'var' for block scoping",
                    "line": start,
                    "rule_id": "VAR_USAGE",
                })

            if t == "BinaryExpression" and node.get("operator") in ("==", "!="):
                start, _ = _line_span(node)
                issues.append({
                    "severity": "low",
                    "category": "style",
                    "title": f"Loose equality operator '{node.get('operator')}'",
                    "description": "Use strict equality (=== or !==) to avoid type coercion bugs",
                    "line": start,
                    "rule_id": "LOOSE_EQUALITY",
                })

        for node in _walk(tree):
            if node.get("type") in LOOP_TYPES:
                body = node.get("body")
                for child in _walk(body):
                    if child is not node and child.get("type") in LOOP_TYPES:
                        start, _ = _line_span(node)
                        issues.append({
                            "severity": "medium",
                            "category": "performance",
                            "title": "Nested loop detected",
                            "description": "Nested loops can lead to O(n^2) or worse time complexity - verify this scales for expected input size",
                            "line": start,
                            "rule_id": "NESTED_LOOP",
                        })
                        break

        return issues

    def _calculate_file_metrics(self, code, functions, classes) -> Dict[str, Any]:
        lines = code.split("\n")
        complexities = [f["complexity"] for f in functions]
        return {
            "total_lines": len(lines),
            "lines_of_code": len([l for l in lines if l.strip() and not l.strip().startswith("//")]),
            "function_count": len(functions),
            "class_count": len(classes),
            "average_function_complexity": sum(complexities) / len(complexities) if complexities else 0,
            "max_function_complexity": max(complexities, default=0),
        }