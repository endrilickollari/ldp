#!/usr/bin/env python3
"""
License System Demo Script

This script demonstrates the complete license system workflow:
1. User registration
2. Login
3. Attempt to access protected endpoint (should fail)
4. Check license pricing
5. Purchase license
6. Activate license
7. Access protected endpoint (should succeed)
8. Check license status
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"
email = f"demo_user_{int(time.time())}@example.com"
username = f"demo_user_{int(time.time())}"
password = "demopassword123"

def print_response(title, response):
    print(f"\n{'='*50}")
    print(f"{title}")
    print(f"{'='*50}")
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
    except:
        print(f"Response: {response.text}")

def main():
    print("🚀 Starting License System Demo")
    
    # 1. User Registration
    print("\n📝 Step 1: Registering user...")
    register_data = {
        "email": email,
        "username": username,
        "full_name": "Demo User",
        "password": password,
        "user_type": "solo"
    }
    
    response = requests.post(f"{BASE_URL}/v1/auth/register", json=register_data)
    print_response("User Registration", response)
    
    if response.status_code != 201:
        print("❌ Registration failed!")
        return
    
    # 2. Login
    print("\n🔐 Step 2: Logging in...")
    login_data = {
        "username": email,
        "password": password
    }
    
    response = requests.post(
        f"{BASE_URL}/v1/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    print_response("User Login", response)
    
    if response.status_code != 200:
        print("❌ Login failed!")
        return
    
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Try to access protected endpoint (should fail)
    print("\n🚫 Step 3: Attempting to access protected endpoint without license...")
    # Create a dummy file for testing
    test_file_content = "This is a test document for license demo."
    files = {"file": ("test_document.txt", test_file_content, "text/plain")}
    
    response = requests.post(f"{BASE_URL}/v1/jobs", headers=headers, files=files)
    print_response("Create Job (Without License)", response)
    
    # 4. Check license pricing
    print("\n💰 Step 4: Checking license pricing...")
    response = requests.get(f"{BASE_URL}/v1/licenses/pricing")
    print_response("License Pricing", response)
    
    # 5. Purchase license
    print("\n🛒 Step 5: Purchasing premium monthly license...")
    purchase_data = {
        "plan_type": "premium",
        "duration": "monthly", 
        "payment_method": "credit_card",
        "payment_id": f"pay_demo_{int(time.time())}"
    }
    
    response = requests.post(f"{BASE_URL}/v1/licenses/purchase", 
                           json=purchase_data, headers=headers)
    print_response("Purchase License", response)
    
    if response.status_code != 201:
        print("❌ License purchase failed!")
        return
    
    license_key = response.json()["license_key"]
    
    # 6. Activate license (admin action)
    print("\n✅ Step 6: Activating license...")
    response = requests.post(f"{BASE_URL}/v1/licenses/activate/{license_key}",
                           json={"payment_confirmed": True})
    print_response("Activate License", response)
    
    # 7. Check license status
    print("\n📊 Step 7: Checking license status...")
    response = requests.get(f"{BASE_URL}/v1/licenses/status", headers=headers)
    print_response("License Status", response)
    
    # 8. Try protected endpoint again (should succeed)
    print("\n✅ Step 8: Attempting to access protected endpoint with valid license...")
    files = {"file": ("test_document.txt", test_file_content, "text/plain")}
    response = requests.post(f"{BASE_URL}/v1/jobs", headers=headers, files=files)
    print_response("Create Job (With License)", response)
    
    if response.status_code == 202:
        job_id = response.json()["job_id"]
        print(f"\n✅ Success! Job created with ID: {job_id}")
        
        # Check job status
        print("\n📋 Checking job status...")
        response = requests.get(f"{BASE_URL}/v1/jobs/{job_id}", headers=headers)
        print_response("Job Status", response)
    
    # 9. List user licenses
    print("\n📄 Step 9: Listing user licenses...")
    response = requests.get(f"{BASE_URL}/v1/licenses/my-licenses", headers=headers)
    print_response("My Licenses", response)
    
    print("\n🎉 License System Demo Complete!")
    print(f"💡 Demo user: {email}")
    print(f"🔑 License key: {license_key}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
