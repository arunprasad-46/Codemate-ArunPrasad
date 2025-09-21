from typing import Dict, List, Any

class FeedbackGenerator:
    def __init__(self):
        self.suggestions = []

    def generate_feedback(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive feedback from analysis results"""
        self.suggestions = []
        
        quality_score = self._calculate_quality_score(analysis_results)
        feedback = {
            "summary": self._generate_summary(analysis_results),
            "suggestions": self._generate_suggestions(analysis_results),
            "security_concerns": self._analyze_security_issues(analysis_results),
            "code_quality": self._analyze_code_quality(analysis_results),
            "detailed_metrics": self._format_detailed_metrics(analysis_results),
            "score": {
                "overall_score": quality_score["overall_score"],
                "breakdown": quality_score["breakdown"],
                "grade": self._get_grade(quality_score["overall_score"]),
                "category_scores": quality_score["category_scores"]
            }
        }
        return feedback

    def _calculate_quality_score(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate a weighted quality score based on various metrics"""
        scores = {
            "maintainability": self._calculate_maintainability_score(results),
            "complexity": self._calculate_complexity_score(results),
            "style": self._calculate_style_score(results),
            "security": self._calculate_security_score(results),
            "documentation": self._calculate_documentation_score(results)
        }
        
        # Define weights for each category
        weights = {
            "maintainability": 0.25,
            "complexity": 0.25,
            "style": 0.2,
            "security": 0.2,
            "documentation": 0.1
        }
        
        overall_score = sum(score * weights[category] for category, score in scores.items())
        
        return {
            "overall_score": round(overall_score, 2),
            "breakdown": {
                category: f"{score:.2f}/100" for category, score in scores.items()
            },
            "category_scores": {
                category: {
                    "score": score,
                    "weight": weights[category],
                    "contribution": round(score * weights[category], 2)
                } for category, score in scores.items()
            }
        }

    def _calculate_maintainability_score(self, results: Dict[str, Any]) -> float:
        """Calculate maintainability score"""
        mi_score = results.get("metrics", {}).get("maintainability_index", 0)
        return min(100, max(0, mi_score))

    def _calculate_complexity_score(self, results: Dict[str, Any]) -> float:
        """Calculate complexity score"""
        functions = results.get("complexity", {}).get("functions", [])
        if not functions:
            return 100.0
        
        scores = []
        for func in functions:
            complexity = func.get("complexity", 0)
            if complexity <= 5:
                scores.append(100)
            elif complexity <= 10:
                scores.append(80)
            elif complexity <= 20:
                scores.append(60)
            elif complexity <= 30:
                scores.append(40)
            else:
                scores.append(20)
        
        return sum(scores) / len(scores)

    def _calculate_style_score(self, results: Dict[str, Any]) -> float:
        """Calculate style score based on linting results"""
        lint_issues = results.get("linting", [])
        if not lint_issues:
            return 100.0
        
        # Weight different types of issues
        weights = {
            "convention": 1,
            "refactor": 2,
            "warning": 3,
            "error": 5
        }
        
        total_weight = sum(weights.get(issue.get("type", "convention"), 1) for issue in lint_issues)
        base_score = 100
        penalty_per_weight = 2
        
        return max(0, base_score - (total_weight * penalty_per_weight))

    def _calculate_security_score(self, results: Dict[str, Any]) -> float:
        """Calculate security score"""
        security_issues = results.get("security", [])
        if not security_issues:
            return 100.0
        
        # Heavy penalty for security issues
        penalty_per_issue = 25
        return max(0, 100 - (len(security_issues) * penalty_per_issue))

    def _calculate_documentation_score(self, results: Dict[str, Any]) -> float:
        """Calculate documentation score"""
        raw_metrics = results.get("raw_metrics", {})
        sloc = raw_metrics.get("sloc", 0)
        comments = raw_metrics.get("comments", 0)
        
        if sloc == 0:
            return 100.0
        
        comment_ratio = (comments / sloc) * 100
        if comment_ratio >= 20:
            return 100.0
        elif comment_ratio >= 15:
            return 80.0
        elif comment_ratio >= 10:
            return 60.0
        elif comment_ratio >= 5:
            return 40.0
        else:
            return 20.0

    @staticmethod
    def _get_grade(score: float) -> str:
        """Convert numerical score to letter grade"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a high-level summary of the code analysis"""
        metrics = results.get("metrics", {})
        raw_metrics = results.get("raw_metrics", {})
        
        return {
            "maintainability_score": metrics.get("maintainability_index", 0),
            "maintainability_rank": metrics.get("rank", "?"),
            "total_lines": raw_metrics.get("loc", 0),
            "code_lines": raw_metrics.get("sloc", 0),
            "comment_lines": raw_metrics.get("comments", 0),
            "issues_count": len(results.get("linting", [])),
            "security_issues_count": len(results.get("security", [])),
        }

    def _generate_suggestions(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate actionable suggestions based on analysis results"""
        suggestions = []
        
        # Add complexity-based suggestions
        for func in results.get("complexity", {}).get("functions", []):
            if func.get("complexity", 0) > 10:
                suggestions.append({
                    "type": "complexity",
                    "severity": "warning" if func["complexity"] <= 20 else "critical",
                    "message": f"Function '{func['name']}' has high cyclomatic complexity ({func['complexity']}). "
                             f"Consider breaking it down into smaller functions.",
                    "line": func.get("lineno")
                })

        # Add maintainability suggestions
        mi_score = results.get("metrics", {}).get("maintainability_index", 0)
        if mi_score < 65:
            suggestions.append({
                "type": "maintainability",
                "severity": "warning",
                "message": "Code has low maintainability score. Consider adding more comments "
                         "and breaking down complex functions.",
                "line": None
            })

        # Add linting suggestions
        for lint_issue in results.get("linting", []):
            suggestions.append({
                "type": "style",
                "severity": "info" if lint_issue.get("type") in ["convention", "refactor"] else "warning",
                "message": lint_issue.get("message"),
                "line": lint_issue.get("line")
            })

        return suggestions

    def _analyze_security_issues(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze and format security issues"""
        security_issues = []
        
        for issue in results.get("security", []):
            security_issues.append({
                "severity": "critical",
                "message": issue.get("message"),
                "line": issue.get("line"),
                "recommendation": self._get_security_recommendation(issue)
            })
        
        return security_issues

    def _analyze_code_quality(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze overall code quality metrics"""
        raw_metrics = results.get("raw_metrics", {})
        comment_ratio = (raw_metrics.get("comments", 0) / raw_metrics.get("sloc", 1)) * 100 if raw_metrics.get("sloc", 0) > 0 else 0
        
        return {
            "comment_ratio": round(comment_ratio, 2),
            "comment_ratio_status": "good" if comment_ratio >= 20 else "needs_improvement",
            "complexity_status": self._get_overall_complexity_status(results.get("complexity", {})),
            "maintainability_status": self._get_maintainability_status(results.get("metrics", {}))
        }

    def _format_detailed_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Format detailed metrics for reporting"""
        return {
            "code_metrics": results.get("raw_metrics", {}),
            "complexity_analysis": results.get("complexity", {}),
            "maintainability": results.get("metrics", {})
        }

    @staticmethod
    def _get_security_recommendation(issue: Dict[str, Any]) -> str:
        """Get specific recommendation for security issues"""
        if "hardcoded secret" in issue.get("message", "").lower():
            return "Move sensitive data to environment variables or secure configuration management"
        elif "exec" in issue.get("message", "").lower() or "eval" in issue.get("message", "").lower():
            return "Avoid using exec/eval as they can lead to code injection vulnerabilities"
        return "Review and fix the security issue according to security best practices"

    @staticmethod
    def _get_overall_complexity_status(complexity_data: Dict[str, Any]) -> str:
        """Determine overall complexity status"""
        functions = complexity_data.get("functions", [])
        if not functions:
            return "unknown"
        
        total_complexity = sum(func.get("complexity", 0) for func in functions)
        avg_complexity = total_complexity / len(functions) if functions else 0
        
        if avg_complexity <= 5:
            return "excellent"
        elif avg_complexity <= 10:
            return "good"
        elif avg_complexity <= 20:
            return "fair"
        else:
            return "poor"

    @staticmethod
    def _get_maintainability_status(metrics: Dict[str, Any]) -> str:
        """Determine maintainability status based on maintainability index"""
        mi_score = metrics.get("maintainability_index", 0)
        
        if mi_score >= 80:
            return "excellent"
        elif mi_score >= 65:
            return "good"
        elif mi_score >= 50:
            return "fair"
        else:
            return "poor"
