"""
Unit tests cho TripService fare calculation logic.
Chạy với: pytest tests/test_tripservice_fare.py
"""
import pytest
import sys
import os

# Mock database dependencies để tránh import conflicts
from unittest.mock import MagicMock

# Tạo mock database module
class MockDatabase:
    trips_collection = MagicMock()
    ratings_collection = MagicMock()

# Thêm mock vào sys.modules để crud.py import được
sys.modules['database'] = MockDatabase()

# Import trực tiếp bằng sys.path để tránh conflict
trip_service_path = os.path.join(os.path.dirname(__file__), "..", "TripService")
if trip_service_path not in sys.path:
    sys.path.insert(0, trip_service_path)

# Xóa LocationService khỏi path để tránh conflict
location_service_path = os.path.join(os.path.dirname(__file__), "..", "LocationService")
if location_service_path in sys.path:
    sys.path.remove(location_service_path)

# Import từ TripService với module prefix để tránh nhầm lẫn
import importlib.util

# Load TripService models.py trước
spec = importlib.util.spec_from_file_location("trip_models", os.path.join(trip_service_path, "models.py"))
trip_models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trip_models)

# Load TripService schemas.py
spec = importlib.util.spec_from_file_location("trip_schemas", os.path.join(trip_service_path, "schemas.py"))
trip_schemas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trip_schemas)

# Thêm models và schemas vào sys.modules để crud.py import được
sys.modules['models'] = trip_models
sys.modules['schemas'] = trip_schemas

# Load TripService crud.py
spec = importlib.util.spec_from_file_location("trip_crud", os.path.join(trip_service_path, "crud.py"))
trip_crud = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trip_crud)

# Sử dụng các import đã load
VehicleTypeEnum = trip_models.VehicleTypeEnum
calculate_estimated_fare = trip_crud.calculate_estimated_fare


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


