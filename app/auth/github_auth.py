import os
import aiohttp
import json
from typing import Dict, Optional

GITHUB_OAUTH_URL = "https://github.com/login/oauth"
GITHUB_DEVICE_URL = "https://github.com/login/device/code"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"

async def get_device_code(client_id: str) -> Dict:
    """
    Get a device code from GitHub for device flow authentication
    """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    data = {
        "client_id": client_id,
        "scope": "repo read:user"  # Minimum required scopes
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                GITHUB_DEVICE_URL,
                headers=headers,
                json=data
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_data = await response.json()
                    raise Exception(f"GitHub API error: {error_data.get('message', 'Unknown error')}")
    except aiohttp.ClientError as e:
        raise Exception(f"Network error while contacting GitHub: {str(e)}")
    except Exception as e:
        raise Exception(f"Error getting device code: {str(e)}")

async def get_access_token(client_id: str, client_secret: str, device_code: str) -> Optional[str]:
    """
    Get an access token using the device code
    """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    data = {
        "client_id": client_id,
        "device_code": device_code,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "client_secret": client_secret
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                GITHUB_TOKEN_URL,
                headers=headers,
                json=data
            ) as response:
                response_data = await response.json()
                
                if response.status == 200 and "access_token" in response_data:
                    return response_data["access_token"]
                elif "error" in response_data:
                    if response_data["error"] == "authorization_pending":
                        return None  # User hasn't authorized yet
                    else:
                        raise Exception(f"GitHub OAuth error: {response_data['error_description']}")
                else:
                    raise Exception("Invalid response from GitHub")
    except aiohttp.ClientError as e:
        raise Exception(f"Network error while getting access token: {str(e)}")
    except Exception as e:
        raise Exception(f"Error getting access token: {str(e)}")

def validate_github_token(token: str) -> bool:
    """
    Validate if a GitHub token is correctly formatted
    """
    # Basic validation - GitHub tokens are 40 characters long
    if not token or not isinstance(token, str):
        return False
    return len(token) == 40 and token.isalnum()