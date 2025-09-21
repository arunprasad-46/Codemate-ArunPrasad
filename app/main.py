from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from typing import Dict, List, Optional
import logging
import os
from .github_review import get_installation_token, post_review_comments
from .git.base import GitClient
from .git.factory import GitClientFactory
from .git.factory import GitClientFactory
from .analyzer import CodeAnalyzer
from .feedback import FeedbackGenerator
from .ai_feedback import AIFeedbackGenerator
from .auth.github_auth import get_device_code, get_access_token
import asyncio
import threading
import time
import asyncio

app = FastAPI(title="PR Review Agent API")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming {request.method} request to {request.url}")
    try:
        response = await call_next(request)
        logger.info(f"Request completed with status code: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Request failed: {str(e)}")
        raise

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# -------------------- Helper Functions --------------------
def calculate_pr_score(analysis_results: List[Dict]) -> Dict:
    """Calculate overall PR score based on multiple metrics"""
    if not analysis_results:
        return {
            "score": 0,
            "grade": "N/A",
            "metrics": {}
        }
    
    # Initialize metric scores
    metrics = {
        "code_quality": 0,
        "complexity": 0,
        "test_coverage": 0,
        "security": 0,
        "style": 0
    }
    
    file_count = len(analysis_results)
    
    for result in analysis_results:
        if "feedback" not in result:
            continue
            
        feedback = result["feedback"]
        
        # Code Quality (based on linter findings)
        if "code_quality" in feedback:
            metrics["code_quality"] += feedback["code_quality"].get("score", 0)
            
        # Complexity
        if "complexity" in feedback:
            metrics["complexity"] += feedback["complexity"].get("score", 0)
            
        # Security
        if "security" in feedback:
            metrics["security"] += feedback["security"].get("score", 0)
            
        # Style (based on style guide adherence)
        if "style" in feedback:
            metrics["style"] += feedback["style"].get("score", 0)
    
    # Average out the scores
    for metric in metrics:
        metrics[metric] = round(metrics[metric] / file_count, 2)
    
    # Calculate weighted average for overall score
    weights = {
        "code_quality": 0.3,
        "complexity": 0.2,
        "security": 0.3,
        "style": 0.2
    }
    
    overall_score = sum(metrics[m] * weights[m] for m in weights.keys())
    
    return {
        "score": round(overall_score, 2),
        "grade": get_grade(overall_score),
        "metrics": metrics,
        "weights": weights
    }

def get_grade(score: float) -> str:
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

# -------------------- Models --------------------
class LoginRequest(BaseModel):
    client_id: str
    client_secret: str
    provider: str = "github"  # Default to github
    provider_url: Optional[str] = None  # For custom installations like GitLab/Enterprise
    scopes: Optional[List[str]] = None  # Optional scopes for authorization

class RepoRequest(BaseModel):
    repo_name: str = None  # Optional, if you want to fetch PRs immediately

class PRRequest(BaseModel):
    repo_name: str
    pr_number: int
    context: Optional[Dict] = None  # Additional context for the review

class FileReviewRequest(BaseModel):
    content: str
    filename: str
    review_type: str = "full"  # full, quick, security-focus

class ReviewResponse(BaseModel):
    score: float
    grade: str
    analysis: Dict
    feedback: Dict
    review_type: str

class ReviewSettings(BaseModel):
    style_guide: Optional[Dict] = None  # Custom style guide settings
    severity_threshold: Optional[str] = "warning"  # warning, error, critical
    focus_areas: Optional[List[str]] = None  # security, performance, maintainability

# -------------------- In-memory token store --------------------
access_tokens: Dict[str, Dict[str, str]] = {}  # key: client_id, value: {token, provider, provider_url}

# -------------------- Background function to fetch token --------------------
async def fetch_token_async(client_id: str, client_secret: str, device_code: str, interval: int, provider: str = "github", provider_url: Optional[str] = None):
    max_attempts = 30  # 5 minutes with 10-second interval
    attempt = 0
    
    while attempt < max_attempts:
        try:
            logger.info(f"Attempting to fetch token for client_id: {client_id}")
            token = await get_access_token(client_id, client_secret, device_code)
            
            if token:
                logger.info(f"Successfully obtained token for client_id: {client_id}")
                access_tokens[client_id] = {
                    "token": token,
                    "provider": provider,
                    "provider_url": provider_url,
                    "timestamp": time.time()
                }
                return
            
            logger.info("Token not yet available, waiting for user authorization...")
            
        except Exception as e:
            logger.error(f"Error fetching token: {str(e)}")
        
        await asyncio.sleep(interval)
        attempt += 1
    
    logger.error(f"Token fetch timeout for client_id: {client_id}")
    # Remove the client_id from tokens if it exists
    access_tokens.pop(client_id, None)

# -------------------- Routes --------------------


async def update_commit_status(client: 'GitClient', repo: str, sha: str, state: str, description: str, context: str = "PR Review"):
    """Update commit status on GitHub"""
    try:
        await client.create_commit_status(
            repo=repo,
            sha=sha,
            state=state,
            description=description,
            context=context
        )
    except Exception as e:
        logger.error(f"Failed to update commit status: {str(e)}")

@app.post("/login")
async def login(request: LoginRequest):
    """
    Handles the login process for different git providers
    """
    logger.info(f"Login request received for client_id: {request.client_id}, provider: {request.provider}")
    
    try:
        provider = request.provider.lower()
        
        if provider == "github":
            # GitHub uses device flow
            logger.info("Getting GitHub device code...")
            try:
                device_info = await get_device_code(request.client_id)
                
                # Validate response
                required_fields = ["device_code", "user_code", "verification_uri", "expires_in", "interval"]
                if not all(field in device_info for field in required_fields):
                    raise ValueError("Invalid device code response")
                
                # Start background token fetch
                background_tasks = BackgroundTasks()
                background_tasks.add_task(
                    fetch_token_async,
                    request.client_id,
                    request.client_secret,
                    device_info['device_code'],
                    device_info['interval'],
                    provider,
                    request.provider_url
                )
                
                return {
                    "status": "pending_authorization",
                    "auth_type": "device_flow",
                    "verification_uri": device_info["verification_uri"],
                    "user_code": device_info["user_code"],
                    "expires_in": device_info["expires_in"],
                    "interval": device_info["interval"],
                    "message": f"Please visit {device_info['verification_uri']} and enter code: {device_info['user_code']}",
                    "provider": provider
                }
            except Exception as e:
                logger.error(f"Error in GitHub authentication: {str(e)}")
                raise HTTPException(status_code=400, detail=str(e))
                
        elif provider == "gitlab":
            # GitLab uses direct token authentication
            try:
                # Clean up and validate the token
                token = request.client_secret.strip()
                
                # Validate token format
                if not token:
                    raise ValueError("Token cannot be empty")
                
                # Validate token format based on type
                if token.startswith(('glpat-', 'gloas-')):
                    # Modern token format - validate length
                    if len(token) < 20:
                        raise ValueError("GitLab token is too short")
                else:
                    # Legacy token format - just check minimum length
                    if len(token) < 20:
                        raise ValueError("Invalid GitLab token format")

                # Set up GitLab API URL
                gitlab_url = request.provider_url or "https://gitlab.com"
                # Ensure URL doesn't end with a slash
                gitlab_url = gitlab_url.rstrip('/')

                # Store token with all necessary info
                access_tokens[request.client_id] = {
                    "token": token,
                    "provider": provider,
                    "provider_url": gitlab_url,
                    "timestamp": time.time()
                }
                
                # Try to validate token by making a test API call
                client = GitClientFactory.create_client(
                    provider=provider,
                    token=token,
                    gitlab_url=gitlab_url
                )
                await client.get_repositories()  # Test API call
                
                return {
                    "status": "authenticated",
                    "auth_type": "token",
                    "provider": provider,
                    "provider_url": request.provider_url or "https://gitlab.com",
                    "message": "Successfully authenticated with GitLab"
                }
            except Exception as e:
                logger.error(f"Error in GitLab authentication: {str(e)}")
                # Remove invalid token
                access_tokens.pop(request.client_id, None)
                raise HTTPException(status_code=401, detail="Invalid GitLab token")
                
        elif provider == "bitbucket":
            # Bitbucket uses OAuth 2.0
            try:
                # Store token immediately for Bitbucket
                access_tokens[request.client_id] = {
                    "token": request.client_secret,  # App password or OAuth token
                    "provider": provider,
                    "provider_url": request.provider_url or "https://api.bitbucket.org/2.0",
                    "timestamp": time.time()
                }
                
                # Validate token by making a test API call
                client = GitClientFactory.create_client(
                    provider=provider,
                    token=request.client_secret
                )
                await client.get_repositories()  # Test API call
                
                return {
                    "status": "authenticated",
                    "auth_type": "oauth",
                    "provider": provider,
                    "message": "Successfully authenticated with Bitbucket"
                }
            except Exception as e:
                logger.error(f"Error in Bitbucket authentication: {str(e)}")
                # Remove invalid token
                access_tokens.pop(request.client_id, None)
                raise HTTPException(status_code=401, detail="Invalid Bitbucket token")
        else:
            # Unknown provider
            raise HTTPException(
                status_code=400,
                detail=f"Provider '{provider}' not supported. Supported providers are: github, gitlab, bitbucket"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during login process: {str(e)}"
        )


@app.post("/repos")
async def get_repos(request: RepoRequest, client_id: str):
    token = access_tokens.get(client_id)
    if not token:
        raise HTTPException(status_code=401, detail="Access token not available yet. Complete login flow.")

    try:
        token_info = access_tokens.get(client_id, {})
        client = GitClientFactory.create_client(
            provider=token_info.get('provider', 'github'),
            token=token_info['token'],
            gitlab_url=token_info.get('provider_url')
        )
        repos = await client.get_repositories()
        repo_list = []
        
        for repo in repos:
            # Get PRs for each repository
            prs = client.get_pull_requests(repo.full_name)
            pr_list = [{"number": pr.number, "title": pr.title, "state": pr.state} for pr in prs]
            
            repo_info = {
                "name": repo.name,
                "full_name": repo.full_name,
                "pull_requests": pr_list,
                "open_pr_count": len([pr for pr in pr_list if pr["state"] == "open"]),
                "total_pr_count": len(pr_list)
            }
            repo_list.append(repo_info)
            
        return {
            "repositories": repo_list,
            "total_repos": len(repo_list),
            "total_open_prs": sum(repo["open_pr_count"] for repo in repo_list)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/prs")
async def get_prs(request: RepoRequest, client_id: str):
    token = access_tokens.get(client_id)
    if not token:
        raise HTTPException(status_code=401, detail="Access token not available yet. Complete login flow.")

    try:
        token_info = access_tokens.get(client_id, {})
        client = GitClientFactory.create_client(
            provider=token_info.get('provider', 'github'),
            token=token_info['token'],
            gitlab_url=token_info.get('provider_url')
        )
        prs = await client.get_pull_requests(request.repo_name)
        return {"pull_requests": [{"number": pr.number, "title": pr.title} for pr in prs]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
@app.post("/review")
async def review_pr(request: PRRequest, client_id: str, background_tasks: BackgroundTasks):
    print(f"[DEBUG] Received review request for repo={request.repo_name}, PR={request.pr_number}, client_id={client_id}")

    token = access_tokens.get(client_id)
    if not token:
        print(f"[ERROR] No access token found for client_id={client_id}")
        raise HTTPException(status_code=401, detail="Access token not available yet. Complete login flow.")

    try:
        print("[DEBUG] Initializing Git client...")
        token_info = access_tokens.get(client_id, {})
        client = GitClientFactory.create_client(
            provider=token_info.get('provider', 'github'),
            token=token_info['token'],
            gitlab_url=token_info.get('provider_url')
        )

        print("[DEBUG] Fetching PR files...")
        files = client.get_pr_files(request.repo_name, request.pr_number)
        print(f"[DEBUG] Total files fetched from PR: {len(files)}")

        # Initialize analyzers
        print("[DEBUG] Initializing analyzers...")
        code_analyzer = CodeAnalyzer()
        feedback_gen = FeedbackGenerator()

        programming_extensions = {
            "py", "pyw", "js", "jsx", "ts", "tsx", "java",
            "cpp", "cc", "c", "h", "hpp", "go", "rb", "php", "cs"
        }

        skip_extensions = {
            "json", "csv", "yml", "yaml", "xml", "ini", "toml", "md", "txt",
            "png", "jpg", "jpeg", "gif", "pdf", "zip", "exe", "dll"
        }

        async def analyze_file(file_path: str, content: str):
            try:
                file_ext = file_path.split('.')[-1].lower() if '.' in file_path else ''
                if file_ext not in programming_extensions or file_ext in skip_extensions:
                    print(f"[INFO] Skipping non-programming file: {file_path}")
                    return None

                print(f"[DEBUG] Analyzing {file_path} (.{file_ext})...")

                lang_map = {
                    "py": "python", "pyw": "python",
                    "js": "javascript", "jsx": "javascript", "ts": "javascript", "tsx": "javascript",
                    "java": "java", "cpp": "cpp", "cc": "cpp", "c": "cpp", "h": "cpp", "hpp": "cpp",
                    "go": "go", "rb": "ruby", "php": "php", "cs": "csharp"
                }
                lang = lang_map.get(file_ext, "generic")

                # Run in threadpool to avoid blocking
                file_analysis = await asyncio.to_thread(code_analyzer.analyze_code, file_path, content, lang)
                file_feedback = await asyncio.to_thread(feedback_gen.generate_feedback, file_analysis)

                print(f"[SUCCESS] Analysis completed for {file_path}")
                return {
                    "file": file_path,
                    "language": lang,
                    "analysis": file_analysis,
                    "feedback": file_feedback
                }
            except Exception as e:
                print(f"[ERROR] Failed analyzing {file_path}: {str(e)}")
                return None

        # Run all file analyses in parallel
        tasks = [analyze_file(file_path, content) for file_path, content in files.items()]
        results = await asyncio.gather(*tasks)

        # Filter out skipped/failed files
        analysis_results = [r for r in results if r is not None]

        print("[DEBUG] Calculating overall PR score...")
        overall_score = calculate_pr_score(analysis_results)
        print(f"[DEBUG] Overall PR score calculated: {overall_score}")

        result = {
            "pr_number": request.pr_number,
            "repo_name": request.repo_name,
            "files_analyzed": len(analysis_results),
            "overall_score": overall_score,
            "file_reviews": analysis_results
        }

        print(f"[SUCCESS] Review completed for PR #{request.pr_number}")
        return result

    except Exception as e:
        print(f"[FATAL] Unexpected error during review: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))