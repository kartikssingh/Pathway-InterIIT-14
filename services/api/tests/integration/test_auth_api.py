#!/usr/bin/env python3
"""
Test script for authentication endpoints
"""
import requests
import json
from typing import Optional

BASE_URL = "http://localhost:8000"


def login(username: str, password: str) -> Optional[dict]:
    """Login and return token data"""
    print(f"\n🔐 Logging in as {username}...")
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        data={"username": username, "password": password}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Login successful! Role: {data['role']}")
        return data
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None


def get_current_admin(token: str):
    """Get current admin info"""
    print("\n👤 Getting current admin info...")
    response = requests.get(
        f"{BASE_URL}/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Username: {data['username']}, Role: {data['role']}")
        print(f"   Email: {data['email']}")
        return data
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")
        return None


def blacklist_user(token: str, user_id: int, reason: str):
    """Blacklist a user"""
    print(f"\n🚫 Blacklisting user {user_id}...")
    response = requests.post(
        f"{BASE_URL}/user/{user_id}/blacklist",
        params={"reason": reason},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ User blacklisted: {data['entity_id']}")
        print(f"   Reason: {data['blacklist_reason']}")
        return data
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")
        return None


def whitelist_user(token: str, user_id: int):
    """Remove user from blacklist"""
    print(f"\n✅ Whitelisting user {user_id}...")
    response = requests.post(
        f"{BASE_URL}/user/{user_id}/whitelist",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ User whitelisted: {data['entity_id']}")
        return data
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")
        return None


def get_audit_logs(token: str, filters: dict = None):
    """Get audit logs (superadmin only)"""
    print("\n📋 Fetching audit logs...")
    params = filters or {"limit": 10}
    response = requests.get(
        f"{BASE_URL}/api/auth/superadmin/logs",
        params=params,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Found {data['total']} total logs, showing {len(data['logs'])} logs:")
        for log in data['logs']:
            print(f"\n   📝 [{log['created_at']}]")
            print(f"      Admin: {log['admin_username']} ({log['admin_email']})")
            print(f"      Action: {log['action_type']}")
            print(f"      Description: {log['action_description']}")
            if log.get('target_type'):
                print(f"      Target: {log['target_type']} (ID: {log['target_id']}, Identifier: {log['target_identifier']})")
            if log.get('metadata'):
                print(f"      Metadata: {json.dumps(log['metadata'], indent=8)}")
        return data
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")
        return None


def create_admin(token: str, username: str, email: str, password: str, role: str = "admin"):
    """Create a new admin (superadmin only)"""
    print(f"\n➕ Creating new admin: {username}...")
    response = requests.post(
        f"{BASE_URL}/api/auth/superadmin/create-admin",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "username": username,
            "email": email,
            "password": password,
            "role": role
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Admin created: {data['username']} ({data['role']})")
        return data
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")
        return None


def list_admins(token: str):
    """List all admins (superadmin only)"""
    print("\n👥 Listing all admins...")
    response = requests.get(
        f"{BASE_URL}/api/auth/superadmin/admins",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Found {len(data['admins'])} admins:")
        for admin in data['admins']:
            print(f"\n   👤 {admin['username']} ({admin['role']})")
            print(f"      Email: {admin['email']}")
            print(f"      Active: {admin['is_active']}")
            print(f"      Created: {admin['created_at']}")
            if admin.get('last_login_at'):
                print(f"      Last Login: {admin['last_login_at']}")
        return data
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")
        return None


def logout(token: str):
    """Logout"""
    print("\n👋 Logging out...")
    response = requests.post(
        f"{BASE_URL}/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        print("✅ Logged out successfully")
        return True
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")
        return False


def main():
    print("=" * 60)
    print("🧪 Authentication System Test Suite")
    print("=" * 60)
    
    # Test 1: Login as admin
    admin_data = login("admin", "admin123")
    if not admin_data:
        print("\n❌ Cannot continue without successful login")
        return
    
    admin_token = admin_data["access_token"]
    
    # Test 2: Get current admin info
    get_current_admin(admin_token)
    
    # Test 3: Try to access superadmin endpoint (should fail)
    print("\n🔒 Testing admin access to superadmin endpoint (should fail)...")
    get_audit_logs(admin_token)
    
    # Test 4: Login as superadmin
    superadmin_data = login("superadmin", "superadmin123")
    if not superadmin_data:
        print("\n❌ Superadmin login failed")
        return
    
    superadmin_token = superadmin_data["access_token"]
    
    # Test 5: Get audit logs as superadmin
    get_audit_logs(superadmin_token, {"limit": 20})
    
    # Test 6: List all admins
    list_admins(superadmin_token)
    
    # Test 7: Blacklist a user (use admin token)
    print("\n" + "=" * 60)
    print("Testing user blacklist/whitelist operations...")
    print("=" * 60)
    
    # Note: Replace with actual user ID from your database
    test_user_id = 1
    blacklist_user(admin_token, test_user_id, "Testing blacklist functionality")
    
    # Test 8: Check audit logs again
    get_audit_logs(superadmin_token, {"action_type": "blacklist_user", "limit": 5})
    
    # Test 9: Whitelist the user
    whitelist_user(admin_token, test_user_id)
    
    # Test 10: Check audit logs for whitelist action
    get_audit_logs(superadmin_token, {"action_type": "whitelist_user", "limit": 5})
    
    # Test 11: Logout
    logout(admin_token)
    logout(superadmin_token)
    
    print("\n" + "=" * 60)
    print("✅ Test suite completed!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
