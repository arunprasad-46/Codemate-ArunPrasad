from typing import Optional
from .github import GitHubClient
from .gitlab import GitLabClient
from .bitbucket import BitbucketClient
from .base import GitClient

class GitClientFactory:
    """
    Factory class to create appropriate git client based on provider
    """
    @staticmethod
    def create_client(provider: str, token: str, **kwargs) -> GitClient:
        """
        Create a git client instance based on the provider
        
        Args:
            provider: The git provider ('github', 'gitlab', or 'bitbucket')
            token: Authentication token
            **kwargs: Additional provider-specific arguments
        
        Returns:
            GitClient: An instance of the appropriate git client
        
        Raises:
            ValueError: If the provider is not supported
        """
        if provider == "github":
            return GitHubClient(token)
        elif provider == "gitlab":
            gitlab_url = kwargs.get('gitlab_url', 'https://gitlab.com')
            return GitLabClient(token, gitlab_url)
        elif provider == "bitbucket":
            return BitbucketClient(token)
        else:
            raise ValueError(f"Unsupported git provider: {provider}")