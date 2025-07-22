#!/usr/bin/env python3
"""
Export page keyword performance data to CSV file
"""

import csv
from datetime import datetime
from pathlib import Path

import requests

# Configuration
BASE_URL = "http://localhost:8000"
ENDPOINT = "/api/v1/page-keyword-performance/"
OUTPUT_DIR = Path(__file__).parent / "exports"


def fetch_page_keyword_data(site_id=None, hostname=None, days=None, max_results=1000):
    """Fetch data from the API endpoint"""

    # Build request payload
    payload = {"max_results": max_results}

    if site_id:
        payload["site_id"] = site_id
    elif hostname:
        payload["hostname"] = hostname
    else:
        raise ValueError("Either site_id or hostname must be provided")

    if days:
        payload["days"] = days

    # Make API request
    try:
        response = requests.post(
            f"{BASE_URL}{ENDPOINT}", json=payload, headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: API returned status code {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to API server")
        print("Please ensure the server is running: just dev-server")
        return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None


def export_to_csv(data, output_filename):
    """Export API response data to CSV file"""

    if not data or not data.get("data"):
        print("No data to export")
        return False

    # Create output directory if it doesn't exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / output_filename

    try:
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            # Define CSV columns
            fieldnames = [
                "url",
                "total_clicks",
                "total_impressions",
                "avg_ctr",
                "avg_position",
                "keyword_count",
                "keywords",
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Write data rows
            for item in data["data"]:
                row = {
                    "url": item["url"],
                    "total_clicks": item["total_clicks"],
                    "total_impressions": item["total_impressions"],
                    "avg_ctr": f"{item['avg_ctr']:.2f}%",
                    "avg_position": f"{item['avg_position']:.1f}",
                    "keyword_count": item["keyword_count"],
                    "keywords": " | ".join(item["keywords"]),  # Join keywords with separator
                }
                writer.writerow(row)

        print(f"✅ Data exported successfully to: {output_path}")
        return True

    except Exception as e:
        print(f"Error writing CSV file: {str(e)}")
        return False


def main():
    """Main function to fetch and export data"""

    print("Page Keyword Performance Data Export")
    print("=" * 50)

    # Configuration - adjust these values as needed
    SITE_ID = 1  # Change this to your site ID
    DAYS = 30  # Last 30 days, set to None for all time
    MAX_RESULTS = 5000  # Maximum number of results to fetch

    # Generate output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"page_keywords_site{SITE_ID}_{timestamp}.csv"

    print(f"Fetching data for site ID: {SITE_ID}")
    print(f"Time range: Last {DAYS} days" if DAYS else "Time range: All time")
    print(f"Max results: {MAX_RESULTS}")
    print()

    # Fetch data from API
    print("Fetching data from API...")
    data = fetch_page_keyword_data(site_id=SITE_ID, days=DAYS, max_results=MAX_RESULTS)

    if data:
        print(f"✅ Received {data['total_results']} results")
        print(f"Time range: {data['time_range']}")

        # Show preview of top 5 results
        if data["data"]:
            print("\nTop 5 pages by clicks:")
            for i, item in enumerate(data["data"][:5], 1):
                print(f"{i}. {item['url'][:60]}...")
                print(f"   Clicks: {item['total_clicks']:,} | Keywords: {item['keyword_count']}")

        # Export to CSV
        print("\nExporting to CSV...")
        export_to_csv(data, output_filename)

        # Summary statistics
        if data["data"]:
            total_clicks = sum(item["total_clicks"] for item in data["data"])
            total_impressions = sum(item["total_impressions"] for item in data["data"])
            print("\nSummary:")
            print(f"  Total pages: {len(data['data'])}")
            print(f"  Total clicks: {total_clicks:,}")
            print(f"  Total impressions: {total_impressions:,}")
            if total_impressions > 0:
                print(f"  Overall CTR: {(total_clicks / total_impressions * 100):.2f}%")
    else:
        print("❌ Failed to fetch data from API")


def export_multiple_sites(site_ids):
    """Export data for multiple sites"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for site_id in site_ids:
        print(f"\n{'=' * 50}")
        print(f"Processing site ID: {site_id}")

        data = fetch_page_keyword_data(site_id=site_id, days=30, max_results=1000)

        if data:
            output_filename = f"page_keywords_site{site_id}_{timestamp}.csv"
            export_to_csv(data, output_filename)
        else:
            print(f"❌ Failed to fetch data for site {site_id}")


if __name__ == "__main__":
    # Single site export
    main()

    # Uncomment below to export multiple sites
    # export_multiple_sites([1, 2, 3, 4, 5])
