import click
import requests
import os
import json
from typing import Optional

@click.group()
def cli():
    """CLI tool for PR Review Agent"""
    pass

@cli.command()
@click.option('--repo', required=True, help='Repository name (owner/repo)')
@click.option('--pr', required=True, type=int, help='PR number')
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub token')
@click.option('--server', default='http://localhost:8000', help='PR Review Agent server URL')
def review(repo: str, pr: int, token: Optional[str], server: str):
    """Run a PR review"""
    if not token:
        click.echo("Error: GitHub token not provided. Set GITHUB_TOKEN environment variable or use --token")
        return

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    try:
        # First authenticate
        auth_response = requests.post(
            f"{server}/login",
            headers=headers,
            json={'client_id': 'cli_client', 'client_secret': token}
        )
        auth_response.raise_for_status()

        # Then request the review
        response = requests.post(
            f"{server}/review",
            headers=headers,
            json={
                'repo_name': repo,
                'pr_number': pr,
                'context': {'source': 'cli'}
            }
        )
        response.raise_for_status()

        # Pretty print the results
        result = response.json()
        click.echo("\n=== PR Review Results ===\n")
        click.echo(f"Repository: {result['repo_name']}")
        click.echo(f"PR Number: {result['pr_number']}")
        click.echo(f"Files Analyzed: {result['files_analyzed']}")
        click.echo(f"Overall Score: {result['overall_score']['score']} ({result['overall_score']['grade']})")
        
        click.echo("\n=== File Reviews ===\n")
        for file_review in result['file_reviews']:
            click.echo(f"\nFile: {file_review['file']}")
            click.echo(f"Language: {file_review['language']}")
            click.echo("\nIssues:")
            
            if 'feedback' in file_review and 'issues' in file_review['feedback']:
                for issue in file_review['feedback']['issues']:
                    click.echo(f"- [{issue['severity']}] {issue['message']}")
                    if 'suggestion' in issue:
                        click.echo(f"  Suggestion: {issue['suggestion']}")
            click.echo("-" * 50)

    except requests.exceptions.RequestException as e:
        click.echo(f"Error: {str(e)}")
        return

@cli.command()
@click.option('--repo', required=True, help='Repository name (owner/repo)')
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub token')
@click.option('--server', default='http://localhost:8000', help='PR Review Agent server URL')
def list_prs(repo: str, token: Optional[str], server: str):
    """List open pull requests"""
    if not token:
        click.echo("Error: GitHub token not provided. Set GITHUB_TOKEN environment variable or use --token")
        return

    try:
        response = requests.get(
            f"{server}/prs",
            headers={'Authorization': f'Bearer {token}'},
            params={'repo_name': repo}
        )
        response.raise_for_status()

        prs = response.json()['pull_requests']
        click.echo(f"\nOpen Pull Requests for {repo}:\n")
        for pr in prs:
            click.echo(f"#{pr['number']} - {pr['title']}")

    except requests.exceptions.RequestException as e:
        click.echo(f"Error: {str(e)}")
        return

if __name__ == '__main__':
    cli()