#!/usr/bin/env python3
"""
Test script for GSC MCP functions via Flask API
"""
import requests
import json
from datetime import datetime, timedelta

# Flask server URL
BASE_URL = "http://localhost:5000"
SITE = "sc-domain:urbanlifehk.com"

def print_result(title, result):
    """Pretty print test results"""
    print(f"\n{'='*60}")
    print(f"TEST: {title}")
    print(f"{'='*60}")
    if isinstance(result, dict):
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif isinstance(result, list):
        print(f"Total results: {len(result)}")
        if result:
            print("\nFirst 3 results:")
            for i, item in enumerate(result[:3]):
                print(f"\n--- Result {i+1} ---")
                print(json.dumps(item, indent=2, ensure_ascii=False))
    else:
        print(result)

def test_track_pages():
    """Test track_pages endpoint"""
    response = requests.post(f"{BASE_URL}/track_pages", json={
        "site": SITE,
        "pages": ["https://urbanlifehk.com/article/108958/香港行山好去處/"],
        "keywords": [],
        "days": 30
    })
    
    data = response.json()
    print_result("Track Pages", data)

def test_compare_periods():
    """Test compare_periods endpoint"""
    response = requests.post(f"{BASE_URL}/compare_periods", json={
        "site": SITE,
        "period_type": "week"
    })
    
    data = response.json()
    print_result("Compare Periods (Week)", data)

def test_pages_queries():
    """Test pages_queries endpoint"""
    response = requests.post(f"{BASE_URL}/pages_queries", json={
        "site": SITE,
        "pages": ["https://urbanlifehk.com/article/108958/香港行山好去處/"]
    })
    
    data = response.json()
    print_result("Pages Queries", data)

def test_query():
    """Test a custom SQL query"""
    # First let's test with the query endpoint to check the data structure
    print("\n" + "="*60)
    print("TEST: Custom Query - Check Data Structure")
    print("="*60)
    
    # Import the gsc_mcp module to use its functions directly
    import sys
    sys.path.append('/Users/rose/Downloads/01_工作相關/面試求職/PressLogic/gsc_db')
    from gsc_mcp import query, best_pages, show_page_queries, search_keywords, show_keyword_pages, track_pages, pages_queries, compare_periods
    
    # Test 1: Check data structure
    result = query(SITE, "SELECT * FROM {site} LIMIT 5")
    print_result("Data Structure Check", result)
    
    # Test 2: Best pages
    result = best_pages(SITE, days=30, limit=5)
    print_result("Best Pages (Last 30 Days)", result)
    
    # Test 3: Show page queries (if we have pages)
    if len(result) > 0 and 'page' in result[0]:
        test_page = result[0]['page']
        page_queries = show_page_queries(SITE, test_page, days=30)
        print_result(f"Queries for page: {test_page[:50]}...", page_queries)
    
    # Test 4: Search keywords
    keyword_results = search_keywords(SITE, "%香港%", days=30)
    print_result("Keywords containing '香港'", keyword_results)
    
    # Test 5: Show keyword pages
    if len(keyword_results) > 0:
        test_keyword = keyword_results[0]['query']
        keyword_pages = show_keyword_pages(SITE, test_keyword, days=30)
        print_result(f"Pages for keyword: {test_keyword}", keyword_pages)
    
    # Test 6: Track specific pages
    track_result = track_pages(SITE, ["https://urbanlifehk.com/"], [], days=7)
    print_result("Track Homepage (7 days)", track_result)
    
    # Test 7: Pages queries for multiple pages
    if len(result) >= 2:
        test_pages = [item['page'] for item in result[:2]]
        pages_q_result = pages_queries(SITE, test_pages)
        print_result("Queries for top 2 pages", pages_q_result)
    
    # Test 8: Compare periods
    compare_result = compare_periods(SITE, "week")
    print_result("Compare This Week vs Last Week", compare_result)

def test_intent_analysis():
    """Test intent_analysis_data endpoint"""
    response = requests.post(f"{BASE_URL}/intent_analysis_data", json={
        "site": SITE,
        "days": 30
    })
    
    # This endpoint returns CSV, not JSON
    if response.status_code == 200:
        print("\n" + "="*60)
        print("TEST: Intent Analysis Data")
        print("="*60)
        print("CSV Response (first 500 chars):")
        print(response.text[:500] + "..." if len(response.text) > 500 else response.text)
    else:
        print(f"Error: {response.status_code}")

def main():
    """Run all tests"""
    print("Starting GSC MCP Function Tests")
    print(f"Testing against: {BASE_URL}")
    print(f"Site: {SITE}")
    
    try:
        # Test direct Python functions first
        test_query()
        
        # Then test Flask API endpoints
        test_track_pages()
        test_compare_periods()
        test_pages_queries()
        test_intent_analysis()
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()