class ProviderAuthenticator:
    """
    Handles authentication for different git providers
    """
    def __init__(self, client_id: str, client_secret: str, provider_url: Optional[str] = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.provider_url = provider_url
        self.detector = GitProviderDetector()

    async def authenticate(self) -> Dict:
        """
        Authenticate with the appropriate git provider
        """
        # Detect provider from token format
        provider = self.detector.detect_from_token(self.client_secret)
        
        if provider == 'gitlab':
            return await self._authenticate_gitlab()
        elif provider == 'github':
            return await self._authenticate_github()
        elif provider == 'bitbucket':
            return await self._authenticate_bitbucket()
        else:
            raise ValueError("Unable to detect git provider")

    async def _authenticate_gitlab(self) -> Dict:
        """
        Authenticate with GitLab using private token
        """
        try:
            client = GitLabClient(self.client_secret, self.provider_url)
            # Verify token by making a test API call
            await client.get_repositories()
            return {
                "status": "authenticated",
                "provider": "gitlab",
                "provider_url": self.provider_url,
                "token": self.client_secret
            }
        except Exception as e:
            raise ValueError(f"GitLab authentication failed: {str(e)}")

    async def _authenticate_github(self) -> Dict:
        """
        Authenticate with GitHub using device flow
        """
        try:
            device_info = await get_device_code(self.client_id)
            if "error" in device_info:
                raise ValueError(f"GitHub device code error: {device_info['error_description']}")
            return {
                "status": "pending_authorization",
                "provider": "github",
                "verification_uri": device_info["verification_uri"],
                "user_code": device_info["user_code"],
                "expires_in": device_info["expires_in"],
                "interval": device_info["interval"]
            }
        except Exception as e:
            raise ValueError(f"GitHub authentication failed: {str(e)}")

    async def _authenticate_bitbucket(self) -> Dict:
        """
        Authenticate with Bitbucket using OAuth token
        """
        try:
            client = BitbucketClient(self.client_secret)
            # Verify token by making a test API call
            await client.get_repositories()
            return {
                "status": "authenticated",
                "provider": "bitbucket",
                "token": self.client_secret
            }
        except Exception as e:
            raise ValueError(f"Bitbucket authentication failed: {str(e)}")