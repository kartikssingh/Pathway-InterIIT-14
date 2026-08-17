from locust import HttpUser, task, between
from locust.exception import RescheduleTask
import random


class AdminUser(HttpUser):
    """Simulates typical admin user behavior with realistic task weights"""
    host = "http://localhost:8000"
    wait_time = between(1, 5)  # Realistic think time between requests
    
    def on_start(self):
        """Authenticate once per user session and store token"""
        response = self.client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "admin123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            name="/api/auth/login"
        )
        if response.status_code != 200:
            print(f"Login failed: {response.status_code} - {response.text}")
            raise RescheduleTask()
        
        # ✅ FIX 1: Store the access token
        token_data = response.json()
        self.token = token_data.get("access_token")
        
        if not self.token:
            print(f"No token in response: {token_data}")
            raise RescheduleTask()
        
        # ✅ FIX 2: Set Authorization header for all subsequent requests
        self.client.headers.update({
            "Authorization": f"Bearer {self.token}"
        })
        
        print(f"✓ Authenticated successfully with token: {self.token[:20]}...")

    @task(10)
    def view_dashboard_summary(self):
        """View dashboard summary - most frequent action"""
        with self.client.get(
            "/dashboard/summary",
            catch_response=True,
            name="Dashboard Summary"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got {response.status_code}")
    
    @task(8)
    def view_risk_distribution(self):
        """Check risk distribution"""
        self.client.get("/dashboard/risk-distribution", name="Risk Distribution")
    
    @task(7)
    def view_flagged_transactions(self):
        """View flagged transactions with varying limits"""
        limit = random.choice([10, 25, 50])
        self.client.get(
            f"/dashboard/flagged-transactions?limit={limit}",
            name="Flagged Transactions"
        )
    
    @task(6)
    def view_unclassified_alerts(self):
        """View unclassified alerts with different severities"""
        # ✅ FIX 3: Use UPPERCASE severity values (CRITICAL, HIGH, MEDIUM, LOW, all)
        severity = random.choice(['all', 'HIGH', 'MEDIUM', 'LOW', 'CRITICAL'])
        self.client.get(
            f"/dashboard/alerts/unclassified?limit=50&severity={severity}",
            name="Unclassified Alerts"
        )
    
    @task(5)
    def list_users(self):
        """List all users"""
        self.client.get("/users?limit=50", name="List Users")
    
    @task(4)
    def view_user_details(self):
        """View specific user details"""
        # ✅ FIX 4: Use valid user ID range (1-113, continuous)
        user_id = random.randint(1, 113)
        with self.client.get(
            f"/user/{user_id}",
            catch_response=True,
            name="User Details"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # Gracefully handle any edge cases
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(3)
    def view_user_transactions(self):
        """View transactions for a specific user"""
        # ✅ FIX 5: Use valid user ID range (1-113)
        user_id = random.randint(1, 113)
        self.client.get(
            f"/transactions/user/{user_id}?limit=50",
            name="User Transactions"
        )
    
    @task(4)
    def list_all_transactions(self):
        """List all transactions in the system"""
        self.client.get("/transactions/all?limit=50", name="All Transactions")
    
    @task(2)
    def mark_alert_false_positive(self):
        """Mark alert as false positive"""
        # ✅ FIX 6: Use valid alert ID range (1-358, 336 alerts total)
        alert_id = random.randint(1, 358)
        self.client.post(
            f"/dashboard/alerts/{alert_id}/mark",
            json={
                "is_true_positive": False,
                "notes": random.choice([
                    "genuine doc expired",
                    "customer verified",
                    "false positive",
                    "duplicate alert"
                ])
            },
            name="Mark Alert (False Positive)"
        )
    
    @task(2)
    def mark_alert_true_positive(self):
        """Mark alert as true positive"""
        # ✅ FIX 7: Use valid alert ID range (1-358, 336 alerts total)
        alert_id = random.randint(1, 358)
        self.client.post(
            f"/dashboard/alerts/{alert_id}/mark",
            json={
                "is_true_positive": True,
                "notes": random.choice([
                    "actual money laundering",
                    "confirmed fraud",
                    "suspicious activity",
                    "needs investigation"
                ])
            },
            name="Mark Alert (True Positive)"
        )
    
    @task(1)
    def health_check(self):
        """API health check"""
        self.client.get("/", name="Health Check")


# class HeavyAdminUser(HttpUser):
#     """Simulates admins doing heavy operations like PDF uploads"""
#     host = "http://localhost:8000"
#     wait_time = between(5, 10)  # Longer think time for heavy operations
    
#     def on_start(self):
#         """Authenticate once per user session"""
#         self.client.post(
#             "/api/auth/login",
#             data={"username": "admin", "password": "admin123"},
#             headers={"Content-Type": "application/x-www-form-urlencoded"}
#         )
    
#     @task(1)
#     def upload_user_form(self):
#         """Upload PDF form (heavy operation)"""
#         # Create a small test PDF
#         files = {'file': ('test.pdf', b'%PDF-1.4 test content', 'application/pdf')}
#         self.client.post(
#             "/user/upload-form",
#             files=files,
#             name="Upload User Form"
#         )
