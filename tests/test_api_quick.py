#!/usr/bin/env python3
"""Quick API contract test - Run this to verify API endpoints quickly."""

import asyncio
import json
import sys
from datetime import datetime, timedelta

import httpx


class Colors:
    """Terminal colors for output."""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


async def test_endpoint(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    params: dict = None,
    expected_status: int = 200,
    check_response: callable = None,
) -> tuple[bool, str]:
    """Test a single endpoint."""
    try:
        response = await client.request(method, path, params=params)

        # Check status code
        if response.status_code != expected_status:
            return False, f"Expected status {expected_status}, got {response.status_code}"

        # Check response format
        if check_response and response.status_code == 200:
            try:
                if response.headers.get("content-type", "").startswith("application/json"):
                    data = response.json()
                    error = check_response(data)
                    if error:
                        return False, error
                elif response.headers.get("content-type", "").startswith("text/csv"):
                    error = check_response(response.text, response.headers)
                    if error:
                        return False, error
            except Exception as e:
                return False, f"Response check failed: {e}"

        return True, "OK"
    except Exception as e:
        return False, f"Request failed: {e}"


async def run_tests(base_url: str = "http://127.0.0.1:8000"):
    """Run all API contract tests."""
    print(f"{Colors.BOLD}Running API Contract Tests{Colors.RESET}")
    print(f"Base URL: {base_url}\n")

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        tests = []

        # Test 1: Root endpoint
        def check_root(data):
            if data.get("service") != "GSC Database Manager API":
                return "Invalid service name"
            if data.get("version") != "2.0.0":
                return "Invalid version"
            if data.get("docs") != "/schema/swagger":
                return "Invalid docs path"
            return None

        tests.append(("GET /", test_endpoint(client, "GET", "/", check_response=check_root)))

        # Test 2: Health endpoint
        def check_health(data):
            if "status" not in data:
                return "Missing status field"
            if "database" not in data:
                return "Missing database field"
            if "timestamp" not in data:
                return "Missing timestamp field"
            return None

        tests.append(
            (
                "GET /api/v1/health",
                test_endpoint(client, "GET", "/api/v1/health", check_response=check_health),
            )
        )

        # Test 3: Sites list
        def check_sites(data):
            if not isinstance(data, list):
                return "Response should be a list"
            if data:  # If there are sites
                site = data[0]
                required_fields = ["id", "domain", "name", "is_active"]
                for field in required_fields:
                    if field not in site:
                        return f"Missing field: {field}"
            return None

        tests.append(
            (
                "GET /api/v1/sites",
                test_endpoint(client, "GET", "/api/v1/sites", check_response=check_sites),
            )
        )

        # Test 4: Page-keyword performance
        def check_performance(data):
            required_fields = ["data", "total_pages", "total_keywords", "generated_at"]
            for field in required_fields:
                if field not in data:
                    return f"Missing field: {field}"

            if not isinstance(data["data"], list):
                return "data field should be a list"

            if data["data"]:  # If there's data
                item = data["data"][0]
                item_fields = [
                    "url",
                    "total_clicks",
                    "total_impressions",
                    "avg_ctr",
                    "avg_position",
                    "keywords",
                    "keyword_count",
                ]
                for field in item_fields:
                    if field not in item:
                        return f"Missing field in data item: {field}"
            return None

        tests.append(
            (
                "GET /api/v1/page-keyword-performance",
                test_endpoint(
                    client,
                    "GET",
                    "/api/v1/page-keyword-performance",
                    params={"site_id": 1, "days": 7},
                    expected_status=200,  # or 404 if site doesn't exist
                    check_response=check_performance,
                ),
            )
        )

        # Test 5: CSV export
        def check_csv(content, headers):
            if not headers.get("content-type", "").startswith("text/csv"):
                return "Invalid content-type header"

            lines = content.strip().split("\n")
            if not lines:
                return "Empty CSV"

            expected_header = (
                "url,total_clicks,total_impressions,avg_ctr,avg_position,keywords,keyword_count"
            )
            if lines[0] != expected_header:
                return f"Invalid CSV header. Expected: {expected_header}, Got: {lines[0]}"

            return None

        tests.append(
            (
                "GET /api/v1/page-keyword-performance/csv",
                test_endpoint(
                    client,
                    "GET",
                    "/api/v1/page-keyword-performance/csv",
                    params={"site_id": 1, "days": 7, "max_results": 10},
                    expected_status=200,  # or 404 if site doesn't exist
                    check_response=check_csv,
                ),
            )
        )

        # Test 6: Parameter validation
        tests.append(
            (
                "GET /api/v1/page-keyword-performance (invalid params)",
                test_endpoint(
                    client,
                    "GET",
                    "/api/v1/page-keyword-performance",
                    params={"site_id": "invalid", "days": 7},
                    expected_status=400,
                ),
            )
        )

        # Test 7: Date range parameters
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        tests.append(
            (
                "GET /api/v1/page-keyword-performance (date range)",
                test_endpoint(
                    client,
                    "GET",
                    "/api/v1/page-keyword-performance",
                    params={
                        "site_id": 1,
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                    },
                    expected_status=200,  # or 404
                ),
            )
        )

        # Test 8: 404 handling
        tests.append(
            (
                "GET /api/v1/nonexistent (404)",
                test_endpoint(client, "GET", "/api/v1/nonexistent", expected_status=404),
            )
        )

        # Run all tests
        results = []
        for name, test_coro in tests:
            success, message = await test_coro
            results.append((name, success, message))

            # Print result
            if success:
                print(f"{Colors.GREEN}✓{Colors.RESET} {name}")
            else:
                print(f"{Colors.RED}✗{Colors.RESET} {name}")
                print(f"  {Colors.YELLOW}{message}{Colors.RESET}")

        # Summary
        print(f"\n{Colors.BOLD}Summary:{Colors.RESET}")
        passed = sum(1 for _, success, _ in results if success)
        total = len(results)

        if passed == total:
            print(f"{Colors.GREEN}All {total} tests passed!{Colors.RESET}")
            return 0
        else:
            print(f"{Colors.RED}{passed}/{total} tests passed{Colors.RESET}")
            return 1


async def test_specific_endpoint(base_url: str, endpoint: str, params: dict = None):
    """Test a specific endpoint with parameters."""
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        print(f"{Colors.BOLD}Testing: {endpoint}{Colors.RESET}")
        if params:
            print(f"Parameters: {json.dumps(params, indent=2)}")

        try:
            response = await client.get(endpoint, params=params)
            print(f"\nStatus: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")

            if response.headers.get("content-type", "").startswith("application/json"):
                print(f"\nResponse:\n{json.dumps(response.json(), indent=2)}")
            else:
                print(f"\nResponse (first 500 chars):\n{response.text[:500]}")

        except Exception as e:
            print(f"{Colors.RED}Error: {e}{Colors.RESET}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Quick API contract tests")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL for the API")
    parser.add_argument("--endpoint", help="Test specific endpoint")
    parser.add_argument("--params", help="JSON parameters for the endpoint")

    args = parser.parse_args()

    if args.endpoint:
        params = json.loads(args.params) if args.params else None
        return asyncio.run(test_specific_endpoint(args.base_url, args.endpoint, params))
    else:
        return asyncio.run(run_tests(args.base_url))


if __name__ == "__main__":
    sys.exit(main())
