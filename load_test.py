#!/usr/bin/env python3
"""Load testing script for API endpoints."""

import asyncio
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

import httpx


async def test_ranking_data_api(client: httpx.AsyncClient, user_id: int) -> Dict[str, Any]:
    """Test ranking-data API endpoint."""
    start_time = time.time()
    
    # Test data for Urban Life (site_id 17)
    payload = {
        "site_id": 17,
        "date_from": "2025-07-22",
        "date_to": "2025-07-25", 
        "queries": ["美容", "護膚"],
        "exact_match": False,
        "group_by": ["query"],
        "limit": 100
    }
    
    try:
        response = await client.post(
            "http://localhost:8000/api/v1/analytics/ranking-data",
            json=payload,
            timeout=30.0
        )
        
        duration = time.time() - start_time
        
        success = response.status_code in [200, 201]
        error = None
        
        # Additional check for empty data
        if success:
            try:
                data = response.json()
                if data.get("total", 0) == 0:
                    success = False
                    error = "No data returned"
            except:
                success = False
                error = "Invalid JSON response"
        else:
            error = response.text[:200]
        
        return {
            "user_id": user_id,
            "endpoint": "ranking-data",
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "success": success,
            "response_size": len(response.content) if response.content else 0,
            "error": error
        }
        
    except Exception as e:
        duration = time.time() - start_time
        return {
            "user_id": user_id,
            "endpoint": "ranking-data",
            "status_code": 0,
            "duration_ms": round(duration * 1000, 2),
            "success": False,
            "response_size": 0,
            "error": str(e)[:200]
        }


async def test_csv_export_api(client: httpx.AsyncClient, user_id: int) -> Dict[str, Any]:
    """Test page-keyword-performance CSV export endpoint."""
    start_time = time.time()
    
    try:
        response = await client.get(
            "http://localhost:8000/api/v1/page-keyword-performance/csv/",
            params={
                "site_id": 17,
                "days": 3
            },
            timeout=30.0
        )
        
        duration = time.time() - start_time
        
        return {
            "user_id": user_id,
            "endpoint": "csv-export", 
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "success": response.status_code in [200, 201],
            "response_size": len(response.content) if response.content else 0,
            "error": None if response.status_code == 200 else response.text[:200]
        }
        
    except Exception as e:
        duration = time.time() - start_time
        return {
            "user_id": user_id,
            "endpoint": "csv-export",
            "status_code": 0,
            "duration_ms": round(duration * 1000, 2), 
            "success": False,
            "response_size": 0,
            "error": str(e)[:200]
        }


async def run_concurrent_test(endpoint_name: str, test_func, num_users: int = 10) -> List[Dict[str, Any]]:
    """Run concurrent test for specific endpoint."""
    print(f"\n🔄 Starting {endpoint_name} test with {num_users} concurrent users...")
    
    # Create HTTP client with connection pooling
    async with httpx.AsyncClient(
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        timeout=httpx.Timeout(30.0)
    ) as client:
        
        # Create tasks for concurrent execution
        tasks = [
            test_func(client, user_id)
            for user_id in range(1, num_users + 1)
        ]
        
        # Execute all tasks concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "user_id": i + 1,
                    "endpoint": endpoint_name,
                    "status_code": 0,
                    "duration_ms": 0,
                    "success": False,
                    "response_size": 0,
                    "error": str(result)[:200]
                })
            else:
                processed_results.append(result)
        
        # Print summary
        successful = sum(1 for r in processed_results if r["success"])
        failed = len(processed_results) - successful
        avg_duration = sum(r["duration_ms"] for r in processed_results) / len(processed_results)
        
        print(f"✅ {endpoint_name} test completed:")
        print(f"   Total time: {total_duration:.2f}s")
        print(f"   Successful: {successful}/{num_users}")
        print(f"   Failed: {failed}/{num_users}")
        print(f"   Average response time: {avg_duration:.2f}ms")
        
        return processed_results


def analyze_results(ranking_results: List[Dict], csv_results: List[Dict]):
    """Analyze and display test results."""
    print("\n" + "="*80)
    print("                        LOAD TEST ANALYSIS")
    print("="*80)
    
    # Combined analysis
    all_results = ranking_results + csv_results
    total_requests = len(all_results)
    successful_requests = sum(1 for r in all_results if r["success"])
    
    print(f"\n📊 Overall Summary:")
    print(f"   Total requests: {total_requests}")
    print(f"   Successful: {successful_requests} ({successful_requests/total_requests*100:.1f}%)")
    print(f"   Failed: {total_requests - successful_requests}")
    
    # Performance analysis by endpoint
    for endpoint, results in [("ranking-data", ranking_results), ("csv-export", csv_results)]:
        print(f"\n📈 {endpoint.upper()} Performance:")
        
        successful = [r for r in results if r["success"]]
        if successful:
            durations = [r["duration_ms"] for r in successful]
            sizes = [r["response_size"] for r in successful]
            
            print(f"   Success rate: {len(successful)}/{len(results)} ({len(successful)/len(results)*100:.1f}%)")
            print(f"   Min response time: {min(durations):.2f}ms")
            print(f"   Max response time: {max(durations):.2f}ms")
            print(f"   Avg response time: {sum(durations)/len(durations):.2f}ms")
            print(f"   Avg response size: {sum(sizes)/len(sizes):.0f} bytes")
            
            # Identify bottlenecks
            slow_requests = [r for r in successful if r["duration_ms"] > 1000]
            if slow_requests:
                print(f"   ⚠️  Slow requests (>1s): {len(slow_requests)}")
        
        # Show errors if any
        failed = [r for r in results if not r["success"]]
        if failed:
            print(f"   ❌ Errors:")
            error_types = {}
            for r in failed:
                error_key = r["error"][:50] if r["error"] else f"HTTP {r['status_code']}"
                error_types[error_key] = error_types.get(error_key, 0) + 1
            
            for error, count in error_types.items():
                print(f"      {error}: {count} occurrences")
    
    # Recommendations
    print(f"\n💡 Performance Recommendations:")
    
    all_durations = [r["duration_ms"] for r in all_results if r["success"]]
    if all_durations:
        avg_duration = sum(all_durations) / len(all_durations)
        
        if avg_duration > 2000:
            print("   - Consider implementing database query optimization")
            print("   - Add Redis caching for frequently accessed data")
        elif avg_duration > 1000:
            print("   - Monitor database connection pool")
            print("   - Consider adding response compression")
        else:
            print("   - API performance is good for current load")
    
    print("="*80)


async def main():
    """Main test execution."""
    print("🚀 Starting GSC Database API Load Test")
    print("Testing urbanlifehk.com (site_id: 17) with 3 days of synced data")
    
    # Test 1: Ranking Data API
    ranking_results = await run_concurrent_test(
        "ranking-data",
        test_ranking_data_api,
        num_users=10
    )
    
    # Small delay between tests
    await asyncio.sleep(2)
    
    # Test 2: CSV Export API
    csv_results = await run_concurrent_test(
        "csv-export", 
        test_csv_export_api,
        num_users=10
    )
    
    # Analyze results
    analyze_results(ranking_results, csv_results)
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"load_test_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "ranking_data_results": ranking_results,
            "csv_export_results": csv_results
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())