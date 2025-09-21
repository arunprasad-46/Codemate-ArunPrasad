from typing import Dict, Optional, Tuple
import re
import urllib.parse

class GitProviderDetector:
    """
    Utility class to detect git provider from repository URL or token format
    """
    
    @staticmethod
    def detect_from_url(url: str) -> Tuple[str, Optional[str]]:
        """
        Detect git provider from URL
        Returns: (provider_name, provider_url)
        """
        # Clean and parse the URL
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.netloc.lower()

        # GitHub detection
        if hostname in ['github.com', 'www.github.com']:
            return 'github', None
        
        # GitLab detection
        if hostname in ['gitlab.com', 'www.gitlab.com']:
            return 'gitlab', None
        elif '.gitlab.' in hostname:  # Self-hosted GitLab
            return 'gitlab', f"https://{hostname}"
        
        # Bitbucket detection
        if hostname in ['bitbucket.org', 'www.bitbucket.org']:
            return 'bitbucket', None
        
        # Check for self-hosted instances
        if any(keyword in hostname for keyword in ['gitlab', 'github', 'bitbucket']):
            if 'gitlab' in hostname:
                return 'gitlab', f"https://{hostname}"
            elif 'github' in hostname:
                return 'github', f"https://{hostname}"
            elif 'bitbucket' in hostname:
                return 'bitbucket', f"https://{hostname}"
        
        return 'unknown', None

    @staticmethod
    def detect_from_token(token: str) -> str:
        """
        Detect git provider from token format
        """
        # GitLab private token format (usually 20 chars)
        if re.match(r'^[a-zA-Z0-9_-]{20}$', token):
            return 'gitlab'
        
        # GitHub token format (40 chars, hex)
        if re.match(r'^gh[ps]_[A-Za-z0-9_]{36}$', token):
            return 'github'
        
        # Bitbucket token format
        if token.startswith('BITBUCKET_'):
            return 'bitbucket'
        
        return 'unknown'

    @staticmethod
    def detect_from_api_url(api_url: str) -> Tuple[str, Optional[str]]:
        """
        Detect git provider from API URL
        """
        parsed = urllib.parse.urlparse(api_url)
        hostname = parsed.netloc.lower()
        path = parsed.path.lower()

        if 'api.github.com' in hostname:
            return 'github', None
        elif 'gitlab' in hostname or '/api/v4' in path:
            return 'gitlab', f"https://{hostname}"
        elif 'bitbucket' in hostname or '/rest/api' in path:
            return 'bitbucket', f"https://{hostname}"
        
        return 'unknown', None

    @staticmethod
    def validate_provider(detected_provider: str, repo_url: str) -> bool:
        """
        Validate if detected provider matches the repository URL
        """
        url_provider, _ = GitProviderDetector.detect_from_url(repo_url)
        return detected_provider == url_provider or url_provider == 'unknown'