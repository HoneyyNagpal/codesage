from typing import Dict, List, Any
import structlog

try:
    import esprima
except ImportError:  # pragma: no cover
    esprima = None

logger = structlog.get_logger()

DECISION_TYPES = {
    "IfStatement", "ForStatement", "ForInStatement", "ForOfStatement",
    "WhileStatement", "DoWhileStatement", "CatchClause", "ConditionalExpression",
}
FUNCTION_TYPES = {"FunctionDeclaration", "FunctionExpression", "ArrowFunctionExpression"}


def _walk(node):
    """Generic recursive walker over esprima's dict-based AST (from toDict())."""
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


def _function_name(node) -> str:
    if node.get("id") and node["id"].get("name"):
        return node["id"]["name"]
    return "anonymous"


class JavaScriptParser:
    """Real AST-based analysis for JavaScript/JSX using esprima. TypeScript-only
    syntax (type annotations, interfaces) will fail to parse - caller should
    fall back to a lighter-weight pass for .ts/.tsx files with such syntax."""

    def __init__(self):
        self.logger = logger.bind(parser="javascript")

    def parse(self, code: str, file_path: str) -> Dict[str, Any]:
        if esprima is None:
            return {
                "file_path": file_path, "error": "esprima not installed",
                "functions": [], "classes": [], "issues": [], "metrics": {},
            }

        try:
            tree = esprima.parseModule(
                code, options={"loc": True, "jsx": True, "tolerant": True}
            ).toDict()
        except Exception as e:
            self.logger.info(f"JS parse failed for {file_path}: {e}")
            return {
                "file_path": file_path,
                "error": f"Parse error (possibly TypeScript-specific syntax): {e}",
                "functions": [], "classes": [], "issues": [], "metrics": {},
            }

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
                methods = sum(1 for m in body if m.get("type") == "MethodDefinition")
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

            # Empty catch block - swallows errors silently
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

            # var instead of let/const
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

            # Loose equality
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

        # Nested loops - real performance risk
        loop_types = {"ForStatement", "ForInStatement", "ForOfStatement", "WhileStatement", "DoWhileStatement"}
        for node in _walk(tree):
            if node.get("type") in loop_types:
                body = node.get("body")
                for child in _walk(body):
                    if child is not node and child.get("type") in loop_types:
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