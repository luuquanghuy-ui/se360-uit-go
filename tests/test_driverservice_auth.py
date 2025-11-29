"""
Unit tests for DriverService auth utilities
Run with: pytest tests/test_driverservice_auth.py
"""
import pytest
import sys
import os

# Đặt biến môi trường cần thiết TRƯỚC khi import module
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-driver-service-32-characters-min")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

# Thêm DriverService vào PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "DriverService"))

from auth import get_password_hash, verify_password, create_access_token  # type: ignore


class TestDriverAuth:
    """Kiểm thử các hàm auth trong DriverService (hash mật khẩu, verify, JWT)."""

    def test_password_hashing(self):
        password = "driver-secret-pass"
        hashed = get_password_hash(password)

        # Hash khác plain text
        assert hashed != password

        # Verify đúng / sai
        assert verify_password(password, hashed) is True
        assert verify_password("wrong-pass", hashed) is False

    def test_password_truncation_long_input(self):
        """Mật khẩu quá dài vẫn được hash mà không lỗi (bcrypt 72 bytes)."""
        long_password = "x" * 100
        hashed = get_password_hash(long_password)
        assert isinstance(hashed, str) and hashed

    def test_create_access_token_structure(self):
        """Tạo JWT token hợp lệ về mặt cấu trúc."""
        data = {"sub": "driver@test.com", "type": "service"}
        token = create_access_token(data)

        assert isinstance(token, str)
        # JWT có 3 phần: header.payload.signature
        parts = token.split(".")
        assert len(parts) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


