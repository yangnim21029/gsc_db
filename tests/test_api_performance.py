#!/usr/bin/env python3
"""
Performance test script for /api/v1/ranking-data/ endpoint.

Tests various scenarios including:
- Basic queries
- Filtered queries (by keywords/pages)
- Large date ranges
- Concurrent requests
- Response time measurements
"""

import json
import statistics
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import requests
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

console = Console()

# Configuration
BASE_URL = "http://localhost:8000"
ENDPOINT = "/api/v1/ranking-data/"
DEFAULT_SITE_ID = 4  # Adjust based on your test site


class PerformanceTest:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.endpoint = f"{base_url}{ENDPOINT}"
        self.results: List[Dict[str, Any]] = []

    def make_request(self, payload: Dict[str, Any]) -> Tuple[float, int, Any]:
        """Make a single request and return (response_time, status_code, response_data)."""
        start_time = time.time()

        try:
            response = requests.post(
                self.endpoint, json=payload, headers={"Content-Type": "application/json"}
            )
            response_time = time.time() - start_time

            try:
                data = response.json()
            except (ValueError, json.JSONDecodeError):
                data = None

            return response_time, response.status_code, data

        except Exception as e:
            response_time = time.time() - start_time
            return response_time, 0, str(e)

    def test_basic_query(self, site_id: int = DEFAULT_SITE_ID) -> Dict[str, Any]:
        """Test basic query for last 7 days."""
        console.print("\n[bold blue]Testing Basic Query (Last 7 Days)[/bold blue]")

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)

        payload = {
            "site_id": site_id,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "group_by": "query",
            "max_results": 100,
        }

        response_time, status_code, data = self.make_request(payload)

        result = {
            "test": "basic_query",
            "response_time": response_time,
            "status_code": status_code,
            "records_returned": len(data.get("data", [])) if isinstance(data, dict) else 0,
            "payload": payload,
        }

        self.results.append(result)
        self._print_result(result)
        return result

    def test_filtered_queries(self, site_id: int = DEFAULT_SITE_ID) -> Dict[str, Any]:
        """Test with specific query filters."""
        console.print("\n[bold blue]Testing Filtered Queries[/bold blue]")

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)

        payload = {
            "site_id": site_id,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "queries": ["阪急百貨香港", "日本阪急百貨 香港", "阪急百貨店"],
            "group_by": "query",
            "max_results": 1000,
        }

        response_time, status_code, data = self.make_request(payload)

        result = {
            "test": "filtered_queries",
            "response_time": response_time,
            "status_code": status_code,
            "records_returned": len(data.get("data", [])) if isinstance(data, dict) else 0,
            "queries_count": len(payload["queries"]),
            "payload": payload,
        }

        self.results.append(result)
        self._print_result(result)
        return result

    def test_page_grouping(self, site_id: int = DEFAULT_SITE_ID) -> Dict[str, Any]:
        """Test page-level grouping."""
        console.print("\n[bold blue]Testing Page Grouping[/bold blue]")

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=14)

        payload = {
            "site_id": site_id,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "group_by": "page",
            "max_results": 500,
        }

        response_time, status_code, data = self.make_request(payload)

        result = {
            "test": "page_grouping",
            "response_time": response_time,
            "status_code": status_code,
            "records_returned": len(data.get("data", [])) if isinstance(data, dict) else 0,
            "payload": payload,
        }

        self.results.append(result)
        self._print_result(result)
        return result

    def test_large_date_range(self, site_id: int = DEFAULT_SITE_ID) -> Dict[str, Any]:
        """Test with large date range (90 days)."""
        console.print("\n[bold blue]Testing Large Date Range (90 Days)[/bold blue]")

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=90)

        payload = {
            "site_id": site_id,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "group_by": "query",
            "max_results": 5000,
        }

        response_time, status_code, data = self.make_request(payload)

        result = {
            "test": "large_date_range",
            "response_time": response_time,
            "status_code": status_code,
            "records_returned": len(data.get("data", [])) if isinstance(data, dict) else 0,
            "days_queried": 90,
            "payload": payload,
        }

        self.results.append(result)
        self._print_result(result)
        return result

    def test_max_results_limit(self, site_id: int = DEFAULT_SITE_ID) -> Dict[str, Any]:
        """Test with maximum allowed results."""
        console.print("\n[bold blue]Testing Maximum Results Limit[/bold blue]")

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=365)

        payload = {
            "site_id": site_id,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "group_by": "query",
            "max_results": 10000,  # Maximum allowed
        }

        response_time, status_code, data = self.make_request(payload)

        result = {
            "test": "max_results_limit",
            "response_time": response_time,
            "status_code": status_code,
            "records_returned": len(data.get("data", [])) if isinstance(data, dict) else 0,
            "max_results_requested": 10000,
            "payload": payload,
        }

        self.results.append(result)
        self._print_result(result)
        return result

    def test_hostname_query(
        self, hostname: str = "hkg.hankyu-hanshin-dept.co.jp"
    ) -> Dict[str, Any]:
        """Test query using hostname instead of site_id."""
        console.print("\n[bold blue]Testing Hostname-based Query[/bold blue]")

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=14)

        payload = {
            "hostname": hostname,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "group_by": "query",
            "max_results": 200,
        }

        response_time, status_code, data = self.make_request(payload)

        result = {
            "test": "hostname_query",
            "response_time": response_time,
            "status_code": status_code,
            "records_returned": len(data.get("data", [])) if isinstance(data, dict) else 0,
            "hostname": hostname,
            "payload": payload,
        }

        self.results.append(result)
        self._print_result(result)
        return result

    def test_daily_api(self, site_id: int = DEFAULT_SITE_ID) -> Dict[str, Any]:
        """Test daily aggregated data API endpoint."""
        console.print("\n[bold blue]Testing Daily Data API[/bold blue]")

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)

        # Change endpoint for this test
        original_endpoint = self.endpoint
        self.endpoint = f"{self.base_url}/api/v1/daily-data/"

        payload = {"site_id": site_id, "start_date": str(start_date), "end_date": str(end_date)}

        response_time, status_code, data = self.make_request(payload)

        result = {
            "test": "daily_data_api",
            "response_time": response_time,
            "status_code": status_code,
            "days_returned": len(data.get("data", [])) if isinstance(data, dict) else 0,
            "payload": payload,
        }

        # Restore original endpoint
        self.endpoint = original_endpoint

        self.results.append(result)
        self._print_result(result)
        return result

    def test_daily_api_with_hostname(
        self, hostname: str = "hkg.hankyu-hanshin-dept.co.jp"
    ) -> Dict[str, Any]:
        """Test daily API with hostname."""
        console.print("\n[bold blue]Testing Daily Data API with Hostname[/bold blue]")

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)

        # Change endpoint for this test
        original_endpoint = self.endpoint
        self.endpoint = f"{self.base_url}/api/v1/daily-data/"

        payload = {"hostname": hostname, "start_date": str(start_date), "end_date": str(end_date)}

        response_time, status_code, data = self.make_request(payload)

        result = {
            "test": "daily_data_hostname",
            "response_time": response_time,
            "status_code": status_code,
            "days_returned": len(data.get("data", [])) if isinstance(data, dict) else 0,
            "hostname": hostname,
            "payload": payload,
        }

        # Restore original endpoint
        self.endpoint = original_endpoint

        self.results.append(result)
        self._print_result(result)
        return result

    def test_hourly_ranking_api(self, site_id: int = DEFAULT_SITE_ID) -> Dict[str, Any]:
        """Test hourly ranking data API endpoint."""
        console.print("\n[bold blue]Testing Hourly Ranking Data API[/bold blue]")

        # Use very recent dates for hourly data (last 2 days)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=1)

        # Change endpoint for this test
        original_endpoint = self.endpoint
        self.endpoint = f"{self.base_url}/api/v1/ranking-data-hourly/"

        payload = {
            "site_id": site_id,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "group_by": "query",
            "max_results": 500,
        }

        response_time, status_code, data = self.make_request(payload)

        result = {
            "test": "hourly_ranking_api",
            "response_time": response_time,
            "status_code": status_code,
            "records_returned": len(data.get("data", [])) if isinstance(data, dict) else 0,
            "date_range": f"{start_date} to {end_date}",
            "payload": payload,
        }

        # Restore original endpoint
        self.endpoint = original_endpoint

        self.results.append(result)
        self._print_result(result)
        return result

    def test_hourly_api_with_hostname(
        self, hostname: str = "hkg.hankyu-hanshin-dept.co.jp"
    ) -> Dict[str, Any]:
        """Test hourly API with hostname."""
        console.print("\n[bold blue]Testing Hourly API with Hostname[/bold blue]")

        # Use very recent dates for hourly data
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=1)

        # Change endpoint for this test
        original_endpoint = self.endpoint
        self.endpoint = f"{self.base_url}/api/v1/ranking-data-hourly/"

        payload = {
            "hostname": hostname,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "group_by": "query",
            "max_results": 200,
        }

        response_time, status_code, data = self.make_request(payload)

        result = {
            "test": "hourly_api_hostname",
            "response_time": response_time,
            "status_code": status_code,
            "records_returned": len(data.get("data", [])) if isinstance(data, dict) else 0,
            "hostname": hostname,
            "payload": payload,
        }

        # Restore original endpoint
        self.endpoint = original_endpoint

        self.results.append(result)
        self._print_result(result)
        return result

    def test_concurrent_requests(
        self, site_id: int = DEFAULT_SITE_ID, concurrent: int = 10
    ) -> Dict[str, Any]:
        """Test concurrent requests."""
        console.print(
            f"\n[bold blue]Testing Concurrent Requests ({concurrent} simultaneous)[/bold blue]"
        )

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)

        payload = {
            "site_id": site_id,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "group_by": "query",
            "max_results": 100,
        }

        response_times = []
        successful_requests = 0

        with Progress() as progress:
            task = progress.add_task(
                f"[cyan]Making {concurrent} concurrent requests...", total=concurrent
            )

            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent) as executor:
                futures = [executor.submit(self.make_request, payload) for _ in range(concurrent)]

                for future in concurrent.futures.as_completed(futures):
                    response_time, status_code, _ = future.result()
                    response_times.append(response_time)
                    if status_code == 200:
                        successful_requests += 1
                    progress.update(task, advance=1)

        result = {
            "test": "concurrent_requests",
            "concurrent_requests": concurrent,
            "successful_requests": successful_requests,
            "avg_response_time": statistics.mean(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "median_response_time": statistics.median(response_times),
            "payload": payload,
        }

        self.results.append(result)
        self._print_result(result)
        return result

    def test_repeated_requests(
        self, site_id: int = DEFAULT_SITE_ID, iterations: int = 20
    ) -> Dict[str, Any]:
        """Test repeated sequential requests to measure consistency."""
        console.print(
            f"\n[bold blue]Testing Request Consistency ({iterations} iterations)[/bold blue]"
        )

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)

        payload = {
            "site_id": site_id,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "group_by": "query",
            "max_results": 100,
        }

        response_times = []

        with Progress() as progress:
            task = progress.add_task(
                f"[cyan]Making {iterations} sequential requests...", total=iterations
            )

            for _ in range(iterations):
                response_time, status_code, _ = self.make_request(payload)
                if status_code == 200:
                    response_times.append(response_time)
                progress.update(task, advance=1)
                time.sleep(0.1)  # Small delay between requests

        if response_times:
            result = {
                "test": "repeated_requests",
                "iterations": iterations,
                "successful_requests": len(response_times),
                "avg_response_time": statistics.mean(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "median_response_time": statistics.median(response_times),
                "std_dev": statistics.stdev(response_times) if len(response_times) > 1 else 0,
                "payload": payload,
            }
        else:
            result = {
                "test": "repeated_requests",
                "iterations": iterations,
                "successful_requests": 0,
                "error": "No successful requests",
            }

        self.results.append(result)
        self._print_result(result)
        return result

    def _print_result(self, result: Dict[str, Any]):
        """Print individual test result."""
        if result.get("status_code") == 200 or result.get("successful_requests", 0) > 0:
            console.print(f"[green]✓[/green] {result['test']}: ", end="")

            if "response_time" in result:
                console.print(f"Response time: {result['response_time']:.3f}s", end="")
                if "records_returned" in result:
                    console.print(f", Records: {result['records_returned']}")
                else:
                    console.print()
            elif "avg_response_time" in result:
                console.print(
                    f"Avg: {result['avg_response_time']:.3f}s, "
                    f"Min: {result['min_response_time']:.3f}s, "
                    f"Max: {result['max_response_time']:.3f}s"
                )
        else:
            console.print(f"[red]✗[/red] {result['test']}: Failed")

    def print_summary(self):
        """Print summary of all test results."""
        console.print("\n[bold]Performance Test Summary[/bold]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Test", style="cyan")
        table.add_column("Response Time", justify="right")
        table.add_column("Records", justify="right")
        table.add_column("Status")

        for result in self.results:
            test_name = result["test"].replace("_", " ").title()

            if "response_time" in result:
                response_time = f"{result['response_time']:.3f}s"
            elif "avg_response_time" in result:
                response_time = f"{result['avg_response_time']:.3f}s (avg)"
            else:
                response_time = "N/A"

            records = str(result.get("records_returned", "N/A"))

            if result.get("status_code") == 200 or result.get("successful_requests", 0) > 0:
                status = "[green]Success[/green]"
            else:
                status = "[red]Failed[/red]"

            table.add_row(test_name, response_time, records, status)

        console.print(table)

        # Print additional statistics
        successful_tests = [r for r in self.results if r.get("status_code") == 200]
        if successful_tests:
            response_times = [r["response_time"] for r in successful_tests if "response_time" in r]
            if response_times:
                console.print("\n[bold]Overall Statistics:[/bold]")
                console.print(f"Average response time: {statistics.mean(response_times):.3f}s")
                console.print(f"Median response time: {statistics.median(response_times):.3f}s")
                console.print(f"Min response time: {min(response_times):.3f}s")
                console.print(f"Max response time: {max(response_times):.3f}s")


def main():
    """Run all performance tests."""
    console.print("[bold green]GSC API Performance Test Suite[/bold green]")
    console.print(f"Testing endpoint: {BASE_URL}{ENDPOINT}")
    console.print(f"Default site ID: {DEFAULT_SITE_ID}")

    # Check if API is accessible
    try:
        response = requests.get(f"{BASE_URL}/docs")
        if response.status_code != 200:
            console.print(
                "[red]Warning: API may not be accessible. Make sure the server is running.[/red]"
            )
    except requests.exceptions.RequestException:
        console.print(
            "[red]Error: Cannot connect to API. Please start the server with 'just dev-server'[/red]"
        )
        return

    tester = PerformanceTest(BASE_URL)

    # Run all tests
    tester.test_basic_query()
    tester.test_filtered_queries()
    tester.test_page_grouping()
    tester.test_large_date_range()
    tester.test_max_results_limit()
    tester.test_hostname_query()  # New test for hostname-based queries
    tester.test_daily_api()  # Test daily aggregated API
    tester.test_daily_api_with_hostname()  # Test daily API with hostname
    tester.test_hourly_ranking_api()  # Test hourly ranking API
    tester.test_hourly_api_with_hostname()  # Test hourly API with hostname
    tester.test_repeated_requests(iterations=10)
    tester.test_concurrent_requests(concurrent=5)

    # Print summary
    tester.print_summary()

    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"performance_test_results_{timestamp}.json"

    with open(results_file, "w") as f:
        json.dump(
            {"timestamp": timestamp, "endpoint": ENDPOINT, "results": tester.results}, f, indent=2
        )

    console.print(f"\n[green]Results saved to: {results_file}[/green]")


if __name__ == "__main__":
    main()
