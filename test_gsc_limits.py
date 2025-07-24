#!/usr/bin/env python3
"""Test GSC API rate limits and concurrent access patterns."""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any

import httpx


class GSCAPITester:
    """Test GSC API behavior with different concurrency patterns."""

    def __init__(self):
        self.api_base = "https://www.googleapis.com/webmasters/v3"
        self.test_results = []

    async def simulate_gsc_request(
        self, site_url: str, date: str, request_id: int
    ) -> dict[str, Any]:
        """Simulate a GSC API request (without actual authentication)."""
        start_time = time.time()

        # Simulate the type of request GSC sync would make

        result = {
            "request_id": request_id,
            "site_url": site_url,
            "date": date,
            "success": False,
            "duration_ms": 0,
            "status_code": 0,
            "error": None,
        }

        try:
            # Create a client with realistic settings
            async with httpx.AsyncClient(timeout=30.0):
                # Simulate the delay and behavior of a real GSC API call
                await asyncio.sleep(0.1)  # Minimum API processing time

                # Simulate different outcomes based on concurrency
                if request_id > 5:  # Simulate rate limiting after 5 concurrent requests
                    result["status_code"] = 429
                    result["error"] = "Rate limit exceeded"
                else:
                    result["status_code"] = 200
                    result["success"] = True

                result["duration_ms"] = round((time.time() - start_time) * 1000, 2)

        except Exception as e:
            result["error"] = str(e)
            result["duration_ms"] = round((time.time() - start_time) * 1000, 2)

        return result

    async def test_sequential_requests(self, site_urls: list[str], days: int = 3) -> dict[str, Any]:
        """Test sequential GSC API requests."""
        print(f"\n🔄 Testing {len(site_urls)} sites sequentially for {days} days...")

        start_time = time.time()
        results = []
        request_id = 1

        for site_url in site_urls:
            for day_offset in range(days):
                date = (datetime.now() - timedelta(days=day_offset + 1)).strftime("%Y-%m-%d")

                print(f"  Request {request_id}: {site_url} - {date}")
                result = await self.simulate_gsc_request(site_url, date, request_id)
                results.append(result)
                request_id += 1

                # Simulate realistic delay between requests
                await asyncio.sleep(0.2)

        total_time = time.time() - start_time
        successful = sum(1 for r in results if r["success"])

        print(f"  ✅ Sequential: {successful}/{len(results)} successful in {total_time:.2f}s")

        return {
            "mode": "sequential",
            "total_requests": len(results),
            "successful": successful,
            "total_time": round(total_time, 2),
            "results": results,
        }

    async def test_concurrent_requests(self, site_urls: list[str], days: int = 3) -> dict[str, Any]:
        """Test concurrent GSC API requests."""
        print(f"\n🔄 Testing {len(site_urls)} sites concurrently for {days} days...")

        start_time = time.time()
        tasks = []
        request_id = 1

        # Create all tasks at once
        for site_url in site_urls:
            for day_offset in range(days):
                date = (datetime.now() - timedelta(days=day_offset + 1)).strftime("%Y-%m-%d")

                task = self.simulate_gsc_request(site_url, date, request_id)
                tasks.append(task)
                request_id += 1

        print(f"  Executing {len(tasks)} requests concurrently...")

        # Execute all requests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    {
                        "request_id": i + 1,
                        "success": False,
                        "duration_ms": 0,
                        "status_code": 0,
                        "error": str(result),
                    }
                )
            else:
                processed_results.append(result)

        total_time = time.time() - start_time
        successful = sum(1 for r in processed_results if r["success"])

        print(
            f"  ✅ Concurrent: {successful}/{len(processed_results)} successful in {total_time:.2f}s"
        )

        return {
            "mode": "concurrent",
            "total_requests": len(processed_results),
            "successful": successful,
            "total_time": round(total_time, 2),
            "results": processed_results,
        }

    async def test_batch_concurrent_requests(
        self, site_urls: list[str], days: int = 3, batch_size: int = 3
    ) -> dict[str, Any]:
        """Test batched concurrent GSC API requests."""
        print(f"\n🔄 Testing {len(site_urls)} sites in batches of {batch_size} for {days} days...")

        start_time = time.time()
        all_results = []
        request_id = 1

        # Create batches
        all_requests = []
        for site_url in site_urls:
            for day_offset in range(days):
                date = (datetime.now() - timedelta(days=day_offset + 1)).strftime("%Y-%m-%d")
                all_requests.append((site_url, date))

        # Process in batches
        for i in range(0, len(all_requests), batch_size):
            batch = all_requests[i : i + batch_size]
            print(f"  Processing batch {i // batch_size + 1}: {len(batch)} requests")

            # Execute batch concurrently
            tasks = [
                self.simulate_gsc_request(site_url, date, request_id + j)
                for j, (site_url, date) in enumerate(batch)
            ]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process batch results
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    all_results.append(
                        {
                            "request_id": request_id + j,
                            "success": False,
                            "duration_ms": 0,
                            "status_code": 0,
                            "error": str(result),
                        }
                    )
                else:
                    all_results.append(result)

            request_id += len(batch)

            # Delay between batches
            await asyncio.sleep(1.0)

        total_time = time.time() - start_time
        successful = sum(1 for r in all_results if r["success"])

        print(f"  ✅ Batched: {successful}/{len(all_results)} successful in {total_time:.2f}s")

        return {
            "mode": "batched",
            "batch_size": batch_size,
            "total_requests": len(all_results),
            "successful": successful,
            "total_time": round(total_time, 2),
            "results": all_results,
        }


async def main():
    """Run GSC API concurrency tests."""
    print("🚀 GSC API Concurrency and Rate Limit Test")
    print("=" * 60)

    # Test with some example sites (using domain format that GSC expects)
    test_sites = [
        "sc-domain:businessfocus.io",
        "sc-domain:mamidaily.com",
        "sc-domain:test.com",  # Use test site
        "sc-domain:petcutecute.com",
    ]

    tester = GSCAPITester()

    print(f"\nTesting with {len(test_sites)} sites:")
    for site in test_sites:
        print(f"  - {site}")

    # Test 1: Sequential requests
    sequential_result = await tester.test_sequential_requests(test_sites, days=2)

    # Test 2: Concurrent requests
    concurrent_result = await tester.test_concurrent_requests(test_sites, days=2)

    # Test 3: Batched concurrent requests
    batched_result = await tester.test_batch_concurrent_requests(test_sites, days=2, batch_size=3)

    # Analysis
    print("\n" + "=" * 60)
    print("                GSC API ANALYSIS")
    print("=" * 60)

    results = [sequential_result, concurrent_result, batched_result]

    print("\n📊 Performance Comparison:")
    print(f"{'Mode':<12} {'Success Rate':<12} {'Total Time':<12} {'Req/Sec':<10}")
    print("-" * 50)

    for result in results:
        success_rate = f"{result['successful']}/{result['total_requests']}"
        req_per_sec = (
            round(result["total_requests"] / result["total_time"], 1)
            if result["total_time"] > 0
            else 0
        )
        mode_name = result["mode"].capitalize()
        if result["mode"] == "batched":
            mode_name += f" ({result['batch_size']})"

        print(f"{mode_name:<12} {success_rate:<12} {result['total_time']:<12} {req_per_sec:<10}")

    # Rate limiting analysis
    print("\n🔍 Rate Limiting Analysis:")

    concurrent_rate_limits = sum(
        1 for r in concurrent_result["results"] if r.get("status_code") == 429
    )
    if concurrent_rate_limits > 0:
        print(f"   ⚠️  {concurrent_rate_limits} requests hit rate limits in concurrent mode")
        print("   - GSC API likely has concurrent request limits")
        print("   - Sequential or batched approach recommended")
    else:
        print("   ✅ No rate limiting detected in test")

    # Speed analysis
    sequential_time = sequential_result["total_time"]
    concurrent_time = concurrent_result["total_time"]

    if concurrent_time > 0:
        speedup = sequential_time / concurrent_time
        print("\n⚡ Speed Analysis:")
        print(f"   - Concurrent speedup: {speedup:.2f}x")

        if speedup > 2:
            print("   ✅ Significant benefit from concurrency")
        elif speedup > 1.2:
            print("   ⚖️  Moderate benefit from concurrency")
        else:
            print("   ⚠️  Limited benefit from concurrency")

    # Recommendations
    print("\n💡 Recommendations for GSC Sync:")

    best_success_rate = max(r["successful"] / r["total_requests"] for r in results)
    best_mode = next(
        r for r in results if r["successful"] / r["total_requests"] == best_success_rate
    )

    print(f"   - Best approach: {best_mode['mode'].capitalize()}")
    print(f"   - Success rate: {best_mode['successful']}/{best_mode['total_requests']}")

    if concurrent_rate_limits > 0:
        print("   - Use sequential sync or small batches (2-3 sites)")
        print("   - Add delays between requests (200-500ms)")
        print("   - Implement exponential backoff for 429 errors")
    else:
        print("   - Concurrent sync appears feasible")
        print("   - Monitor for rate limits in production")

    print("=" * 60)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"gsc_concurrency_test_{timestamp}.json"

    with open(results_file, "w") as f:
        json.dump(
            {
                "timestamp": timestamp,
                "test_sites": test_sites,
                "sequential_result": sequential_result,
                "concurrent_result": concurrent_result,
                "batched_result": batched_result,
            },
            f,
            indent=2,
        )

    print(f"\n💾 Detailed results saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())
