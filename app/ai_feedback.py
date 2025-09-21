from typing import Dict, List, Any
import re

class AIFeedbackGenerator:
    def __init__(self):
        # Common code patterns and their suggestions
        self.patterns = {
            'performance': self._get_performance_patterns(),
            'security': self._get_security_patterns(),
            'maintainability': self._get_maintainability_patterns(),
            'best_practices': self._get_best_practice_patterns()
        }

    def generate_ai_feedback(self, code_content: str, language: str, analysis_results: Dict) -> Dict[str, Any]:
        """Generate AI-driven feedback for code"""
        feedback = {
            "summary": self._generate_summary(analysis_results),
            "smart_suggestions": self._generate_smart_suggestions(code_content, language, analysis_results),
            "improvement_areas": self._identify_improvement_areas(analysis_results),
            "best_practices": self._check_best_practices(code_content, language),
            "priority_fixes": self._prioritize_fixes(analysis_results)
        }
        return feedback

    def _generate_summary(self, analysis: Dict) -> Dict[str, Any]:
        """Generate an AI-driven summary of the code analysis"""
        metrics = analysis.get("metrics", {})
        complexity = analysis.get("complexity", {})
        security = analysis.get("security", [])
        
        # Determine the overall code health
        health_score = self._calculate_health_score(analysis)
        
        return {
            "code_health": {
                "score": health_score,
                "status": self._get_health_status(health_score),
                "primary_concerns": self._identify_primary_concerns(analysis)
            },
            "key_metrics": {
                "maintainability": metrics.get("maintainability_index", 0),
                "security_issues": len(security),
                "complexity_level": self._assess_complexity(complexity)
            },
            "quick_wins": self._identify_quick_wins(analysis)
        }

    def _generate_smart_suggestions(self, content: str, language: str, analysis: Dict) -> List[Dict]:
        """Generate intelligent suggestions based on code patterns and analysis"""
        suggestions = []
        
        # Get language-specific patterns
        patterns = self._get_language_patterns(language)
        
        # Analyze code patterns
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for category, category_patterns in patterns.items():
                for pattern, suggestion in category_patterns.items():
                    if re.search(pattern, line):
                        suggestions.append({
                            "category": category,
                            "line": i,
                            "suggestion": suggestion,
                            "severity": "medium",
                            "context": line.strip(),
                            "improvement_type": "pattern"
                        })

        # Add suggestions based on metrics
        suggestions.extend(self._generate_metric_based_suggestions(analysis))
        
        return suggestions

    def _identify_improvement_areas(self, analysis: Dict) -> List[Dict]:
        """Identify areas that need improvement"""
        areas = []
        
        # Check complexity
        if "complexity" in analysis:
            complex_functions = [f for f in analysis["complexity"].get("functions", [])
                              if f.get("complexity", 0) > 10]
            if complex_functions:
                areas.append({
                    "area": "code_complexity",
                    "severity": "high" if len(complex_functions) > 3 else "medium",
                    "suggestion": "Consider breaking down complex functions",
                    "affected_items": [f["name"] for f in complex_functions]
                })

        # Check maintainability
        if analysis.get("metrics", {}).get("maintainability_index", 100) < 65:
            areas.append({
                "area": "maintainability",
                "severity": "high",
                "suggestion": "Code needs better structure and documentation",
                "improvement_tips": [
                    "Add more comments to explain complex logic",
                    "Break down large functions into smaller ones",
                    "Use more descriptive variable names"
                ]
            })

        return areas

    def _check_best_practices(self, content: str, language: str) -> List[Dict]:
        """Check for language-specific best practices"""
        practices = []
        patterns = self._get_language_specific_practices(language)
        
        for practice_name, pattern in patterns.items():
            if re.search(pattern, content):
                practices.append({
                    "name": practice_name,
                    "status": "violation",
                    "recommendation": self._get_practice_recommendation(practice_name)
                })

        return practices

    def _prioritize_fixes(self, analysis: Dict) -> List[Dict]:
        """Prioritize which issues should be fixed first"""
        issues = []
        
        # Collect all issues
        if "security" in analysis:
            for issue in analysis["security"]:
                issues.append({
                    "type": "security",
                    "severity": "high",
                    "issue": issue["message"],
                    "priority": 1,
                    "fix_difficulty": "medium"
                })

        if "complexity" in analysis:
            for func in analysis.get("complexity", {}).get("functions", []):
                if func.get("complexity", 0) > 15:
                    issues.append({
                        "type": "complexity",
                        "severity": "medium",
                        "issue": f"High complexity in function {func['name']}",
                        "priority": 2,
                        "fix_difficulty": "high"
                    })

        # Sort by priority
        return sorted(issues, key=lambda x: (x["priority"], -len(x["issue"])))

    def _calculate_health_score(self, analysis: Dict) -> float:
        """Calculate overall code health score"""
        score = 100.0
        
        # Deduct for security issues
        security_issues = len(analysis.get("security", []))
        score -= security_issues * 10

        # Deduct for complexity
        for func in analysis.get("complexity", {}).get("functions", []):
            if func.get("complexity", 0) > 10:
                score -= 5

        # Deduct for maintainability
        maintainability = analysis.get("metrics", {}).get("maintainability_index", 100)
        if maintainability < 65:
            score -= (65 - maintainability) / 2

        return max(0, min(100, score))

    def _get_language_patterns(self, language: str) -> Dict:
        """Get language-specific patterns to check"""
        common_patterns = {
            "performance": {
                r"for\s+\w+\s+in\s+range\(len\(": "Use enumerate() instead of range(len())",
                r"while\s+True:": "Consider using a more specific condition",
            },
            "security": {
                r"password\s*=\s*['\"][^'\"]+['\"]": "Avoid hardcoding sensitive information",
                r"eval\(": "Avoid using eval() for security reasons",
            }
        }
        
        language_specific = self._get_language_specific_patterns(language)
        common_patterns.update(language_specific)
        
        return common_patterns

    def _get_language_specific_patterns(self, language: str) -> Dict:
        """Get patterns specific to a programming language"""
        patterns = {
            "python": {
                "performance": {
                    r"\.append\(.*\)\s+in\s+loop": "Consider using list comprehension",
                    r"dict\(\[\[": "Use dict comprehension for better readability"
                }
            },
            "javascript": {
                "performance": {
                    r"\.forEach\(": "Consider using for...of for better performance",
                    r"\.map\(.+\.filter\(": "Combine map and filter operations"
                }
            }
            # Add patterns for other languages
        }
        return patterns.get(language, {})

    def _get_language_specific_practices(self, language: str) -> Dict:
        """Get best practices for specific languages"""
        practices = {
            "python": {
                "use_type_hints": r"def\s+\w+\([^:]+\)\s*:",
                "use_docstrings": r"def\s+\w+\([^)]*\)[^:]*:\s*[^\"\'\n]",
            },
            "javascript": {
                "use_const_let": r"var\s+",
                "use_strict_equality": r"==(?!=)",
            }
        }
        return practices.get(language, {})

    def _get_practice_recommendation(self, practice: str) -> str:
        """Get recommendation for best practice violations"""
        recommendations = {
            "use_type_hints": "Add type hints to improve code clarity and catch type-related bugs early",
            "use_docstrings": "Add docstrings to document function purpose and parameters",
            "use_const_let": "Use 'const' or 'let' instead of 'var' for better scoping",
            "use_strict_equality": "Use === instead of == for strict equality comparison"
        }
        return recommendations.get(practice, "Follow language best practices")

    def _assess_complexity(self, complexity: Dict) -> str:
        """Assess the overall complexity level"""
        functions = complexity.get("functions", [])
        if not functions:
            return "low"
            
        avg_complexity = sum(f.get("complexity", 0) for f in functions) / len(functions)
        if avg_complexity > 15:
            return "high"
        elif avg_complexity > 8:
            return "medium"
        return "low"

    def _identify_primary_concerns(self, analysis: Dict) -> List[str]:
        """Identify primary concerns in the code"""
        concerns = []
        
        if len(analysis.get("security", [])) > 0:
            concerns.append("security vulnerabilities")
            
        if analysis.get("metrics", {}).get("maintainability_index", 100) < 65:
            concerns.append("low maintainability")
            
        complex_funcs = [f for f in analysis.get("complexity", {}).get("functions", [])
                        if f.get("complexity", 0) > 10]
        if complex_funcs:
            concerns.append("high complexity")
            
        return concerns

    def _identify_quick_wins(self, analysis: Dict) -> List[Dict]:
        """Identify easy-to-fix issues"""
        quick_wins = []
        
        # Look for simple style issues
        for issue in analysis.get("linting", []):
            if issue.get("type") in ["convention", "style"]:
                quick_wins.append({
                    "type": "style",
                    "fix": issue["message"],
                    "effort": "low"
                })
                
        return quick_wins[:3]  # Return top 3 quick wins

    def _get_performance_patterns(self) -> Dict:
        return {
            r"for.*in.*:": "Consider using list comprehension for better performance",
            r"\.copy\(\)": "Check if deep copy is really necessary",
        }

    def _get_security_patterns(self) -> Dict:
        return {
            r"input\(": "Validate user input",
            r"subprocess\.": "Ensure proper input sanitization for subprocess",
        }

    def _get_maintainability_patterns(self) -> Dict:
        return {
            r"def.*\(.*\)": "Consider adding docstring",
            r"if.*if.*if": "Consider simplifying nested conditions",
        }

    def _get_best_practice_patterns(self) -> Dict:
        return {
            r"print\(": "Consider using logging for production code",
            r"except:": "Specify exception types explicitly",
        }
