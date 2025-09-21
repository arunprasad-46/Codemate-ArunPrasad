from typing import Dict, List, Optional
import ast
import astroid
from pylint.lint import Run
from pylint.reporters import JSONReporter
import radon.complexity as radon
from bandit.core.manager import BanditManager
import subprocess
import json

class AdvancedCodeAnalyzer:
    def __init__(self):
        self.language_analyzers = {
            'python': self.analyze_python,
            'javascript': self.analyze_javascript,
            'java': self.analyze_java
        }

    def analyze_code(self, file_path: str, content: str, lang: str = 'python') -> Dict:
        """
        Performs advanced code analysis using multiple tools based on language
        """
        analyzer = self.language_analyzers.get(lang, self.analyze_generic)
        return analyzer(file_path, content)

    def analyze_python(self, file_path: str, content: str) -> Dict:
        """
        Analyzes Python code using multiple tools:
        - AST Analysis for code structure
        - Pylint for code quality and bugs
        - Radon for complexity metrics
        - Bandit for security issues
        """
        results = {
            'structure': self._analyze_ast(content),
            'quality': self._run_pylint(file_path, content),
            'complexity': self._analyze_complexity(content),
            'security': self._run_security_check(content)
        }
        return results

    def _analyze_ast(self, content: str) -> Dict:
        """
        Analyzes code structure using AST
        """
        try:
            tree = ast.parse(content)
            analysis = {
                'imports': [],
                'functions': [],
                'classes': [],
                'complexity': 0
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    analysis['imports'].extend(n.name for n in node.names)
                elif isinstance(node, ast.ImportFrom):
                    analysis['imports'].append(f"{node.module}.{node.names[0].name}")
                elif isinstance(node, ast.FunctionDef):
                    analysis['functions'].append({
                        'name': node.name,
                        'args': len(node.args.args),
                        'line': node.lineno
                    })
                elif isinstance(node, ast.ClassDef):
                    analysis['classes'].append({
                        'name': node.name,
                        'bases': len(node.bases),
                        'line': node.lineno
                    })
                    
            return analysis
        except Exception as e:
            return {'error': str(e)}

    def _run_pylint(self, file_path: str, content: str) -> Dict:
        """
        Runs Pylint analysis
        """
        try:
            reporter = JSONReporter()
            Run([file_path], reporter=reporter, do_exit=False)
            return {
                'issues': reporter.data,
                'score': reporter.data.get('score', 0)
            }
        except Exception as e:
            return {'error': str(e)}

    def _analyze_complexity(self, content: str) -> Dict:
        """
        Analyzes code complexity using Radon
        """
        try:
            complexity = radon.cc_visit(content)
            return {
                'average_complexity': sum(cc.complexity for cc in complexity) / len(complexity) if complexity else 0,
                'functions': [{
                    'name': cc.name,
                    'complexity': cc.complexity,
                    'line': cc.lineno
                } for cc in complexity]
            }
        except Exception as e:
            return {'error': str(e)}

    def _run_security_check(self, content: str) -> Dict:
        """
        Runs security analysis using Bandit
        """
        try:
            b_mgr = BanditManager()
            b_mgr.discover_files([])
            b_mgr.run_tests()
            
            return {
                'issues': b_mgr.get_issue_list(),
                'metrics': b_mgr.metrics.data
            }
        except Exception as e:
            return {'error': str(e)}

    def analyze_javascript(self, file_path: str, content: str) -> Dict:
        """
        Analyzes JavaScript code using ESLint
        """
        try:
            result = subprocess.run(
                ['npx', 'eslint', '--format', 'json', file_path],
                capture_output=True,
                text=True
            )
            return json.loads(result.stdout)
        except Exception as e:
            return {'error': str(e)}

    def analyze_java(self, file_path: str, content: str) -> Dict:
        """
        Analyzes Java code using PMD
        """
        try:
            result = subprocess.run(
                ['pmd', 'check', '-f', 'json', '-R', 'rulesets/java/quickstart.xml', file_path],
                capture_output=True,
                text=True
            )
            return json.loads(result.stdout)
        except Exception as e:
            return {'error': str(e)}

    def analyze_generic(self, file_path: str, content: str) -> Dict:
        """
        Performs basic analysis for unsupported languages
        """
        return {
            'lines_of_code': len(content.splitlines()),
            'character_count': len(content),
            'todo_count': content.lower().count('todo'),
            'fixme_count': content.lower().count('fixme')
        }