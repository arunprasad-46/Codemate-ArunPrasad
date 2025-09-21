import requests
import time
from github import Github

# ---------------- Device Flow ----------------
def get_device_code(client_id):
    url = "https://github.com/login/device/code"
    data = {
        "client_id": client_id,
        "scope": "repo"
    }
    headers = {"Accept": "application/json"}
    
    resp = requests.post(url, data=data, headers=headers)
    
    # Check response content first
    if resp.status_code != 200:
        raise Exception(f"GitHub API returned {resp.status_code}: {resp.text}")
    
    try:
        return resp.json()
    except Exception as e:
        raise Exception(f"Error parsing JSON from GitHub API: {resp.text}") from e
def get_access_token(client_id, client_secret, device_code):
    url = "https://github.com/login/oauth/access_token"
    headers = {"Accept": "application/json"}
    
    while True:
        data = {
            "client_id": client_id,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_secret": client_secret
        }
        resp = requests.post(url, data=data, headers=headers).json()
        if "access_token" in resp:
            return resp["access_token"]
        elif resp.get("error") == "authorization_pending":
            time.sleep(5)  # wait and poll again
        else:
            return resp  # error
        

# ---------------- GitHub API helpers ----------------
def list_repositories(access_token):
    g = Github(access_token)
    return g.get_user().get_repos()

def list_pull_requests(repo):
    return repo.get_pulls(state="open")
