from typing import Dict, List
from .base import GitClient
import base64

class BitbucketClient(GitClient):
    """
    Bitbucket-specific implementation of GitClient
    """
    def __init__(self, token: str):
        super().__init__(token, api_url="https://api.bitbucket.org/2.0")

    def get_auth_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }

    async def get_repositories(self) -> List[Dict]:
        """Get list of repositories for the authenticated user"""
        response = await self._make_request("GET", f"{self.api_url}/repositories")
        return response['values']

    async def get_pull_requests(self, repo_name: str) -> List[Dict]:
        """Get list of pull requests for a repository"""
        url = f"{self.api_url}/repositories/{repo_name}/pullrequests"
        response = await self._make_request("GET", url)
        
        # Convert Bitbucket format to match GitHub format
        return [{
            "number": pr['id'],
            "title": pr['title'],
            "state": "open" if pr['state'] == "OPEN" else "closed",
            "html_url": pr['links']['html']['href']
        } for pr in response['values']]

    async def get_pr_files(self, repo_name: str, pr_number: int) -> Dict[str, str]:
        """Get files changed in a pull request"""
        url = f"{self.api_url}/repositories/{repo_name}/pullrequests/{pr_number}/diffstat"
        response = await self._make_request("GET", url)
        
        result = {}
        for file_change in response['values']:
            if file_change['status'] != 'removed':
                file_url = f"{self.api_url}/repositories/{repo_name}/src/{await self._get_head_commit(repo_name, pr_number)}/{file_change['new']['path']}"
                content = await self._make_request("GET", file_url)
                result[file_change['new']['path']] = content
                
        return result

    async def create_review(self, repo: str, pr_number: int, comments: List[Dict], event: str, body: str):
        """Create a review with comments on a pull request"""
        # Post general comment
        await self._make_request(
            "POST",
            f"{self.api_url}/repositories/{repo}/pullrequests/{pr_number}/comments",
            json={"content": {"raw": body}}
        )
        
        # Post individual comments
        for comment in comments:
            await self._make_request(
                "POST",
                f"{self.api_url}/repositories/{repo}/pullrequests/{pr_number}/comments",
                json={
                    "content": {"raw": comment['body']},
                    "inline": {
                        "path": comment['path'],
                        "to": comment['line']
                    }
                }
            )

    async def create_commit_status(self, repo: str, sha: str, state: str, description: str, context: str):
        """Create a commit status"""
        # Convert GitHub state to Bitbucket state
        state_map = {
            "success": "SUCCESSFUL",
            "failure": "FAILED",
            "pending": "INPROGRESS",
            "error": "FAILED"
        }
        
        await self._make_request(
            "POST",
            f"{self.api_url}/repositories/{repo}/commit/{sha}/statuses/build",
            json={
                "state": state_map[state],
                "description": description,
                "key": context,
                "name": context
            }
        )

    async def _get_head_commit(self, repo: str, pr_number: int) -> str:
        """Get the head commit hash for a pull request"""
        pr_data = await self._make_request(
            "GET",
            f"{self.api_url}/repositories/{repo}/pullrequests/{pr_number}"
        )
        return pr_data['source']['commit']['hash']

    def get_provider_name(self) -> str:
        return "bitbucket"