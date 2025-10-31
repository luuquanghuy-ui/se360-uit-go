"""
Unit tests for UserService
Run with: pytest tests/test_userservice.py
"""
import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add UserService to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'UserService'))

from main import app
from auth import get_password_hash, verify_password, create_access_token

client = TestClient(app)

class TestAuth:
    """Test authentication functions"""

    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "testpassword123"
        hashed = get_password_hash(password)

        # Hash should be different from original
        assert hashed != password

        # Should verify correctly
        assert verify_password(password, hashed) == True

        # Should fail with wrong password
        assert verify_password("wrongpassword", hashed) == False

    def test_password_truncation(self):
        """Test that long passwords are truncated properly"""
        # Password > 72 bytes
        long_password = "a" * 100
        hashed = get_password_hash(long_password)

        # Should not raise exception
        assert hashed is not None

    def test_create_access_token(self):
        """Test JWT token creation"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)

        # Token should be a string
        assert isinstance(token, str)

        # Token should have 3 parts (header.payload.signature)
        assert len(token.split('.')) == 3

class TestEndpoints:
    """Test API endpoints"""

    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "status" in data
        assert data["status"] == "running"

    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = client.get("/health")

        # Should return 200 or 503
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "userservice"

class TestValidation:
    """Test input validation"""

    def test_registration_missing_fields(self):
        """Test registration with missing required fields"""
        payload = {
            "email": "test@example.com"
            # Missing username, password, user_type
        }

        response = client.post("/auth/register", json=payload)
        assert response.status_code == 422  # Validation error

    def test_registration_invalid_email(self):
        """Test registration with invalid email"""
        payload = {
            "username": "testuser",
            "email": "not-an-email",
            "password": "testpass123",
            "user_type": "passenger"
        }

        response = client.post("/auth/register", json=payload)
        assert response.status_code == 422

    def test_registration_short_password(self):
        """Test registration with password < 8 characters"""
        payload = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "short",
            "user_type": "passenger"
        }

        response = client.post("/auth/register", json=payload)
        assert response.status_code == 422

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
