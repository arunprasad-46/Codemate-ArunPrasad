from typing import Dict, List
import jwt
import time
import aiohttp
from datetime import datetime, timedelta

async def get_installation_token(installation_id: int) -> str:
    """
    Get an installation access token for a GitHub App installation
    """
    # Load the private key from environment or config
    private_key = os.getenv('GITHUB_APP_PRIVATE_KEY')
    app_id = os.getenv('GITHUB_APP_ID')
    
    if not private_key or not app_id:
        raise ValueError("GitHub App credentials not configured")
    
    # Generate JWT for GitHub App
    now = int(time.time())
    payload = {
        'iat': now,
        'exp': now + (10 * 60),  # 10 minutes expiration
        'iss': app_id
    }
    
    jwt_token = jwt.encode(payload, private_key, algorithm='RS256')
    
    # Get installation token
    async with aiohttp.ClientSession() as session:
        headers = {
            'Authorization': f'Bearer {jwt_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        async with session.post(
            f'https://api.github.com/app/installations/{installation_id}/access_tokens',
            headers=headers
        ) as response:
            if response.status == 201:
                data = await response.json()
                return data['token']
            else:
                raise Exception(f"Failed to get installation token: {await response.text()}")

async def post_review_comments(client: 'GitHubClient', repo: str, pr_number: int, file_reviews: List[Dict]):
    """
    Post inline review comments on GitHub PR.
    """
    comments = []

    for review in file_reviews:
        file_path = review['file']
        if 'feedback' in review and 'issues' in review['feedback']:
            for issue in review['feedback']['issues']:
                if issue.get('line_number'):
                    comments.append({
                        'path': file_path,
                        'line': issue['line_number'],
                        'body': f"**{issue['type']}**: {issue['message']}\n\n💡 Suggestion: {issue.get('suggestion', 'No suggestion available')}"
                    })

    if comments:
        try:
            # Group comments by file
            grouped_comments = {}
            for comment in comments:
                if comment['path'] not in grouped_comments:
                    grouped_comments[comment['path']] = []
                grouped_comments[comment['path']].append(comment)

            # Create review with comments
            await client.create_review(
                repo=repo,
                pr_number=pr_number,
                comments=comments,
                event='COMMENT',
                body="## PR Review Results\n\n" + \
                     "I've reviewed your pull request and here are my findings:\n\n" + \
                     generate_review_summary(file_reviews)
            )
        except Exception as e:
            logger.error(f"Failed to post review comments: {str(e)}")
            raise

def generate_review_summary(file_reviews: List[Dict]) -> str:
    """
    Generate a markdown summary of the review
    """
    summary = []
    total_issues = 0
    critical_issues = 0
    
    for review in file_reviews:
        if 'feedback' in review and 'issues' in review['feedback']:
            file_issues = len(review['feedback']['issues'])
            critical = sum(1 for i in review['feedback']['issues'] if i.get('severity') == 'critical')
            
            if file_issues > 0:
                summary.append(f"### {review['file']}")
                summary.append(f"- Found {file_issues} issue(s)")
                if critical > 0:
                    summary.append(f"- ❗ {critical} critical issue(s)")
                summary.append("")
            
            total_issues += file_issues
            critical_issues += critical
    
    if total_issues > 0:
        header = f"Found {total_issues} total issue(s)"
        if critical_issues > 0:
            header += f", including {critical_issues} critical issue(s)"
        summary.insert(0, header + "\n")
    else:
        summary.insert(0, "✅ No issues found! Great job!\n")
    
    return "\n".join(summary)