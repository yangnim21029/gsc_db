#!/usr/bin/env python3
"""
Automated performance test for sync-multiple operations.
This script tests the sync performance improvements after fixing the latency issue.
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from typing import Dict, Tuple


def run_sync_test(site_ids: str, days: int) -> Tuple[float, bool, str]:
    """Run sync-multiple command and measure execution time."""
    start_time = time.time()

    cmd = ["just", "sync-multiple", site_ids, str(days)]
    print(f"\n🚀 Running: {' '.join(cmd)}")
    print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
        )

        elapsed_time = time.time() - start_time
        success = result.returncode == 0

        output = result.stdout if success else result.stderr

        return elapsed_time, success, output

    except subprocess.TimeoutExpired:
        elapsed_time = time.time() - start_time
        return elapsed_time, False, "Command timed out after 10 minutes"
    except Exception as e:
        elapsed_time = time.time() - start_time
        return elapsed_time, False, f"Error: {str(e)}"


def extract_sync_stats(output: str) -> Dict[str, int]:
    """Extract success/failure counts from sync output."""
    stats = {"success": 0, "failed": 0, "total": 0}

    # Look for patterns like "✓ Site 1: Success" or "✗ Site 2: Failed"
    for line in output.split("\n"):
        if "✓" in line and "Success" in line:
            stats["success"] += 1
        elif "✗" in line and "Failed" in line:
            stats["failed"] += 1

    stats["total"] = stats["success"] + stats["failed"]
    return stats


def format_time(seconds: float) -> str:
    """Format seconds into human-readable time."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m ({seconds:.0f}s)"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h ({seconds:.0f}s)"


def main():
    """Run performance tests with different configurations."""
    print("=" * 60)
    print("🔬 GSC Sync Performance Test")
    print("=" * 60)

    # Test configurations using actual site IDs
    test_configs = [
        ("5 11 16", 5),  # 3 sites, 5 days
        ("5", 7),  # 1 site, 7 days
        ("5 11 16 21", 3),  # 4 sites, 3 days
    ]

    results = []

    for site_ids, days in test_configs:
        site_count = len(site_ids.split())
        print(f"\n📊 Test: {site_count} sites, {days} days")
        print("-" * 40)

        elapsed_time, success, output = run_sync_test(site_ids, days)
        stats = extract_sync_stats(output)

        result = {
            "sites": site_ids,
            "site_count": site_count,
            "days": days,
            "elapsed_time": elapsed_time,
            "formatted_time": format_time(elapsed_time),
            "success": success,
            "stats": stats,
            "avg_time_per_site": elapsed_time / site_count if site_count > 0 else 0,
        }

        results.append(result)

        # Print results
        print(f"⏱️  Duration: {result['formatted_time']}")
        print(f"📈 Status: {'✅ Success' if success else '❌ Failed'}")
        print(f"📊 Stats: {stats['success']} succeeded, {stats['failed']} failed")
        print(f"⚡ Avg per site: {format_time(result['avg_time_per_site'])}")

        if not success:
            print("❗ Error output (last 500 chars):")
            print(output[-500:] if len(output) > 500 else output)

    # Summary
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE SUMMARY")
    print("=" * 60)

    total_time = sum(r["elapsed_time"] for r in results)
    total_sites = sum(r["site_count"] * r["days"] for r in results)

    print(f"\n🏁 Total test time: {format_time(total_time)}")
    print(f"📍 Total site-days synced: {total_sites}")
    print(
        f"⚡ Average time per site-day: {format_time(total_time / total_sites if total_sites > 0 else 0)}"
    )

    print("\n📈 Detailed Results:")
    print("-" * 60)
    print(f"{'Config':<15} {'Time':<12} {'Per Site':<12} {'Status':<10}")
    print("-" * 60)

    for r in results:
        config = f"{r['site_count']} sites, {r['days']}d"
        status = "✅" if r["success"] else "❌"
        print(
            f"{config:<15} {r['formatted_time']:<12} {format_time(r['avg_time_per_site']):<12} {status:<10}"
        )

    # Performance notes
    print("\n💡 Performance Notes:")
    print("- With latency fix: No exponential delay accumulation")
    print("- Dynamic delays: Only slows when approaching rate limits")
    print("- Retry count resets: Prevents cascading delays after errors")

    # Save results to JSON
    with open("sync_performance_results.json", "w") as f:
        json.dump(
            {
                "test_date": datetime.now().isoformat(),
                "results": results,
                "summary": {
                    "total_time": total_time,
                    "total_site_days": total_sites,
                    "avg_time_per_site_day": total_time / total_sites if total_sites > 0 else 0,
                },
            },
            f,
            indent=2,
        )

    print("\n💾 Results saved to: sync_performance_results.json")

    return 0 if all(r["success"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
