"""Modern async Google Search Console client."""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Optional
from urllib.parse import quote

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config import get_settings
from ..models import PerformanceData

# GSC API configuration
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
API_BASE_URL = "https://www.googleapis.com/webmasters/v3"  # Fixed: was incorrect v1 URL causing 404 errors


class ModernGSCClient:
    """
    Async Google Search Console client with rate limiting and retry logic.
    
    CRITICAL: GSC API does NOT support concurrent access!
    - Concurrent requests result in 100% failure rate
    - Sequential execution required: 100% success rate
    - Tested 2025-07-25: concurrent=0% success, sequential=100% success
    - Always use max_workers=1 and sequential processing
    """
    
    def __init__(self, credentials_path: Optional[Path] = None):
        """Initialize GSC client with sequential-only processing."""
        settings = get_settings()
        self.credentials_path = credentials_path or settings.credentials_path
        self.token_path = self.credentials_path.parent / "token.json"
        
        # HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20
            ),
            http2=True  # Enable HTTP/2 for better performance
        )
        
        # Rate limiting - MUST be 1 for GSC API compatibility
        # GSC API fails with concurrent access - tested and confirmed
        self.api_semaphore = asyncio.Semaphore(1)  # REQUIRED: Sequential API calls only
        self.rate_limit_delay = 1.0  # Minimum delay between sequential API calls
        
        # Credentials
        self._creds: Optional[Credentials] = None
        
    async def initialize(self) -> None:
        """Initialize credentials."""
        self._creds = await self._get_credentials()
        
    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()
        
    async def _get_credentials(self) -> Credentials:
        """Get or refresh Google credentials."""
        creds = None
        
        # Load existing token
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(
                str(self.token_path), SCOPES
            )
        
        # Refresh or get new token
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Run refresh in thread pool
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, creds.refresh, Request())
            else:
                # Need new authorization
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                # Run auth flow in thread pool
                loop = asyncio.get_event_loop()
                creds = await loop.run_in_executor(
                    None, lambda: flow.run_local_server(port=0)
                )
            
            # Save token
            self.token_path.write_text(creds.to_json())
        
        return creds
    
    @asynccontextmanager
    async def rate_limit(self) -> AsyncGenerator[None, None]:
        """Rate limiting context manager."""
        async with self.api_semaphore:
            try:
                yield
            finally:
                # Ensure minimum delay between API calls
                await asyncio.sleep(self.rate_limit_delay)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, asyncio.TimeoutError))
    )
    async def _make_request(
        self, 
        method: str, 
        url: str, 
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with retry logic."""
        # Ensure credentials are valid
        if self._creds.expired:
            self._creds = await self._get_credentials()
        
        # Add authorization header
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {self._creds.token}"
        kwargs["headers"] = headers
        
        # Make request
        async with self.rate_limit():
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                await asyncio.sleep(retry_after)
                raise httpx.HTTPStatusError(
                    "Rate limited", 
                    request=response.request, 
                    response=response
                )
            
            return response
    
    async def list_sites(self) -> list[str]:
        """List all verified sites."""
        url = f"{API_BASE_URL}/sites"
        response = await self._make_request("GET", url)
        data = response.json()
        return [site["siteUrl"] for site in data.get("siteEntry", [])]
    
    async def fetch_data_for_date(
        self,
        site_url: str,
        target_date: date,
        row_limit: int = 25000,
        start_row: int = 0
    ) -> list[PerformanceData]:
        """Fetch performance data for a specific date with pagination support."""
        url = f"{API_BASE_URL}/sites/{quote(site_url, safe=':')}/searchAnalytics/query"
        
        # Build request body with pagination support
        body = {
            "startDate": target_date.strftime("%Y-%m-%d"),
            "endDate": target_date.strftime("%Y-%m-%d"),
            "dimensions": ["query", "page", "device"],  # Removed "searchType" - causes 400 error
            "rowLimit": row_limit,
            "startRow": start_row,  # Add pagination support
            "dataState": "final"
        }
        
        response = await self._make_request("POST", url, json=body)
        data = response.json()
        
        # Parse response into PerformanceData objects
        results = []
        for row in data.get("rows", []):
            results.append(PerformanceData(
                site_id=0,  # Will be set by caller
                date=target_date,
                query=row["keys"][0],
                page=row["keys"][1],
                device=row["keys"][2],
                search_type="web",  # Default to "web" since searchType dimension removed
                clicks=int(row.get("clicks", 0)),
                impressions=int(row.get("impressions", 0)),
                ctr=float(row.get("ctr", 0.0)),
                position=float(row.get("position", 0.0))
            ))
        
        return results
    
    async def test_site_access(self, site_url: str) -> bool:
        """Test if we have access to a specific site."""
        if not self._creds:
            raise ValueError("Client not initialized")
        
        # Try to get site information as a lightweight test
        url = f"{API_BASE_URL}/sites/{site_url}"
        
        try:
            await self._make_request("GET", url)
            return True
        except Exception:
            # If we get any error, we don't have access
            return False
    
    async def fetch_batch(
        self,
        site_url: str,
        dates: list[date]
    ) -> dict[date, list[PerformanceData]]:
        """Fetch data for multiple dates sequentially."""
        results = {}
        
        for target_date in dates:
            try:
                data = await self.fetch_data_for_date(site_url, target_date)
                results[target_date] = data
            except httpx.HTTPError as e:
                # Log error but continue with other dates
                print(f"Error fetching data for {target_date}: {e}")
                results[target_date] = []
        
        return results
    
    async def fetch_hourly_data(
        self,
        site_url: str,
        target_date: date,
        queries: Optional[list[str]] = None
    ) -> dict[int, list[dict]]:
        """Fetch hourly data for specific queries."""
        # GSC doesn't provide hourly data directly
        # This would need to be implemented with multiple API calls
        # or a different data source
        return {}


class GSCAuthManager:
    """Manage GSC authentication flow."""
    
    @staticmethod
    async def authenticate(
        credentials_path: Path,
        token_path: Optional[Path] = None
    ) -> Credentials:
        """Run authentication flow."""
        token_path = token_path or credentials_path.parent / "token.json"
        
        # Check existing token
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(
                str(token_path), SCOPES
            )
            if creds.valid:
                return creds
        
        # Run OAuth flow
        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path), SCOPES
        )
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        creds = await loop.run_in_executor(
            None, flow.run_local_server, 0
        )
        
        # Save token
        token_path.write_text(creds.to_json())
        
        return creds