import time
from locust import HttpUser, task, between

class Admin(HttpUser):
    wait_time = between(1, 5)
    
    def on_start(self):
        self.client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    

