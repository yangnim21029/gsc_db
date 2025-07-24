#!/usr/bin/env python3
"""Stress testing script for API concurrent performance."""

import asyncio
import json
import time
from datetime import datetime
from typing import Any

import httpx


async def test_ranking_data_concurrent(
    client: httpx.AsyncClient, user_id: int, test_data: dict
) -> dict[str, Any]:
    """Test ranking-data API with concurrent access."""
    start_time = time.time()

    try:
        response = await client.post(
            "http://localhost:8000/api/v1/analytics/ranking-data", json=test_data, timeout=30.0
        )

        duration = time.time() - start_time
        success = response.status_code in [200, 201]

        # Parse response for analysis
        data_size = 0
        total_records = 0
        if success:
            try:
                json_data = response.json()
                data_size = len(response.content)
                total_records = json_data.get("total", 0)
            except Exception:
                success = False

        return {
            "user_id": user_id,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "success": success,
            "response_size": data_size,
            "total_records": total_records,
            "error": None if success else response.text[:200],
        }

    except Exception as e:
        duration = time.time() - start_time
        return {
            "user_id": user_id,
            "status_code": 0,
            "duration_ms": round(duration * 1000, 2),
            "success": False,
            "response_size": 0,
            "total_records": 0,
            "error": str(e)[:200],
        }


async def run_concurrent_stress_test(concurrent_users: int) -> dict[str, Any]:
    """Run stress test with specified number of concurrent users."""
    print(f"\n🔥 Running stress test with {concurrent_users} concurrent users...")

    # Test data for Urban Life
    test_payload = {
        "site_id": 17,
        "date_from": "2025-07-23",
        "date_to": "2025-07-24",
        "group_by": ["query"],
        "limit": 100,
    }

    # Create HTTP client optimized for high concurrency
    async with httpx.AsyncClient(
        limits=httpx.Limits(
            max_keepalive_connections=concurrent_users * 2, max_connections=concurrent_users * 4
        ),
        timeout=httpx.Timeout(30.0),
    ) as client:
        # Create tasks
        tasks = [
            test_ranking_data_concurrent(client, user_id, test_payload)
            for user_id in range(1, concurrent_users + 1)
        ]

        # Execute all tasks concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time

        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    {
                        "user_id": i + 1,
                        "status_code": 0,
                        "duration_ms": 0,
                        "success": False,
                        "response_size": 0,
                        "total_records": 0,
                        "error": str(result)[:200],
                    }
                )
            else:
                processed_results.append(result)

        # Calculate metrics
        successful = [r for r in processed_results if r["success"]]
        failed = [r for r in processed_results if not r["success"]]

        # Performance metrics
        metrics = {
            "concurrent_users": concurrent_users,
            "total_duration": round(total_duration, 2),
            "total_requests": len(processed_results),
            "successful_requests": len(successful),
            "failed_requests": len(failed),
            "success_rate": round(len(successful) / len(processed_results) * 100, 1),
            "requests_per_second": round(len(processed_results) / total_duration, 2),
            "avg_response_time": round(
                sum(r["duration_ms"] for r in successful) / len(successful), 2
            )
            if successful
            else 0,
            "min_response_time": min(r["duration_ms"] for r in successful) if successful else 0,
            "max_response_time": max(r["duration_ms"] for r in successful) if successful else 0,
            "total_data_transferred": sum(r["response_size"] for r in successful),
            "avg_records_per_request": round(
                sum(r["total_records"] for r in successful) / len(successful), 1
            )
            if successful
            else 0,
        }

        # Print summary
        print(
            f"   ✅ {metrics['successful_requests']}/{metrics['total_requests']} requests successful ({metrics['success_rate']}%)"
        )
        print(f"   ⚡ {metrics['requests_per_second']} requests/second")
        print(f"   🕐 Avg response time: {metrics['avg_response_time']}ms")
        print(f"   📊 Total data: {metrics['total_data_transferred']} bytes")

        if failed:
            print(f"   ❌ {len(failed)} failures")
            error_types = {}
            for r in failed:
                error = r["error"][:50] if r["error"] else f"HTTP {r['status_code']}"
                error_types[error] = error_types.get(error, 0) + 1
            for error, count in error_types.items():
                print(f"      - {error}: {count} times")

        return {"metrics": metrics, "results": processed_results}


async def run_scalability_test():
    """Test API scalability with increasing concurrent users."""
    print("🚀 Starting API Scalability Test")
    print("Testing urbanlifehk.com ranking-data endpoint")

    # Test different concurrency levels
    concurrency_levels = [1, 5, 10, 20, 30, 50]
    all_results = {}

    for concurrent_users in concurrency_levels:
        test_result = await run_concurrent_stress_test(concurrent_users)
        all_results[concurrent_users] = test_result

        # Small delay between tests
        await asyncio.sleep(1)

    # Analysis
    print("\n" + "=" * 80)
    print("                     SCALABILITY ANALYSIS")
    print("=" * 80)

    print("\n📈 Performance Summary:")
    print(
        f"{'Users':<8} {'Success%':<10} {'RPS':<8} {'Avg(ms)':<10} {'Min(ms)':<10} {'Max(ms)':<10}"
    )
    print("-" * 66)

    best_rps = 0
    best_concurrency = 0

    for users in concurrency_levels:
        metrics = all_results[users]["metrics"]
        print(
            f"{users:<8} {metrics['success_rate']:<10} {metrics['requests_per_second']:<8} "
            f"{metrics['avg_response_time']:<10} {metrics['min_response_time']:<10} {metrics['max_response_time']:<10}"
        )

        if metrics["requests_per_second"] > best_rps and metrics["success_rate"] > 95:
            best_rps = metrics["requests_per_second"]
            best_concurrency = users

    # Recommendations
    print("\n💡 Performance Analysis:")
    if best_concurrency > 0:
        print(f"   - Best performance: {best_concurrency} concurrent users ({best_rps} RPS)")

    # Check for bottlenecks
    last_metrics = all_results[concurrency_levels[-1]]["metrics"]
    if last_metrics["success_rate"] < 90:
        print(f"   - ⚠️  API shows stress at {concurrency_levels[-1]} concurrent users")
        print("   - Consider implementing connection pooling or caching")
    elif last_metrics["avg_response_time"] > 1000:
        print("   - ⚠️  Response times degrading at high concurrency")
        print("   - Database query optimization recommended")
    else:
        print(f"   - ✅ API handles {concurrency_levels[-1]} concurrent users well")

    # Database bottleneck detection
    high_concurrency_metrics = all_results[concurrency_levels[-2]]["metrics"]
    if high_concurrency_metrics["avg_response_time"] > 500:
        print("   - 🔍 Potential database bottleneck detected")
        print("   - Consider implementing Redis caching")
        print("   - Monitor SQLite lock contention")

    print("=" * 80)

    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"stress_test_results_{timestamp}.json"

    with open(results_file, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n💾 Detailed results saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(run_scalability_test())
