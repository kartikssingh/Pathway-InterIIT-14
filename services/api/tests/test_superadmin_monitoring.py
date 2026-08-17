"""
Test script to verify superadmin monitoring implementation.
Run this after migration to ensure everything works.
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
SUPERADMIN_TOKEN = "YOUR_SUPERADMIN_TOKEN_HERE"  # Replace with actual token

headers = {
    "Authorization": f"Bearer {SUPERADMIN_TOKEN}",
    "Content-Type": "application/json"
}


def test_dashboard():
    """Test superadmin dashboard endpoint"""
    print("\n" + "="*60)
    print("Testing Dashboard Endpoint")
    print("="*60)
    
    response = requests.get(
        f"{BASE_URL}/api/superadmin/dashboard?days=7",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✓ Dashboard endpoint working!")
        print(f"  System Status: {data['system_status']}")
        print(f"  Hit Rate: {data['metrics_summary']['alert_hit_rate']}%")
        print(f"  False Positive Rate: {data['metrics_summary']['false_positive_rate']}%")
        print(f"  Active Alerts: {len(data['active_system_alerts'])}")
        return True
    else:
        print(f"✗ Dashboard endpoint failed: {response.status_code}")
        print(f"  Error: {response.text}")
        return False


def test_audit_logs():
    """Test audit logs endpoint"""
    print("\n" + "="*60)
    print("Testing Audit Logs Endpoint")
    print("="*60)
    
    response = requests.get(
        f"{BASE_URL}/api/superadmin/audit-logs?limit=10",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Audit logs endpoint working!")
        print(f"  Retrieved {len(data)} audit logs")
        if data:
            print(f"  Latest: {data[0]['action_type']} by {data[0].get('admin_username', 'unknown')}")
        return True
    else:
        print(f"✗ Audit logs endpoint failed: {response.status_code}")
        print(f"  Error: {response.text}")
        return False


def test_metrics():
    """Test metrics endpoints"""
    print("\n" + "="*60)
    print("Testing Metrics Endpoints")
    print("="*60)
    
    # Test metrics summary
    response = requests.get(
        f"{BASE_URL}/api/superadmin/metrics/summary?days=7",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✓ Metrics summary endpoint working!")
        print(f"  Total Alerts: {data['total_alerts']}")
        print(f"  True Positives: {data['true_positives']}")
        print(f"  False Positives: {data['false_positives']}")
        print(f"  Unreviewed: {data['unreviewed']}")
    else:
        print(f"✗ Metrics summary failed: {response.status_code}")
        return False
    
    # Test alert resolutions
    response = requests.get(
        f"{BASE_URL}/api/superadmin/metrics/alert-resolutions?days=30",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✓ Alert resolutions endpoint working!")
        print(f"  Average Resolution Time: {data['avg_resolution_time_hours']:.2f} hours")
    else:
        print(f"✗ Alert resolutions failed: {response.status_code}")
        return False
    
    return True


def test_health_checks():
    """Test health checks endpoint"""
    print("\n" + "="*60)
    print("Testing Health Checks Endpoint")
    print("="*60)
    
    response = requests.get(
        f"{BASE_URL}/api/superadmin/health/checks?limit=10",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Health checks endpoint working!")
        print(f"  Retrieved {len(data)} health checks")
        if data:
            print(f"  Latest: {data[0]['component_name']} - {data[0]['status']}")
        return True
    else:
        print(f"✗ Health checks endpoint failed: {response.status_code}")
        print(f"  Error: {response.text}")
        return False


def test_system_alerts():
    """Test system alerts endpoint"""
    print("\n" + "="*60)
    print("Testing System Alerts Endpoint")
    print("="*60)
    
    response = requests.get(
        f"{BASE_URL}/api/superadmin/alerts?limit=10",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ System alerts endpoint working!")
        print(f"  Retrieved {len(data)} system alerts")
        if data:
            print(f"  Latest: {data[0]['title']} - {data[0]['severity']}")
        return True
    else:
        print(f"✗ System alerts endpoint failed: {response.status_code}")
        print(f"  Error: {response.text}")
        return False


def test_system_status():
    """Test system status endpoint"""
    print("\n" + "="*60)
    print("Testing System Status Endpoint")
    print("="*60)
    
    response = requests.get(
        f"{BASE_URL}/api/superadmin/system-status",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ System status endpoint working!")
        print(f"  Status: {data['status']}")
        print(f"  Critical Alerts: {data['critical_alerts']}")
        print(f"  Unresolved Errors: {data['unresolved_errors']}")
        return True
    else:
        print(f"✗ System status endpoint failed: {response.status_code}")
        print(f"  Error: {response.text}")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("SUPERADMIN MONITORING - VERIFICATION TESTS")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    print(f"Time: {datetime.now()}")
    
    if SUPERADMIN_TOKEN == "YOUR_SUPERADMIN_TOKEN_HERE":
        print("\n⚠️  WARNING: Please set SUPERADMIN_TOKEN in this script!")
        print("   1. Login as superadmin to get token")
        print("   2. Replace YOUR_SUPERADMIN_TOKEN_HERE with actual token")
        print("   3. Run this script again")
        return
    
    results = {
        "Dashboard": test_dashboard(),
        "Audit Logs": test_audit_logs(),
        "Metrics": test_metrics(),
        "Health Checks": test_health_checks(),
        "System Alerts": test_system_alerts(),
        "System Status": test_system_status()
    }
    
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:20} {status}")
    
    print("\n" + "="*60)
    print(f"Results: {passed}/{total} tests passed")
    print("="*60)
    
    if passed == total:
        print("\n🎉 All tests passed! Superadmin monitoring is working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check the errors above.")


if __name__ == "__main__":
    run_all_tests()
