from typing import Dict, List
from .base import GitClient
import urllib.parse

class GitHubClient(GitClient):
    """
    GitHub-specific implementation of GitClient
    """
    def __init__(self, token: str):
        super().__init__(token, api_url="https://api.github.com")

    def get_auth_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }

    async def get_repositories(self) -> List[Dict]:
        """Get list of repositories for the authenticated user"""
        return await self._make_request("GET", f"{self.api_url}/user/repos")

    async def get_pull_requests(self, repo_name: str) -> List[Dict]:
        """Get list of pull requests for a repository"""
        url = f"{self.api_url}/repos/{repo_name}/pulls"
        return await self._make_request("GET", url)

    async def get_pr_files(self, repo_name: str, pr_number: int) -> Dict[str, str]:
        """Get files changed in a pull request"""
        url = f"{self.api_url}/repos/{repo_name}/pulls/{pr_number}/files"
        files_data = await self._make_request("GET", url)
        
        result = {}
        for file_data in files_data:
            if file_data['status'] != 'removed':
                content_url = file_data['raw_url']
                content = await self._make_request("GET", content_url)
                result[file_data['filename']] = content
        
        return result

    async def create_review(self, repo: str, pr_number: int, comments: List[Dict], event: str, body: str):
        """Create a review with comments on a pull request"""
        url = f"{self.api_url}/repos/{repo}/pulls/{pr_number}/reviews"
        
        data = {
            "commit_id": await self._get_latest_commit_sha(repo, pr_number),
            "body": body,
            "event": event,
            "comments": comments
        }
        
        await self._make_request("POST", url, json=data)

    async def create_commit_status(self, repo: str, sha: str, state: str, description: str, context: str):
        """Create a commit status"""
        url = f"{self.api_url}/repos/{repo}/statuses/{sha}"
        
        data = {
            "state": state,
            "description": description,
            "context": context
        }
        
        await self._make_request("POST", url, json=data)

    async def _get_latest_commit_sha(self, repo: str, pr_number: int) -> str:
        """Get the latest commit SHA for a pull request"""
        url = f"{self.api_url}/repos/{repo}/pulls/{pr_number}"
        pr_data = await self._make_request("GET", url)
        return pr_data['head']['sha']

    def get_provider_name(self) -> str:
        return "github"