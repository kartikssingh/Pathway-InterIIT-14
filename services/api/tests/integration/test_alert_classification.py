"""
Test script for alert classification feature
Tests the new endpoint to mark alerts as true/false positive
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
ALERT_ID = 1  # Change this to a valid alert ID in your database

# You'll need to get a valid admin token first
# Run this after logging in as an admin
ADMIN_TOKEN = "your_admin_token_here"

def test_mark_alert_positive():
    """Test marking an alert as true positive"""
    print("\n" + "="*60)
    print("TEST: Mark Alert as TRUE POSITIVE")
    print("="*60)
    
    response = requests.post(
        f"{BASE_URL}/dashboard/alerts/{ALERT_ID}/mark",
        headers={
            "Authorization": f"Bearer {ADMIN_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "is_true_positive": True,
            "notes": "Test: Confirmed suspicious activity"
        }
    )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("✅ Successfully marked alert as TRUE POSITIVE")
    else:
        print("❌ Failed to mark alert")


def test_mark_alert_negative():
    """Test marking an alert as false positive"""
    print("\n" + "="*60)
    print("TEST: Mark Alert as FALSE POSITIVE")
    print("="*60)
    
    response = requests.post(
        f"{BASE_URL}/dashboard/alerts/{ALERT_ID}/mark",
        headers={
            "Authorization": f"Bearer {ADMIN_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "is_true_positive": False,
            "notes": "Test: Verified legitimate transaction"
        }
    )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("✅ Successfully marked alert as FALSE POSITIVE")
    else:
        print("❌ Failed to mark alert")


def test_get_unclassified_alerts():
    """Fetch unclassified alerts that need review"""
    print("\n" + "="*60)
    print("TEST: Get Unclassified Alerts")
    print("="*60)
    
    response = requests.get(
        f"{BASE_URL}/dashboard/alerts/unclassified?limit=50",
        headers={
            "Authorization": f"Bearer {ADMIN_TOKEN}",
        }
    )
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n📊 Total unclassified alerts: {data.get('total')}")
        print(f"📋 Showing first {len(data.get('items', []))} alerts:")
        
        for alert in data.get('items', [])[:5]:  # Show first 5
            print(f"\n  Alert ID: {alert.get('id')}")
            print(f"    Type: {alert.get('alert_type')}")
            print(f"    Severity: {alert.get('severity')}")
            print(f"    Title: {alert.get('title')}")
            print(f"    Status: {alert.get('status')}")
            print(f"    Classification: {alert.get('is_true_positive')} (should be null)")
        
        print("\n✅ Successfully fetched unclassified alerts")
    else:
        print(f"❌ Failed to fetch unclassified alerts")
        print(f"Response: {response.text}")


def test_get_alert_details():
    """Fetch alert details to verify classification was saved"""
    print("\n" + "="*60)
    print("TEST: Get All Alerts (with classification status)")
    print("="*60)
    
    response = requests.get(
        f"{BASE_URL}/dashboard/critical-alerts?limit=100",
        headers={
            "Authorization": f"Bearer {ADMIN_TOKEN}",
        }
    )
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        alerts = response.json()
        
        # Count classification status
        total = len(alerts)
        classified = sum(1 for a in alerts if a.get('is_true_positive') is not None)
        unclassified = total - classified
        
        print(f"\n📊 Alert Statistics:")
        print(f"  Total: {total}")
        print(f"  Classified: {classified}")
        print(f"  Unclassified: {unclassified}")
        
        print(f"\n📋 First 5 alerts:")
        for alert in alerts[:5]:
            print(f"\n  Alert ID: {alert.get('id')}")
            print(f"    Type: {alert.get('alert_type')}")
            print(f"    Severity: {alert.get('severity')}")
            
            classification = alert.get('is_true_positive')
            if classification is True:
                print(f"    Classification: ✅ TRUE POSITIVE")
            elif classification is False:
                print(f"    Classification: ❌ FALSE POSITIVE")
            else:
                print(f"    Classification: ⚠️  UNCLASSIFIED")
            
            print(f"    Reviewed At: {alert.get('reviewed_at')}")
            print(f"    Reviewed By: {alert.get('reviewed_by')}")
    else:
        print("❌ Failed to fetch alerts")


if __name__ == "__main__":
    print("="*60)
    print("ALERT CLASSIFICATION FEATURE TEST")
    print("="*60)
    print("\n⚠️  IMPORTANT: Update ADMIN_TOKEN and ALERT_ID before running!")
    print(f"\nTesting against: {BASE_URL}")
    print(f"Alert ID: {ALERT_ID}")
    
    # Uncomment the tests you want to run
    # Make sure to update ADMIN_TOKEN first!
    
    if ADMIN_TOKEN == "your_admin_token_here":
        print("\n❌ Please update ADMIN_TOKEN in the script before running")
        print("\nTo get a token:")
        print("1. Start the server: uvicorn app.main:app --reload")
        print("2. Login as admin: POST /auth/login")
        print("3. Copy the access_token from response")
        print("4. Update ADMIN_TOKEN in this script")
    else:
        # Run tests
        test_get_unclassified_alerts()
        input("\nPress Enter to test marking alert as positive...")
        test_mark_alert_positive()
        input("\nPress Enter to test marking as negative...")
        test_mark_alert_negative()
        input("\nPress Enter to view all alert details...")
        test_get_alert_details()
        input("\nPress Enter to check unclassified alerts again...")
        test_get_unclassified_alerts()
