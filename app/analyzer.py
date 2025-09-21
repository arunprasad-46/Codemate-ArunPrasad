import subprocess
import json
import re
from typing import List, Dict, Optional, Any
from radon.complexity import cc_visit
from radon.metrics import mi_visit
from radon.raw import analyze
import ast

class CodeAnalyzer:
    def __init__(self):
        self.analysis_results = {}
        self.language_linters = {
            # Map file extensions to their respective linting functions
            'py': self._run_pylint,
            'js': self._run_eslint,
            'jsx': self._run_eslint,
            'ts': self._run_eslint,
            'tsx': self._run_eslint,
            'java': self._run_checkstyle,
            'cpp': self._run_cppcheck,
            'hpp': self._run_cppcheck,
            'c': self._run_cppcheck,
            'h': self._run_cppcheck,
            'cc': self._run_cppcheck,
            'go': self._run_golint,
            'rb': self._run_rubocop,
            'php': self._run_phpcs,
            'cs': self._run_dotnetformat,
            'generic': self._analyze_generic  # Fallback for unsupported languages
        }

    def analyze_code(self, file_path: str, content: str, lang: str = None) -> Dict[str, Any]:
        """
        Analyze code using multiple metrics and return comprehensive results
        """
        # Determine language from file extension if not provided
        if lang is None:
            ext = file_path.split('.')[-1].lower() if '.' in file_path else 'generic'
            lang = ext if ext in self.language_linters else 'generic'
        else:
            lang = lang.lower()
            
        results = {
            "path": file_path,
            "language": lang,
            "linting": self._run_linter(file_path, content, lang),
            "complexity": self._analyze_complexity(content, lang),
            "metrics": self._analyze_metrics(content, lang),
            "raw_metrics": self._analyze_raw_metrics(content),
            "security": self._check_security_issues(content, lang)
        }
        return results

    def _run_linter(self, file_path: str, content: str, lang: str) -> List[Dict]:
        """Run appropriate linter based on language"""
        try:
            if lang in self.language_linters:
                return self.language_linters[lang](file_path)
            return self._analyze_generic(content)
        except Exception as e:
            return [{
                "line": "?",
                "message": f"Error running linter for {lang}: {str(e)}",
                "symbol": "error",
                "type": "error"
            }]
            
    def _analyze_generic(self, content: str) -> List[Dict]:
        """Basic analysis for unsupported languages"""
        issues = []
        
        # Check line length
        for i, line in enumerate(content.split('\n'), 1):
            if len(line.strip()) > 100:
                issues.append({
                    "line": i,
                    "message": "Line too long (exceeds 100 characters)",
                    "symbol": "line-length",
                    "type": "convention"
                })
            
            # Check for TODO comments
            if 'TODO' in line or 'FIXME' in line:
                issues.append({
                    "line": i,
                    "message": "Found TODO/FIXME comment",
                    "symbol": "todo-comment",
                    "type": "info"
                })
        
        return issues

    def _run_pylint(self, file_path: str) -> List[Dict]:
        """Run pylint for code quality analysis"""
        try:
            cmd = ["pylint", file_path, "-f", "json"]
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.stdout.strip():
                messages = json.loads(process.stdout)
                return [{
                    "line": msg.get("line", "?"),
                    "message": msg.get("message", ""),
                    "symbol": msg.get("symbol", ""),
                    "type": msg.get("type", "")
                } for msg in messages]
        except Exception as e:
            return [{
                "line": "?",
                "message": f"Error running pylint: {str(e)}",
                "symbol": "error",
                "type": "error"
            }]
        return []

    def _run_eslint(self, file_path: str) -> List[Dict]:
        """Run ESLint for JavaScript/TypeScript"""
        try:
            cmd = ["eslint", "--format", "json", file_path]
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.stdout.strip():
                messages = json.loads(process.stdout)[0]["messages"]
                return [{
                    "line": msg.get("line", "?"),
                    "message": msg.get("message", ""),
                    "symbol": msg.get("ruleId", ""),
                    "type": msg.get("severity", "")
                } for msg in messages]
        except Exception:
            return self._analyze_generic(open(file_path).read())

    def _run_checkstyle(self, file_path: str) -> List[Dict]:
        """Run Checkstyle for Java"""
        try:
            cmd = ["checkstyle", "-f", "json", file_path]
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.stdout.strip():
                return [{
                    "line": error.get("line", "?"),
                    "message": error.get("message", ""),
                    "symbol": error.get("source", ""),
                    "type": "error"
                } for error in json.loads(process.stdout)]
        except Exception:
            return self._analyze_generic(open(file_path).read())

    def _run_cppcheck(self, file_path: str) -> List[Dict]:
        """Run Cppcheck for C/C++"""
        try:
            cmd = ["cppcheck", "--enable=all", "--template=json", file_path]
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.stdout.strip():
                return [{
                    "line": error.get("line", "?"),
                    "message": error.get("message", ""),
                    "symbol": error.get("id", ""),
                    "type": error.get("severity", "")
                } for error in json.loads(process.stdout)]
        except Exception:
            return self._analyze_generic(open(file_path).read())

    def _run_golint(self, file_path: str) -> List[Dict]:
        """Run golint for Go code"""
        try:
            cmd = ["golint", file_path]
            process = subprocess.run(cmd, capture_output=True, text=True)
            issues = []
            if process.stdout.strip():
                for line in process.stdout.splitlines():
                    # golint format: file:line:col: message
                    parts = line.split(":", 3)
                    if len(parts) >= 4:
                        issues.append({
                            "line": parts[1],
                            "message": parts[3].strip(),
                            "symbol": "style",
                            "type": "warning"
                        })
            return issues
        except Exception:
            return self._analyze_generic(open(file_path).read())

    def _run_rubocop(self, file_path: str) -> List[Dict]:
        """Run RuboCop for Ruby code"""
        try:
            cmd = ["rubocop", "--format", "json", file_path]
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.stdout.strip():
                data = json.loads(process.stdout)
                issues = []
                for file_data in data["files"]:
                    for offense in file_data["offenses"]:
                        issues.append({
                            "line": offense["location"]["line"],
                            "message": offense["message"],
                            "symbol": offense["cop_name"],
                            "type": offense["severity"]
                        })
                return issues
        except Exception:
            return self._analyze_generic(open(file_path).read())

    def _run_phpcs(self, file_path: str) -> List[Dict]:
        """Run PHP_CodeSniffer for PHP code"""
        try:
            cmd = ["phpcs", "--report=json", file_path]
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.stdout.strip():
                data = json.loads(process.stdout)
                issues = []
                for file_data in data["files"].values():
                    for message in file_data["messages"]:
                        issues.append({
                            "line": message["line"],
                            "message": message["message"],
                            "symbol": message["source"],
                            "type": "error" if message["type"] == "ERROR" else "warning"
                        })
                return issues
        except Exception:
            return self._analyze_generic(open(file_path).read())

    def _run_dotnetformat(self, file_path: str) -> List[Dict]:
        """Run dotnet format for C# code"""
        try:
            cmd = ["dotnet", "format", "--verify-no-changes", "--report", file_path]
            process = subprocess.run(cmd, capture_output=True, text=True)
            issues = []
            if process.returncode != 0:
                # If format check fails, there are style issues
                for line in process.stdout.splitlines():
                    if ":" in line and "warning" in line.lower() or "error" in line.lower():
                        parts = line.split(":", 2)
                        if len(parts) >= 3:
                            issues.append({
                                "line": parts[1].strip(),
                                "message": parts[2].strip(),
                                "symbol": "style",
                                "type": "warning"
                            })
            return issues
        except Exception:
            return self._analyze_generic(open(file_path).read())

    def _analyze_complexity(self, content: str, lang: str = 'python') -> Dict[str, Any]:
        """Analyze code complexity using appropriate tools"""
        try:
            if lang == 'python':
                results = cc_visit(content)
            else:
                # For other languages, use a simpler complexity analysis
                results = self._analyze_generic_complexity(content)
            
            return {
                "functions": [{
                    "name": item.name if hasattr(item, 'name') else 'unknown',
                    "complexity": item.complexity if hasattr(item, 'complexity') else self._estimate_complexity(item),
                    "lineno": item.lineno if hasattr(item, 'lineno') else 0,
                    "rank": self._get_complexity_rank(item.complexity if hasattr(item, 'complexity') else 0)
                } for item in results]
            }
        except Exception as e:
            return {"error": str(e)}

    def _analyze_generic_complexity(self, content: str) -> List[Dict]:
        """Simple complexity analysis for non-Python code"""
        results = []
        current_function = None
        
        for i, line in enumerate(content.split('\n'), 1):
            line = line.strip()
            
            # Detect function/method definitions
            if any(keyword in line.lower() for keyword in ['function', 'def ', 'method', 'sub ']):
                if current_function:
                    results.append(current_function)
                current_function = {
                    'name': line.split('(')[0].split()[-1],
                    'lineno': i,
                    'complexity': 1,
                    'branches': []
                }
            
            # Count branching statements
            if current_function and any(keyword in line.lower() for keyword in 
                ['if', 'else', 'for', 'while', 'case', 'switch', 'catch']):
                current_function['complexity'] += 1
        
        if current_function:
            results.append(current_function)
        
        return results

    def _estimate_complexity(self, item: Dict) -> int:
        """Estimate complexity for non-Python code"""
        if isinstance(item, dict):
            return item.get('complexity', 1)
        return 1
        try:
            results = cc_visit(content)
            return {
                "functions": [{
                    "name": item.name,
                    "complexity": item.complexity,
                    "lineno": item.lineno,
                    "rank": self._get_complexity_rank(item.complexity)
                } for item in results]
            }
        except Exception as e:
            return {"error": str(e)}

    def _analyze_metrics(self, content: str, lang: str = 'python') -> Dict[str, Any]:
        """Calculate maintainability metrics for any language"""
        try:
            if lang == 'python':
                mi_score = mi_visit(content, multi=True)
            else:
                # Calculate generic maintainability index for other languages
                mi_score = self._calculate_generic_maintainability(content)
            
            return {
                "maintainability_index": mi_score,
                "rank": self._get_maintainability_rank(mi_score)
            }
        except Exception as e:
            return {"error": str(e)}

    def _calculate_generic_maintainability(self, content: str) -> float:
        """Calculate a generic maintainability index for non-Python code"""
        lines = content.split('\n')
        
        # Count metrics
        total_lines = len(lines)
        code_lines = len([l for l in lines if l.strip() and not l.strip().startswith(('//', '#', '/*', '*', '*/')) ])
        comment_lines = len([l for l in lines if l.strip() and l.strip().startswith(('//', '#', '/*', '*', '*/'))])
        empty_lines = total_lines - code_lines - comment_lines
        
        # Calculate basic metrics
        comment_ratio = (comment_lines / total_lines) if total_lines > 0 else 0
        code_density = (code_lines / total_lines) if total_lines > 0 else 0
        
        # Calculate maintainability score (0-100)
        base_score = 100
        
        # Deduct points for poor commenting
        if comment_ratio < 0.1:  # Less than 10% comments
            base_score -= 20
        elif comment_ratio < 0.2:  # Less than 20% comments
            base_score -= 10
            
        # Deduct points for code density
        if code_density > 0.9:  # More than 90% code
            base_score -= 10
            
        # Adjust based on complexity
        try:
            complexity_results = self._analyze_generic_complexity(content)
            avg_complexity = sum(r['complexity'] for r in complexity_results) / len(complexity_results) if complexity_results else 1
            if avg_complexity > 10:
                base_score -= 20
            elif avg_complexity > 5:
                base_score -= 10
        except:
            pass
            
        return max(0, min(100, base_score))  # Ensure score is between 0 and 100

    def _analyze_raw_metrics(self, content: str) -> Dict[str, Any]:
        """Analyze raw metrics like LOC, SLOC, comments using radon"""
        try:
            metrics = analyze(content)
            return {
                "loc": metrics.loc,
                "sloc": metrics.sloc,
                "comments": metrics.comments,
                "multi": metrics.multi,
                "blank": metrics.blank
            }
        except Exception as e:
            return {"error": str(e)}

    def _check_security_issues(self, content: str, lang: str = 'python') -> List[Dict]:
        """Security checks for any programming language"""
        issues = []
        try:
            # Common security checks for all languages
            issues.extend(self._check_common_security_issues(content))
            
            # Language-specific security checks
            if lang == 'python':
                issues.extend(self._check_python_security(content))
            elif lang in ['javascript', 'typescript']:
                issues.extend(self._check_js_security(content))
            elif lang == 'java':
                issues.extend(self._check_java_security(content))
            elif lang in ['cpp', 'c']:
                issues.extend(self._check_cpp_security(content))
            
        except Exception as e:
            issues.append({
                "type": "error",
                "message": f"Error checking security issues: {str(e)}",
                "line": "?"
            })
        return issues

    def _check_common_security_issues(self, content: str) -> List[Dict]:
        """Check for common security issues across all languages"""
        issues = []
        
        # Define security patterns
        patterns = {
            'hardcoded_secrets': r'(?i)(password|secret|key|token|pwd)\s*[=:]\s*["\'][^"\']+["\']',
            'unsafe_comments': r'(?i)#?\s*(todo|fixme|hack|xxx):?\s*(?:password|security|vulnerability)',
            'insecure_protocols': r'(?i)(http://|ftp://|telnet://)',
            'potential_sqli': r'(?i)(select|insert|update|delete).*(\+\s*[\'"]|\'\s*\+|\'\s*\|\|)',
            'debug_statements': r'(?i)(console\.(log|debug)|print|var_dump|debug|alert)\(',
        }
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Check for hardcoded secrets
            for pattern_name, pattern in patterns.items():
                if re.search(pattern, line):
                    issues.append({
                        "type": "security",
                        "message": f"Potential security issue: {pattern_name.replace('_', ' ')}",
                        "line": i,
                        "severity": "high" if "hardcoded_secrets" in pattern_name else "medium"
                    })
        
        return issues

    def _check_python_security(self, content: str) -> List[Dict]:
        """Python-specific security checks"""
        issues = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                # Check for potentially unsafe exec/eval usage
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in ['exec', 'eval', 'input']:
                        issues.append({
                            "type": "security",
                            "message": f"Potentially unsafe use of {node.func.id}()",
                            "line": node.lineno,
                            "severity": "high"
                        })
        except:
            pass
        return issues

    def _check_js_security(self, content: str) -> List[Dict]:
        """JavaScript/TypeScript security checks"""
        issues = []
        
        dangerous_patterns = {
            r'eval\(': "Potentially unsafe use of eval()",
            r'innerHTML\s*=': "Potentially unsafe innerHTML assignment",
            r'document\.write\(': "Potentially unsafe document.write()",
            r'(?:window|document)\.location\s*=': "Potentially unsafe location assignment",
            r'localStorage\.(get|set)Item': "Check for sensitive data in localStorage",
        }
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, message in dangerous_patterns.items():
                if re.search(pattern, line):
                    issues.append({
                        "type": "security",
                        "message": message,
                        "line": i,
                        "severity": "high"
                    })
        
        return issues

    def _check_java_security(self, content: str) -> List[Dict]:
        """Java security checks"""
        issues = []
        
        patterns = {
            r'System\.exit\(': "Potentially unsafe System.exit()",
            r'printStackTrace\(': "Exposing stack trace information",
            r'new\s+File\(': "Check file operations for path traversal",
            r'Class\.forName\(': "Potentially unsafe class loading",
        }
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, message in patterns.items():
                if re.search(pattern, line):
                    issues.append({
                        "type": "security",
                        "message": message,
                        "line": i,
                        "severity": "medium"
                    })
        
        return issues

    def _check_cpp_security(self, content: str) -> List[Dict]:
        """C/C++ security checks"""
        issues = []
        
        dangerous_functions = {
            r'gets\(': "Unsafe gets() function",
            r'strcpy\(': "Use strncpy() instead of strcpy()",
            r'strcat\(': "Use strncat() instead of strcat()",
            r'printf\([^"]*%s': "Potential format string vulnerability",
            r'system\(': "Potentially unsafe system() call",
        }
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, message in dangerous_functions.items():
                if re.search(pattern, line):
                    issues.append({
                        "type": "security",
                        "message": message,
                        "line": i,
                        "severity": "high"
                    })
        
        return issues

    @staticmethod
    def _get_complexity_rank(score: int) -> str:
        """Get rank for cyclomatic complexity score"""
        if score <= 5:
            return "A"
        elif score <= 10:
            return "B"
        elif score <= 20:
            return "C"
        elif score <= 30:
            return "D"
        else:
            return "F"

    @staticmethod
    def _get_maintainability_rank(score: float) -> str:
        """Get rank for maintainability index"""
        if score >= 100:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 60:
            return "C"
        elif score >= 40:
            return "D"
        else:
            return "F"
