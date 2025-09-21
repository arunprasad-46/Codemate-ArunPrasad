from typing import Dict, List
from .base import GitClient
import urllib.parse

class GitLabClient(GitClient):
    """
    GitLab-specific implementation of GitClient
    """
    def __init__(self, token: str, gitlab_url: str = "https://gitlab.com"):
        # Ensure the URL is properly formatted
        gitlab_url = gitlab_url.rstrip('/')
        api_url = f"{gitlab_url}/api/v4"
        super().__init__(token, api_url=api_url)

    def get_auth_headers(self) -> Dict[str, str]:
        # For OAuth access tokens, remove the prefix before using it
        token = self.token
        if token.startswith('gloas-'):
            token = token[6:]  # Remove 'gloas-' prefix
        elif token.startswith('glpat-'):
            token = token[6:]  # Remove 'glpat-' prefix

        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

    async def get_repositories(self) -> List[Dict]:
        """Get list of repositories for the authenticated user"""
        return await self._make_request("GET", f"{self.api_url}/projects")

    async def get_pull_requests(self, repo_name: str) -> List[Dict]:
        """Get list of merge requests for a repository"""
        encoded_repo = urllib.parse.quote(repo_name, safe='')
        url = f"{self.api_url}/projects/{encoded_repo}/merge_requests"
        mrs = await self._make_request("GET", url)
        
        # Convert GitLab format to match GitHub format
        return [{
            "number": mr['iid'],
            "title": mr['title'],
            "state": mr['state'],
            "html_url": mr['web_url']
        } for mr in mrs]

    async def get_pr_files(self, repo_name: str, pr_number: int) -> Dict[str, str]:
        """Get files changed in a merge request"""
        encoded_repo = urllib.parse.quote(repo_name, safe='')
        url = f"{self.api_url}/projects/{encoded_repo}/merge_requests/{pr_number}/changes"
        changes = await self._make_request("GET", url)
        
        result = {}
        for change in changes['changes']:
            if change['new_file'] or change['renamed_file']:
                file_url = f"{self.api_url}/projects/{encoded_repo}/repository/files/{urllib.parse.quote(change['new_path'], safe='')}/raw"
                content = await self._make_request("GET", file_url, params={"ref": changes['source_branch']})
                result[change['new_path']] = content
                
        return result

    async def create_review(self, repo: str, pr_number: int, comments: List[Dict], event: str, body: str):
        """Create a review with comments on a merge request"""
        encoded_repo = urllib.parse.quote(repo, safe='')
        
        # Post general comment
        await self._make_request(
            "POST",
            f"{self.api_url}/projects/{encoded_repo}/merge_requests/{pr_number}/notes",
            json={"body": body}
        )
        
        # Post individual comments
        for comment in comments:
            await self._make_request(
                "POST",
                f"{self.api_url}/projects/{encoded_repo}/merge_requests/{pr_number}/discussions",
                json={
                    "body": comment['body'],
                    "position": {
                        "base_sha": await self._get_base_sha(repo, pr_number),
                        "start_sha": await self._get_base_sha(repo, pr_number),
                        "head_sha": await self._get_head_sha(repo, pr_number),
                        "position_type": "text",
                        "new_path": comment['path'],
                        "new_line": comment['line']
                    }
                }
            )

    async def create_commit_status(self, repo: str, sha: str, state: str, description: str, context: str):
        """Create a commit status"""
        encoded_repo = urllib.parse.quote(repo, safe='')
        
        # Convert GitHub state to GitLab state
        state_map = {
            "success": "success",
            "failure": "failed",
            "pending": "pending",
            "error": "failed"
        }
        
        await self._make_request(
            "POST",
            f"{self.api_url}/projects/{encoded_repo}/statuses/{sha}",
            json={
                "state": state_map[state],
                "description": description,
                "name": context
            }
        )

    async def _get_base_sha(self, repo: str, pr_number: int) -> str:
        """Get the base commit SHA for a merge request"""
        encoded_repo = urllib.parse.quote(repo, safe='')
        mr_data = await self._make_request(
            "GET",
            f"{self.api_url}/projects/{encoded_repo}/merge_requests/{pr_number}"
        )
        return mr_data['diff_refs']['base_sha']

    async def _get_head_sha(self, repo: str, pr_number: int) -> str:
        """Get the head commit SHA for a merge request"""
        encoded_repo = urllib.parse.quote(repo, safe='')
        mr_data = await self._make_request(
            "GET",
            f"{self.api_url}/projects/{encoded_repo}/merge_requests/{pr_number}"
        )
        return mr_data['diff_refs']['head_sha']

    def get_provider_name(self) -> str:
        return "gitlab"