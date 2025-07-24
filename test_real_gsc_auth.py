#!/usr/bin/env python3
"""Test real GSC API authentication and basic connectivity."""

import asyncio
import json
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import get_settings

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


def load_credentials():
    """Load Google API credentials."""
    settings = get_settings()
    token_path = settings.credentials_path.parent / "token.json"
    client_secret_path = settings.credentials_path

    creds = None

    # Load existing token
    if token_path.exists():
        try:
            with open(token_path) as token_file:
                token_data = json.load(token_file)
                creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        except Exception as e:
            print(f"Error loading token: {e}")

    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print("✅ Refreshed existing credentials")
            except Exception as e:
                print(f"❌ Failed to refresh credentials: {e}")
                creds = None

        if not creds:
            if not client_secret_path.exists():
                print(f"❌ Client secret file not found: {client_secret_path}")
                return None

            try:
                flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
                creds = flow.run_local_server(port=0)
                print("✅ Obtained new credentials")
            except Exception as e:
                print(f"❌ Failed to obtain credentials: {e}")
                return None

        # Save the credentials for the next run
        try:
            with open(token_path, "w") as token_file:
                token_file.write(creds.to_json())
            print("✅ Saved credentials to token.json")
        except Exception as e:
            print(f"⚠️ Failed to save credentials: {e}")

    return creds


def test_gsc_connection():
    """Test basic GSC API connection."""
    print("🔐 Testing GSC API Authentication...")

    # Load credentials
    creds = load_credentials()
    if not creds:
        print("❌ Failed to obtain valid credentials")
        return False

    try:
        # Build service
        service = build("searchconsole", "v1", credentials=creds)
        print("✅ Successfully built GSC service")

        # Test basic API call - list sites
        print("📋 Testing sites list...")
        sites_result = service.sites().list().execute()
        sites = sites_result.get("siteEntry", [])

        print(f"✅ Found {len(sites)} sites:")
        for i, site in enumerate(sites[:5]):  # Show first 5 sites
            print(f"   {i + 1}. {site['siteUrl']}")

        if len(sites) > 5:
            print(f"   ... and {len(sites) - 5} more sites")

        return True, service, sites

    except HttpError as e:
        print(f"❌ HTTP Error: {e}")
        return False, None, []
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False, None, []


def test_single_site_query(service, site_url):
    """Test a single site query to understand response format."""
    print(f"\n🔍 Testing single query for: {site_url}")

    try:
        # Simple query for recent data
        request_body = {
            "startDate": "2025-07-23",
            "endDate": "2025-07-23",
            "dimensions": ["query"],
            "rowLimit": 5,
        }

        result = service.searchanalytics().query(siteUrl=site_url, body=request_body).execute()

        rows = result.get("rows", [])
        print(f"✅ Got {len(rows)} rows")

        if rows:
            print("📊 Sample data:")
            for i, row in enumerate(rows[:3]):
                keys = row.get("keys", [])
                clicks = row.get("clicks", 0)
                impressions = row.get("impressions", 0)
                print(
                    f"   {i + 1}. Query: {keys[0] if keys else 'N/A'}, Clicks: {clicks}, Impressions: {impressions}"
                )
        else:
            print("⚠️ No data returned - this might be normal for recent dates")

        return True, len(rows)

    except HttpError as e:
        if e.resp.status == 403:
            print("❌ Access denied - site may not be verified or no permission")
        elif e.resp.status == 400:
            print("❌ Bad request - check date range or parameters")
        else:
            print(f"❌ HTTP Error {e.resp.status}: {e}")
        return False, 0
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False, 0


async def test_concurrent_queries(service, sites, max_concurrent=3):
    """Test concurrent queries to different sites."""
    print(f"\n🔄 Testing concurrent queries to {min(len(sites), max_concurrent)} sites...")

    # Select sites to test
    test_sites = sites[:max_concurrent]

    def query_site(site_url):
        """Synchronous query function."""
        try:
            request_body = {
                "startDate": "2025-07-22",
                "endDate": "2025-07-22",
                "dimensions": ["query"],
                "rowLimit": 10,
            }

            result = service.searchanalytics().query(siteUrl=site_url, body=request_body).execute()

            rows = result.get("rows", [])
            return {"site": site_url, "success": True, "rows": len(rows), "error": None}

        except Exception as e:
            return {"site": site_url, "success": False, "rows": 0, "error": str(e)}

    # Since Google API client is not async, we'll run in executor
    import concurrent.futures
    import time

    start_time = time.time()

    # Test sequential execution
    print("   Sequential execution:")
    sequential_results = []
    for site in test_sites:
        result = query_site(site["siteUrl"])
        sequential_results.append(result)
        print(
            f"     {site['siteUrl']}: {'✅' if result['success'] else '❌'} ({result['rows']} rows)"
        )

    sequential_time = time.time() - start_time

    # Test concurrent execution
    print("   Concurrent execution:")
    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        futures = [executor.submit(query_site, site["siteUrl"]) for site in test_sites]
        concurrent_results = [
            future.result() for future in concurrent.futures.as_completed(futures)
        ]

    concurrent_time = time.time() - start_time

    for result in concurrent_results:
        print(
            f"     {result['site']}: {'✅' if result['success'] else '❌'} ({result['rows']} rows)"
        )

    # Analysis
    print("\n⚡ Performance Analysis:")
    print(f"   Sequential time: {sequential_time:.2f}s")
    print(f"   Concurrent time: {concurrent_time:.2f}s")

    if concurrent_time > 0:
        speedup = sequential_time / concurrent_time
        print(f"   Speedup: {speedup:.2f}x")

        if speedup > 1.5:
            print("   ✅ Concurrent execution provides significant benefit")
        else:
            print("   ⚖️ Limited benefit from concurrent execution")

    # Error analysis
    sequential_errors = sum(1 for r in sequential_results if not r["success"])
    concurrent_errors = sum(1 for r in concurrent_results if not r["success"])

    print(f"   Sequential errors: {sequential_errors}/{len(sequential_results)}")
    print(f"   Concurrent errors: {concurrent_errors}/{len(concurrent_results)}")

    if concurrent_errors > sequential_errors:
        print("   ⚠️ Concurrent execution has more errors - API may not support concurrency")
    else:
        print("   ✅ No additional errors from concurrent execution")


def main():
    """Main test function."""
    print("🚀 Real GSC API Concurrency Test")
    print("=" * 60)

    # Test basic connection
    success, service, sites = test_gsc_connection()

    if not success or not sites:
        print("❌ Cannot proceed without valid GSC connection")
        return

    # Test single site query
    test_site = sites[0]["siteUrl"]
    query_success, rows = test_single_site_query(service, test_site)

    if not query_success:
        print("❌ Single query failed - cannot test concurrency")
        return

    # Test concurrent queries
    if len(sites) >= 2:
        asyncio.run(test_concurrent_queries(service, sites, max_concurrent=min(3, len(sites))))
    else:
        print("⚠️ Need at least 2 sites to test concurrency")

    print("\n" + "=" * 60)
    print("💡 Conclusions:")
    print("   - GSC API authentication: ✅ Working")
    print("   - Basic queries: ✅ Working")

    if len(sites) >= 2:
        print("   - Concurrent access: Test completed (see results above)")
        print("   - Recommendation: Use results above to determine best sync strategy")

    print("=" * 60)


if __name__ == "__main__":
    main()
