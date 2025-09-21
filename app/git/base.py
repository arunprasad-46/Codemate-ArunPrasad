from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import aiohttp
import json

class GitClient(ABC):
    """
    Abstract base class for git provider clients
    """
    def __init__(self, token: str, api_url: str):
        self.token = token
        self.api_url = api_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    @abstractmethod
    async def get_repositories(self) -> List[Dict]:
        """Get list of repositories"""
        pass

    @abstractmethod
    async def get_pull_requests(self, repo_name: str) -> List[Dict]:
        """Get list of pull requests for a repository"""
        pass

    @abstractmethod
    async def get_pr_files(self, repo_name: str, pr_number: int) -> Dict[str, str]:
        """Get files changed in a pull request"""
        pass

    @abstractmethod
    async def create_review(self, repo: str, pr_number: int, comments: List[Dict], event: str, body: str):
        """Create a review with comments on a pull request"""
        pass

    @abstractmethod
    async def create_commit_status(self, repo: str, sha: str, state: str, description: str, context: str):
        """Create a commit status"""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of the git provider"""
        pass

    async def _make_request(self, method: str, url: str, **kwargs) -> Dict:
        """Make an HTTP request to the git provider API"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        headers = kwargs.pop('headers', {})
        headers.update(self.get_auth_headers())

        async with self.session.request(method, url, headers=headers, **kwargs) as response:
            response.raise_for_status()
            return await response.json()

    @abstractmethod
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for the git provider"""
        pass