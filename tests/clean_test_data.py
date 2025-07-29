#!/usr/bin/env python3
"""Manual test data cleanup script."""

import argparse

from src.utils.test_cleanup import TestDataCleaner


def main():
    """Main cleanup function."""
    parser = argparse.ArgumentParser(description="Clean test data from GSC database")
    parser.add_argument(
        "--site-id",
        type=int,
        default=3,
        help="Site ID to clean (default: 3 for test site)",
    )
    parser.add_argument(
        "--days", type=int, default=7, help="Clean data from last N days (default: 7)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Delete ALL data for the site (use with caution!)",
    )
    parser.add_argument("--future", action="store_true", help="Also clean any future-dated data")

    args = parser.parse_args()

    cleaner = TestDataCleaner()

    print("🧹 GSC Test Data Cleanup Tool")
    print("=" * 50)
    print(f"Site ID: {args.site_id}")

    if args.all:
        print("⚠️  WARNING: This will delete ALL data for this site!")
        confirm = input("Are you sure? (yes/no): ")
        if confirm.lower() != "yes":
            print("Cancelled.")
            return

        result = cleaner.clean_test_site_data(args.site_id, days_to_keep=0)
    else:
        print(f"Cleaning data from last {args.days} days...")
        result = cleaner.clean_recent_days_data(args.site_id, args.days)

    print(f"\n✅ Cleaned {result['total']} records:")
    print(f"   - Performance data: {result['performance_data']}")
    print(f"   - Hourly rankings: {result['hourly_rankings']}")

    if args.future:
        print("\nChecking for future-dated data...")
        future_result = cleaner.clean_future_data()
        if future_result["total"] > 0:
            print(f"✅ Cleaned {future_result['total']} future-dated records:")
            print(f"   - Performance data: {future_result['performance_data']}")
            print(f"   - Hourly rankings: {future_result['hourly_rankings']}")
        else:
            print("No future-dated data found.")

    print("\n✨ Cleanup complete!")


if __name__ == "__main__":
    main()
