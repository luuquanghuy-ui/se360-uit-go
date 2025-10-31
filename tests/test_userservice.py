"""
Unit tests for UserService
Run with: pytest tests/test_userservice.py
"""
import pytest
import sys
import os

# Set required environment variables BEFORE importing modules
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars-minimum")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

# Add UserService to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'UserService'))

# Import only what we need, avoid importing main.py (has DB dependencies)
from auth import get_password_hash, verify_password, create_access_token

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

# Note: API endpoint tests removed to avoid database dependencies
# Use smoke_test.py for integration tests after deployment

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
