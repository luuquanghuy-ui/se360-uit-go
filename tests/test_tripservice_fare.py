"""
Unit tests cho TripService fare calculation logic.
Chạy với: pytest tests/test_tripservice_fare.py
"""
import pytest
import sys
import os

# Thêm TripService vào PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "TripService"))

from models import VehicleTypeEnum  # type: ignore
from crud import calculate_estimated_fare  # type: ignore


class TestTripServiceFare:
    """Kiểm thử hàm tính giá cước ước tính của TripService."""

    @pytest.mark.parametrize(
        "distance_m, vehicle_type, expected",
        [
            # 2 chỗ: base 15000 + 5km * 8000 = 55000 → làm tròn = 55000
            (5000, VehicleTypeEnum.TWO_SEATER, 55000),
            # 4 chỗ: base 20000 + 5km * 10000 = 70000
            (5000, VehicleTypeEnum.FOUR_SEATER, 70000),
            # 7 chỗ: base 30000 + 5km * 15000 = 105000
            (5000, VehicleTypeEnum.SEVEN_SEATER, 105000),
        ],
    )
    def test_calculate_estimated_fare_basic(self, distance_m, vehicle_type, expected):
        fare = calculate_estimated_fare(distance_m, vehicle_type)
        assert fare == expected

    def test_calculate_estimated_fare_rounding(self):
        """Đảm bảo làm tròn về 1000 VND gần nhất."""
        # Với 1234m cho 4 chỗ:
        # distance_km = 1.234 → base 20000 + 1.234 * 10000 = 32340 → ~32000
        fare = calculate_estimated_fare(1234, VehicleTypeEnum.FOUR_SEATER)
        assert fare % 1000 == 0

    def test_calculate_estimated_fare_zero_distance(self):
        """Khoảng cách 0 vẫn phải ít nhất bằng base fare."""
        fare_two = calculate_estimated_fare(0, VehicleTypeEnum.TWO_SEATER)
        fare_four = calculate_estimated_fare(0, VehicleTypeEnum.FOUR_SEATER)
        fare_seven = calculate_estimated_fare(0, VehicleTypeEnum.SEVEN_SEATER)

        assert fare_two >= 15000
        assert fare_four >= 20000
        assert fare_seven >= 30000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


