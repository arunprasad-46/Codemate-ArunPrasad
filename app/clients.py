from .github_utils import get_device_code, get_access_token, list_repositories, list_pull_requests
from typing import List, Dict

class GitServerClient:
    """Base class for any git server"""
    def get_repositories(self):
        raise NotImplementedError

    def get_pull_requests(self, repo_name: str):
        raise NotImplementedError

    def get_pr_files(self, repo_name: str, pr_number: int):
        raise NotImplementedError


class GitHubClient(GitServerClient):
    def __init__(self, access_token: str):
        from github import Github
        self.client = Github(access_token)

    def get_repositories(self):
        return self.client.get_user().get_repos()

    def get_pull_requests(self, repo_name: str):
        try:
            repo = self.client.get_repo(repo_name)
            # Get all PRs including their details
            prs = repo.get_pulls(state='all', sort='created', direction='desc')
            return list(prs)  # Convert PaginatedList to list for easier handling
        except Exception as e:
            print(f"Error fetching PRs for {repo_name}: {str(e)}")
            return []

    def get_pr_files(self, repo_name: str, pr_number: int):
        try:
            repo = self.client.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            files_content = {}
            
            for file in pr.get_files():
                if file.status != 'removed':  # Skip deleted files
                    try:
                        # Get file content
                        content = repo.get_contents(file.filename, ref=pr.head.sha)
                        files_content[file.filename] = content.decoded_content.decode('utf-8')
                    except Exception as e:
                        print(f"Error fetching content for {file.filename}: {str(e)}")
                        files_content[file.filename] = ""
            
            return files_content
        except Exception as e:
            raise Exception(f"Error fetching PR files: {str(e)}")
