import ast
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


@dataclass
class FunctionMetrics:
    """Metrics for a single function"""
    name: str
    line_start: int
    line_end: int
    complexity: int
    parameters: int
    returns: bool
    lines_of_code: int
    cognitive_complexity: int


@dataclass
class ClassMetrics:
    """Metrics for a single class"""
    name: str
    line_start: int
    line_end: int
    methods: int
    attributes: int
    inheritance_depth: int
    lines_of_code: int


class PythonParser:
    """Advanced Python code parser using AST"""
    
    def __init__(self):
        self.logger = logger.bind(parser="python")
    
    def parse(self, code: str, file_path: str) -> Dict[str, Any]:
        """
        Parse Python code and extract comprehensive metrics
        
        Args:
            code: Source code string
            file_path: Path to the file being analyzed
            
        Returns:
            Dictionary containing all extracted metrics and issues
        """
        try:
            tree = ast.parse(code)
            
            results = {
                "file_path": file_path,
                "language": "python",
                "functions": self._extract_functions(tree, code),
                "classes": self._extract_classes(tree, code),
                "imports": self._extract_imports(tree),
                "complexity": self._calculate_complexity(tree),
                "issues": [],
                "metrics": {}
            }
            
            # Calculate file-level metrics
            results["metrics"] = self._calculate_file_metrics(results, code)
            
            # Detect issues
            results["issues"] = self._detect_issues(tree, code, results)
            
            return results
            
        except SyntaxError as e:
            self.logger.error(f"Syntax error parsing {file_path}", error=str(e))
            return {
                "file_path": file_path,
                "error": f"Syntax error: {str(e)}",
                "functions": [],
                "classes": [],
                "issues": [],
                "metrics": {}
            }
        except Exception as e:
            self.logger.error(f"Error parsing {file_path}", error=str(e))
            raise
    
    def _extract_functions(self, tree: ast.AST, code: str) -> List[FunctionMetrics]:
        """Extract all function definitions and their metrics"""
        functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                metrics = FunctionMetrics(
                    name=node.name,
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    complexity=self._calculate_cyclomatic_complexity(node),
                    parameters=len(node.args.args),
                    returns=any(isinstance(n, ast.Return) for n in ast.walk(node)),
                    lines_of_code=self._count_lines_of_code(node),
                    cognitive_complexity=self._calculate_cognitive_complexity(node)
                )
                functions.append(metrics)
        
        return functions
    
    def _extract_classes(self, tree: ast.AST, code: str) -> List[ClassMetrics]:
        """Extract all class definitions and their metrics"""
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = sum(1 for n in node.body if isinstance(n, ast.FunctionDef))
                attributes = sum(1 for n in node.body if isinstance(n, ast.Assign))
                
                metrics = ClassMetrics(
                    name=node.name,
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    methods=methods,
                    attributes=attributes,
                    inheritance_depth=len(node.bases),
                    lines_of_code=self._count_lines_of_code(node)
                )
                classes.append(metrics)
        
        return classes
    
    def _extract_imports(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract all import statements"""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "module": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno
                    })
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.append({
                        "module": f"{node.module}.{alias.name}" if node.module else alias.name,
                        "alias": alias.asname,
                        "line": node.lineno
                    })
        
        return imports
    
    def _calculate_cyclomatic_complexity(self, node: ast.AST) -> int:
        """Calculate McCabe cyclomatic complexity"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            # Add 1 for each decision point
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
                complexity += 1
        
        return complexity
    
    def _calculate_cognitive_complexity(self, node: ast.AST, nesting: int = 0) -> int:
        """Calculate cognitive complexity (more human-friendly than cyclomatic)"""
        complexity = 0
        
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.While, ast.For)):
                complexity += 1 + nesting
                complexity += self._calculate_cognitive_complexity(child, nesting + 1)
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1 + nesting
            elif isinstance(child, (ast.BoolOp, ast.Compare)):
                complexity += 1
            else:
                complexity += self._calculate_cognitive_complexity(child, nesting)
        
        return complexity
    
    def _count_lines_of_code(self, node: ast.AST) -> int:
        """Count actual lines of code (excluding comments and blank lines)"""
        if hasattr(node, 'end_lineno') and node.end_lineno:
            return node.end_lineno - node.lineno + 1
        return 1
    
    def _calculate_complexity(self, tree: ast.AST) -> Dict[str, int]:
        """Calculate overall file complexity metrics"""
        total_complexity = 0
        max_complexity = 0
        function_count = 0
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity = self._calculate_cyclomatic_complexity(node)
                total_complexity += complexity
                max_complexity = max(max_complexity, complexity)
                function_count += 1
        
        return {
            "total": total_complexity,
            "max": max_complexity,
            "average": total_complexity / function_count if function_count > 0 else 0
        }
    
    def _calculate_file_metrics(self, results: Dict, code: str) -> Dict[str, Any]:
        """Calculate comprehensive file-level metrics"""
        lines = code.split('\n')
        
        return {
            "total_lines": len(lines),
            "lines_of_code": len([l for l in lines if l.strip() and not l.strip().startswith('#')]),
            "comment_lines": len([l for l in lines if l.strip().startswith('#')]),
            "blank_lines": len([l for l in lines if not l.strip()]),
            "function_count": len(results["functions"]),
            "class_count": len(results["classes"]),
            "import_count": len(results["imports"]),
            "average_function_complexity": sum(f.complexity for f in results["functions"]) / len(results["functions"]) if results["functions"] else 0,
            "max_function_complexity": max((f.complexity for f in results["functions"]), default=0)
        }
    
    def _detect_issues(self, tree: ast.AST, code: str, results: Dict) -> List[Dict[str, Any]]:
        """Detect potential code issues and anti-patterns"""
        issues = []
        
        # Check for high complexity functions
        for func in results["functions"]:
            if func.complexity > 10:
                issues.append({
                    "severity": "high" if func.complexity > 15 else "medium",
                    "category": "complexity",
                    "title": f"High cyclomatic complexity in function '{func.name}'",
                    "description": f"Function has complexity of {func.complexity}, consider refactoring",
                    "line": func.line_start,
                    "rule_id": "HIGH_COMPLEXITY"
                })
            
            if func.cognitive_complexity > 15:
                issues.append({
                    "severity": "medium",
                    "category": "complexity",
                    "title": f"High cognitive complexity in function '{func.name}'",
                    "description": f"Function has cognitive complexity of {func.cognitive_complexity}",
                    "line": func.line_start,
                    "rule_id": "HIGH_COGNITIVE_COMPLEXITY"
                })
            
            if func.lines_of_code > 50:
                issues.append({
                    "severity": "medium",
                    "category": "maintainability",
                    "title": f"Long function '{func.name}'",
                    "description": f"Function has {func.lines_of_code} lines, consider splitting",
                    "line": func.line_start,
                    "rule_id": "LONG_FUNCTION"
                })
        
        # Check for large classes
        for cls in results["classes"]:
            if cls.methods > 20:
                issues.append({
                    "severity": "medium",
                    "category": "maintainability",
                    "title": f"Class '{cls.name}' has too many methods",
                    "description": f"Class has {cls.methods} methods, consider splitting responsibilities",
                    "line": cls.line_start,
                    "rule_id": "TOO_MANY_METHODS"
                })
        
        # Detect common anti-patterns
        for node in ast.walk(tree):
            # Bare except clauses
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                issues.append({
                    "severity": "medium",
                    "category": "style",
                    "title": "Bare except clause",
                    "description": "Using bare 'except:' catches all exceptions, specify exception types",
                    "line": node.lineno,
                    "rule_id": "BARE_EXCEPT"
                })
            
            # Global variables (excluding constants)
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if not target.id.isupper():  # Not a constant
                            issues.append({
                                "severity": "low",
                                "category": "style",
                                "title": f"Global variable '{target.id}'",
                                "description": "Global variables can make code harder to maintain",
                                "line": node.lineno,
                                "rule_id": "GLOBAL_VARIABLE"
                            })
        
        return issues