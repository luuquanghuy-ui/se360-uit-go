#!/usr/bin/env python3
"""
Smoke tests for UIT-Go services after deployment
Run after deploying to verify basic functionality
"""
import requests
import sys
import time
from typing import Dict

# Azure Production URL
BASE_URL = "http://4.144.174.255"

# Internal service URLs (only accessible from within cluster)
INTERNAL_SERVICES = {
    "tripservice": "http://tripservice:8000",
    "driverservice": "http://driverservice:8000",
    "locationservice": "http://locationservice:8000",
    "paymentservice": "http://paymentservice:8000"
}

class Color:
    """ANSI color codes"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def log_test(message: str, status: str = "info"):
    """Print formatted log message"""
    colors = {
        "pass": Color.GREEN,
        "fail": Color.RED,
        "info": Color.BLUE,
        "warn": Color.YELLOW
    }
    color = colors.get(status, Color.BLUE)
    symbol = "✅" if status == "pass" else "❌" if status == "fail" else "ℹ️"
    print(f"{color}{symbol} {message}{Color.END}")

def test_health_endpoint(service_name: str, url: str) -> bool:
    """Test health endpoint of a service"""
    try:
        response = requests.get(f"{url}/health", timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                log_test(f"{service_name}: Health check passed", "pass")
                return True
            else:
                log_test(f"{service_name}: Health check returned unhealthy status", "fail")
                return False
        else:
            log_test(f"{service_name}: Health check failed with status {response.status_code}", "fail")
            return False
    except requests.exceptions.RequestException as e:
        log_test(f"{service_name}: Health check failed - {str(e)}", "fail")
        return False

def test_userservice_registration() -> bool:
    """Test user registration flow"""
    log_test("Testing user registration...", "info")

    # Use timestamp to ensure unique email
    timestamp = int(time.time())
    payload = {
        "username": f"smoketest_{timestamp}",
        "email": f"smoketest_{timestamp}@test.com",
        "password": "testpass123",
        "full_name": "Smoke Test User",
        "phone": f"09{timestamp % 100000000}",
        "user_type": "passenger"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json=payload,
            timeout=10
        )

        if response.status_code == 201:
            log_test("User registration: SUCCESS", "pass")
            return True
        elif response.status_code == 400:
            # Email might already exist from previous test
            log_test("User registration: Email exists (acceptable)", "warn")
            return True
        else:
            log_test(f"User registration: FAILED with status {response.status_code}", "fail")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        log_test(f"User registration: FAILED - {str(e)}", "fail")
        return False

def test_userservice_login() -> Dict[str, str]:
    """Test user login flow"""
    log_test("Testing user login...", "info")

    # First, create a test user
    timestamp = int(time.time())
    register_payload = {
        "username": f"logintest_{timestamp}",
        "email": f"logintest_{timestamp}@test.com",
        "password": "testpass123",
        "full_name": "Login Test User",
        "user_type": "passenger"
    }

    try:
        # Register user
        requests.post(f"{BASE_URL}/auth/register", json=register_payload, timeout=10)

        # Login
        login_data = {
            "username": register_payload["email"],
            "password": register_payload["password"]
        }

        response = requests.post(
            f"{BASE_URL}/auth/login",
            data=login_data,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            if "access_token" in data:
                log_test("User login: SUCCESS", "pass")
                return data
            else:
                log_test("User login: No token in response", "fail")
                return {}
        else:
            log_test(f"User login: FAILED with status {response.status_code}", "fail")
            return {}

    except requests.exceptions.RequestException as e:
        log_test(f"User login: FAILED - {str(e)}", "fail")
        return {}

def test_root_endpoint() -> bool:
    """Test root endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=10)

        if response.status_code == 200:
            data = response.json()
            if "service" in data and "status" in data:
                log_test(f"Root endpoint: {data.get('service', 'Unknown')} - {data.get('status', 'Unknown')}", "pass")
                return True

        log_test("Root endpoint: FAILED", "fail")
        return False

    except requests.exceptions.RequestException as e:
        log_test(f"Root endpoint: FAILED - {str(e)}", "fail")
        return False

def run_smoke_tests():
    """Run all smoke tests"""
    print("\n" + "="*60)
    print("🔥 UIT-Go Smoke Tests")
    print("="*60 + "\n")

    results = []

    # Test 1: Root endpoint
    log_test("Test 1: Root Endpoint", "info")
    results.append(test_root_endpoint())
    print()

    # Test 2: Health check
    log_test("Test 2: Health Check", "info")
    results.append(test_health_endpoint("UserService", BASE_URL))
    print()

    # Test 3: User registration
    log_test("Test 3: User Registration", "info")
    results.append(test_userservice_registration())
    print()

    # Test 4: User login
    log_test("Test 4: User Login", "info")
    token_data = test_userservice_login()
    results.append(bool(token_data))
    print()

    # Summary
    print("="*60)
    passed = sum(results)
    total = len(results)

    if passed == total:
        log_test(f"All tests passed! ({passed}/{total})", "pass")
        print("="*60 + "\n")
        return 0
    else:
        log_test(f"Some tests failed. ({passed}/{total} passed)", "fail")
        print("="*60 + "\n")
        return 1

if __name__ == "__main__":
    exit_code = run_smoke_tests()
    sys.exit(exit_code)
