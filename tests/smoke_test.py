#!/usr/bin/env python3
"""
Smoke tests for UIT-Go services after deployment
Run after deploying to verify basic functionality
"""
import requests
import sys
import time
import os  # <-- THÊM IMPORT NÀY
from typing import Dict

# --- SỬA LỖI: Đọc IP động từ Biến Môi Trường (do CI cung cấp) ---
# Lấy URL từ biến môi trường (do job 'smoke_test' trong deploy.yml cung cấp)
BASE_URL = os.environ.get("API_URL")
# Thêm prefix /api/users vì đang dùng Ingress routing
if BASE_URL:
    BASE_URL = f"{BASE_URL}/api/users"
# --- KẾT THÚC SỬA LỖI ---

# Internal service URLs (only accessible from within cluster)
INTERNAL_SERVICES = {
    "tripservice": "http://tripservice:8000",
    "driverservice": "http://driverservice:8000",
    "locationservice": "http://locationservice:8000",
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

# Đổi tên hàm (thêm _) để Pytest (trong job 'test') tự động bỏ qua
def _test_health_endpoint(service_name: str, url: str) -> bool:
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

# Đổi tên hàm (thêm _) để Pytest (trong job 'test') tự động bỏ qua
def _test_userservice_registration() -> bool:
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
        # --- SỬA LỖI 422: Đổi thành chữ hoa ---
        "user_type": "PASSENGER"
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

# Đổi tên hàm (thêm _) để Pytest (trong job 'test') tự động bỏ qua
def _test_userservice_login() -> Dict[str, str]:
    """Test user login flow"""
    log_test("Testing user login...", "info")

    # First, create a test user
    timestamp = int(time.time())
    register_payload = {
        "username": f"logintest_{timestamp}",
        "email": f"logintest_{timestamp}@test.com",
        "password": "testpass123",
        "full_name": "Login Test User",
        # --- SỬA LỖI 422: Đổi thành chữ hoa ---
        "user_type": "PASSENGER"
    }

    try:
        # Register user
        # Chúng ta dùng _test_userservice_registration để đảm bảo user được tạo đúng
        reg_payload = {
            "username": f"logintest_{timestamp}",
            "email": f"logintest_{timestamp}@test.com",
            "password": "testpass123",
            "full_name": "Login Test User",
            "user_type": "PASSENGER"
        }
        reg_response = requests.post(f"{BASE_URL}/auth/register", json=reg_payload, timeout=10)
        
        if reg_response.status_code != 201 and reg_response.status_code != 400:
             log_test(f"User login: FAILED (Không thể tạo user để test login, lỗi: {reg_response.text})", "fail")
             return {}

        # Login
        login_data = {
            "username": reg_payload["email"],
            "password": reg_payload["password"]
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
            print(f"Response: {response.text}")
            return {}

    except requests.exceptions.RequestException as e:
        log_test(f"User login: FAILED - {str(e)}", "fail")
        return {}

# Đổi tên hàm (thêm _) để Pytest (trong job 'test') tự động bỏ qua
def _test_root_endpoint() -> bool:
    """Test root endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=10)

        if response.status_code == 200:
            data = response.json()
            if "service" in data and "status" in data:
                log_test(f"Root endpoint: {data.get('service', 'Unknown')} - {data.get('status', 'Unknown')}", "pass")
                return True

        log_test(f"Root endpoint: FAILED (Status: {response.status_code})", "fail")
        return False

    except requests.exceptions.RequestException as e:
        log_test(f"Root endpoint: FAILED - {str(e)}", "fail")
        return False

def run_smoke_tests():
    """Run all smoke tests"""
    print("\n" + "="*60)
    print("🔥 UIT-Go Smoke Tests")
    print("="*60 + "\n")

    # --- SỬA LỖI: Kiểm tra BASE_URL trước khi chạy ---
    if not BASE_URL:
        log_test("Biến môi trường API_URL không được đặt. Thoát...", "fail")
        return 1
    # --- KẾT THÚC SỬA LỖI ---

    results = []

    # Test 1: Root endpoint
    log_test(f"Test 1: Root Endpoint ({BASE_URL}/)", "info")
    results.append(_test_root_endpoint()) # Đổi tên hàm
    print()

    # Test 2: Health check
    log_test(f"Test 2: Health Check ({BASE_URL}/health)", "info")
    results.append(_test_health_endpoint("UserService", BASE_URL)) # Đổi tên hàm
    print()

    # Test 3: User registration
    log_test(f"Test 3: User Registration ({BASE_URL}/auth/register)", "info")
    results.append(_test_userservice_registration()) # Đổi tên hàm
    print()

    # Test 4: User login
    log_test(f"Test 4: User Login ({BASE_URL}/auth/login)", "info")
    token_data = _test_userservice_login() # Đổi tên hàm
    results.append(bool(token_data))
    print()

    # Test 5: TripService health (internal)
    print()
    trip_url = INTERNAL_SERVICES["tripservice"]
    log_test(f"Test 5: TripService Health ({trip_url}/health)", "info")
    results.append(_test_health_endpoint("TripService", trip_url))
    print()

    # Test 6: LocationService health (internal)
    loc_url = INTERNAL_SERVICES["locationservice"]
    log_test(f"Test 6: LocationService Health ({loc_url}/health)", "info")
    results.append(_test_health_endpoint("LocationService", loc_url))
    print()

    # (Tuỳ chọn) Test 7: DriverService health (internal)
    drv_url = INTERNAL_SERVICES["driverservice"]
    log_test(f"Test 7: DriverService Health ({drv_url}/health)", "info")
    results.append(_test_health_endpoint("DriverService", drv_url))
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

