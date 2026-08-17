#!/usr/bin/env python3
"""
Quick test script for Dashboard API endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_endpoint(name, method, url, data=None):
    """Test an API endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")
    
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code < 400:
            print("✅ Success!")
            result = response.json()
            print(json.dumps(result, indent=2)[:500])  # Print first 500 chars
        else:
            print("❌ Error!")
            print(response.text)
    except Exception as e:
        print(f"❌ Exception: {e}")

def main():
    print("=" * 60)
    print("Dashboard API Endpoint Tests")
    print("=" * 60)
    
    # Test 1: Dashboard Summary (Enhanced)
    test_endpoint(
        "Dashboard Summary (Enhanced)",
        "GET",
        f"{BASE_URL}/dashboard/summary"
    )
    
    # Test 2: Risk Distribution
    test_endpoint(
        "Risk Distribution",
        "GET",
        f"{BASE_URL}/dashboard/risk-distribution"
    )
    
    # Test 3: Flagged Transactions
    test_endpoint(
        "Flagged Transactions",
        "GET",
        f"{BASE_URL}/dashboard/flagged-transactions?limit=5"
    )
    
    # Test 4: Critical Alerts
    test_endpoint(
        "Critical Alerts",
        "GET",
        f"{BASE_URL}/dashboard/critical-alerts?limit=5&severity=all&hours=24"
    )
    
    # Test 5: Live Alerts
    test_endpoint(
        "Live Alerts",
        "GET",
        f"{BASE_URL}/dashboard/live-alerts?limit=10"
    )
    
    # Test 6: Alert Trend
    test_endpoint(
        "Alert Trend",
        "GET",
        f"{BASE_URL}/dashboard/alert-trend?period=1h&interval=5m"
    )
    
    print("\n" + "=" * 60)
    print("All GET endpoint tests completed!")
    print("=" * 60)
    print("\nNote: POST endpoints (dismiss, create case, place hold)")
    print("require existing data and will be tested separately.")

if __name__ == "__main__":
    main()
