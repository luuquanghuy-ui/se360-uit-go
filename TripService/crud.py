from typing import List, Optional, Any, Dict
from bson import ObjectId
from database import trips_collection, ratings_collection
import models
import schemas
from datetime import datetime
import requests
import httpx
import logging
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
# import polyline  # Uncomment if you install polyline package


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MY_CLIENT_ID = os.getenv("MY_CLIENT_ID")
MY_CLIENT_SECRET = os.getenv("MY_CLIENT_SECRET")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL")
DRIVER_SERVICE_URL = os.getenv("DRIVER_SERVICE_URL")
LOCATION_SERVICE_URL = os.getenv("LOCATION_SERVICE_URL")

_service_token_cache: Optional[str] = None
_token_expiry_time: Optional[datetime] = None



# Mapbox API configuration
MAPBOX_ACCESS_TOKEN = os.getenv("MAPBOX_ACCESS_TOKEN", "pk.your_mapbox_token_here")
LOCATION_SERVICE_URL = os.getenv("LOCATION_SERVICE_URL", "http://locationservice:8000")
DRIVER_SERVICE_URL = os.getenv("DRIVER_SERVICE_URL", "http://driverservice:8000")
def convert_objectid(doc):
    """Convert ObjectId to string for Pydantic models"""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

async def get_trip_by_id(trip_id: str) -> Optional[dict]:
    """Get trip by ObjectId"""
    if not ObjectId.is_valid(trip_id):
        return None
    doc = await trips_collection.find_one({"_id": ObjectId(trip_id)})
    return convert_objectid(doc)

async def get_trips_by_passenger(passenger_id: str, skip: int = 0, limit: int = 100) -> List[dict]:
    """Get trips by passenger ID"""
    cursor = trips_collection.find({"passenger_id": passenger_id}).skip(skip).limit(limit).sort("created_at", -1)
    return await cursor.to_list(length=limit)

async def get_trips_by_driver(driver_id: str, skip: int = 0, limit: int = 100) -> List[dict]:
    """Get trips by driver ID"""
    cursor = trips_collection.find({"driver_id": driver_id}).skip(skip).limit(limit).sort("created_at", -1)
    return await cursor.to_list(length=limit)

async def get_available_trips(skip: int = 0, limit: int = 100) -> List[dict]:
    """Get available trips (status = PENDING)"""
    cursor = trips_collection.find({"status": models.TripStatusEnum.PENDING.value}).skip(skip).limit(limit).sort("created_at", -1)
    return await cursor.to_list(length=limit)

async def get_trips_near_location(longitude: float, latitude: float, max_distance: int = 5000, limit: int = 50) -> List[dict]:
    """Get trips near specific location using GeoJSON"""
    cursor = trips_collection.find({
        "pickup.location": {
            "$near": {
                "$geometry": {
                    "type": "Point",
                    "coordinates": [longitude, latitude]
                },
                "$maxDistance": max_distance  
            }
        },
        "status": models.TripStatusEnum.PENDING.value
    }).limit(limit)
    return await cursor.to_list(length=limit)

async def get_coordinates(location_name: str) -> tuple | None:
    """Hàm này nhận tên một địa điểm và trả về tọa độ (kinh độ, vĩ độ)."""
    geocoding_url = "https://api.mapbox.com/search/geocode/v6/forward"
    params = {
        'q': location_name,
        'access_token': MAPBOX_ACCESS_TOKEN,
        'limit': 1
    }
    
    logger.info(f"Mapbox: Requesting geocoding for: {location_name}")
    
    try:
        # Sử dụng httpx thay vì requests để bất đồng bộ
        async with httpx.AsyncClient() as client:
            response = await client.get(geocoding_url, params=params)
            response.raise_for_status()
            data = response.json()
        
        if data.get("features"):
            coords = data["features"][0]["geometry"]["coordinates"]
            return (coords[0], coords[1])  
        else:
            logger.warning(f"Mapbox: No features found for location: {location_name}")
            return None
            
    except httpx.RequestError as e:
        logger.error(f"Mapbox API (Geocoding) error: {e}")
        raise e # Ném lỗi ra để main.py bắt


async def get_route_info(pickup_coords: tuple[float, float], dropoff_coords: tuple[float, float], vehicle_type: models.VehicleTypeEnum) -> dict | None:
    """Get route information from Mapbox Directions API"""
    directions_url = "https://api.mapbox.com/directions/v5/mapbox/driving"
    coordinates = f"{pickup_coords[0]},{pickup_coords[1]};{dropoff_coords[0]},{dropoff_coords[1]}"
    
    params = {
        'access_token': MAPBOX_ACCESS_TOKEN,
        'geometries': 'polyline',
        'overview': 'full'
    }
    
    if vehicle_type == models.VehicleTypeEnum.TWO_SEATER:
        params['exclude'] = 'motorway'
    
    logger.info(f"Mapbox: Requesting directions from {pickup_coords} to {dropoff_coords}")
    
    try:
        # Sử dụng httpx thay vì requests
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{directions_url}/{coordinates}", params=params)
            response.raise_for_status()
            data = response.json()
        
        if data.get("routes"):
            route = data["routes"][0]
            return {
                "distance": route["distance"],  # meters
                "duration": route["duration"],  # seconds
                "geometry": route["geometry"]   # encoded polyline
            }
        else:
            logger.warning("Mapbox: No routes found")
            return None
    except httpx.RequestError as e:
        logger.error(f"Mapbox API (Directions) error: {e}")
        raise e # Ném lỗi ra

def calculate_estimated_fare(distance_meters: float, vehicle_type: models.VehicleTypeEnum) -> float:
    """Calculate estimated fare based on distance and vehicle type"""
    # TODO: Implement your fare calculation logic here
    # Base fare + distance-based pricing + vehicle type multiplier
    
    distance_km = distance_meters / 1000
    
    # Base fare by vehicle type
    base_fares = {
        models.VehicleTypeEnum.TWO_SEATER: 15000,   # 2 chỗ
        models.VehicleTypeEnum.FOUR_SEATER: 20000,  # 4 chỗ
        models.VehicleTypeEnum.SEVEN_SEATER: 30000  # 7 chỗ
    }
    
    # Per km rate by vehicle type
    per_km_rates = {
        models.VehicleTypeEnum.TWO_SEATER: 8000,    # 2 chỗ
        models.VehicleTypeEnum.FOUR_SEATER: 10000,  # 4 chỗ
        models.VehicleTypeEnum.SEVEN_SEATER: 15000  # 7 chỗ
    }
    
    base_fare = base_fares.get(vehicle_type, 20000)
    per_km_rate = per_km_rates.get(vehicle_type, 10000)
    
    estimated_fare = base_fare + (distance_km * per_km_rate)
    
    # Round to nearest 1000 VND
    return round(estimated_fare / 1000) * 1000

async def estimate_fare_for_all_vehicles(pickup_coords: tuple[float, float], dropoff_coords: tuple[float, float]) -> List[dict]:
    """Estimate fare for all 3 vehicle types"""
    estimates = []
    
    for vehicle_type in [models.VehicleTypeEnum.TWO_SEATER, models.VehicleTypeEnum.FOUR_SEATER, models.VehicleTypeEnum.SEVEN_SEATER]:
        # Get route info for this vehicle type
        route_info = await get_route_info(pickup_coords, dropoff_coords, vehicle_type)
        
        if route_info:
            # Calculate fare
            estimated_fare = calculate_estimated_fare(route_info["distance"], vehicle_type)
            
            # Let FE handle polyline decoding
            route_geometry = {
                "type": "LineString",
                "encoded_polyline": route_info["geometry"]  # FE will decode this to coordinates
            }
            
            estimates.append({
                "vehicle_type": vehicle_type,
                "estimated_fare": estimated_fare,
                "distance_meters": route_info["distance"],
                "duration_seconds": route_info["duration"],
                "route_geometry": route_geometry
            })
    
    return estimates



async def create_trip_request_complete(trip_request: schemas.TripRequestComplete) -> dict:
    pickup_location = models.LocationInfo(
        address=trip_request.pickup.address,
        location=models.GeoLocation(
            coordinates=[trip_request.pickup.longitude, trip_request.pickup.latitude]
        )
    )
    dropoff_location = models.LocationInfo(
        address=trip_request.dropoff.address,
        location=models.GeoLocation(
            coordinates=[trip_request.dropoff.longitude, trip_request.dropoff.latitude]
        )
    )
    pickup_coords = (trip_request.pickup.longitude, trip_request.pickup.latitude)
    dropoff_coords = (trip_request.dropoff.longitude, trip_request.dropoff.latitude)
    route_info_data = await get_route_info(pickup_coords, dropoff_coords, trip_request.vehicle_type)
    if not route_info_data:
        raise ValueError("Could not calculate route between coordinates")
    route_info = models.RouteInfo(**route_info_data)
    estimated_fare = calculate_estimated_fare(route_info_data["distance"], trip_request.vehicle_type)
    fare_info = models.FareInfo(estimated=estimated_fare)
    payment_info = models.PaymentInfo(
        method=trip_request.payment_method,
        status=models.PaymentStatusEnum.PENDING
    )
    initial_history = [models.StatusHistory(status=models.TripStatusEnum.PENDING)]
    trip_obj = models.Trip(
        passenger_id=trip_request.passenger_id,
        driver_id="",
        vehicle_type=trip_request.vehicle_type,
        status=models.TripStatusEnum.PENDING,
        pickup=pickup_location,
        dropoff=dropoff_location,
        created_at=datetime.now(timezone.utc), 
        fare=fare_info,
        route_info=route_info,
        payment=payment_info,
        history=initial_history,
        notes=trip_request.notes,
        notified_driver_ids=[],
        rejected_driver_ids=[],
        offer_sent_at=None 
    )
    trip_dict = trip_obj.model_dump(by_alias=True, exclude={"id"})

    try:
        result = await trips_collection.insert_one(trip_dict)
        trip_id = str(result.inserted_id)
        trip_dict["_id"] = trip_id
        logger.info(f"Đã tạo chuyến đi mới với ID: {trip_id}")
    except Exception as e:
         logger.error(f"Lỗi khi insert chuyến đi vào DB: {e}", exc_info=True)
         raise HTTPException(status_code=500, detail="Lỗi server khi tạo chuyến đi.")
    nearby_drivers_raw = await find_nearby_drivers_from_location_service(
        trip_request.pickup.latitude,
        trip_request.pickup.longitude
    )
    if nearby_drivers_raw:
        driver_ids = [driver['driver_id'] for driver in nearby_drivers_raw]
        logger.info(f"Tìm thấy {len(driver_ids)} tài xế gần đó cho chuyến đi {trip_id}. Bắt đầu mời...")
        await add_notified_drivers_to_trip(trip_id, driver_ids)
        trip_payload = {
            "type": "TRIP_OFFER",
            "trip_id": trip_id,
            "pickup_address": trip_dict["pickup"]["address"],
            "dropoff_address": trip_dict["dropoff"]["address"],
            "estimated_fare": trip_dict["fare"]["estimated"],
            "distance_meters": trip_dict.get("route_info", {}).get("distance")
        }
        await notify_drivers_via_location_service(driver_ids, trip_payload)
        offer_timestamp = datetime.now(timezone.utc) 
        try:
            await trips_collection.update_one(
                {"_id": ObjectId(trip_id)},
                {"$set": {"offer_sent_at": offer_timestamp}}
            )
            logger.info(f"Đã cập nhật offer_sent_at cho chuyến đi {trip_id}.")
            trip_dict["offer_sent_at"] = offer_timestamp
        except Exception as e:
             logger.error(f"Lỗi khi cập nhật offer_sent_at cho chuyến đi {trip_id}: {e}")
    else:
        logger.warning(f"Không tìm thấy tài xế nào cho chuyến đi {trip_id} khi tạo.")
    final_trip_data = await get_trip_by_id(trip_id)
    return final_trip_data if final_trip_data else trip_dict

async def create_trip_request(trip_request: schemas.TripRequest) -> dict:
    """Create new trip request from passenger (using Mapbox APIs)"""
    # Get coordinates from addresses using Mapbox Geocoding API
    pickup_coords = await get_coordinates(trip_request.pickup.address)
    dropoff_coords = await get_coordinates(trip_request.dropoff.address)
    
    if not pickup_coords or not dropoff_coords:
        raise ValueError("Could not geocode one or both addresses")
    
    # Get route information from Mapbox Directions API
    route_info_data = await get_route_info(pickup_coords, dropoff_coords, trip_request.vehicle_type)
    
    if not route_info_data:
        raise ValueError("Could not calculate route between addresses")
    
    # Create RouteInfo object
    route_info = models.RouteInfo(
        distance=route_info_data["distance"],
        duration=route_info_data["duration"], 
        geometry=route_info_data["geometry"]
    )
    
    # Calculate estimated fare based on distance and vehicle type
    estimated_fare = calculate_estimated_fare(route_info_data["distance"], trip_request.vehicle_type)
    
    # Convert addresses to LocationInfo with Mapbox coordinates
    pickup_location = models.LocationInfo(
        address=trip_request.pickup.address,
        location=models.GeoLocation(
            coordinates=[pickup_coords[0], pickup_coords[1]]  # [longitude, latitude]
        )
    )
    
    dropoff_location = models.LocationInfo(
        address=trip_request.dropoff.address,
        location=models.GeoLocation(
            coordinates=[dropoff_coords[0], dropoff_coords[1]]  # [longitude, latitude]
        )
    )
    
    # Create fare info with calculated estimate
    fare_info = models.FareInfo(
        estimated=estimated_fare
    )
    
    # Create payment info from request
    payment_info = models.PaymentInfo(
        method=trip_request.payment_method,
        status=models.PaymentStatusEnum.PENDING
    )
    
    # Create initial status history
    initial_history = [models.StatusHistory(status=models.TripStatusEnum.PENDING)]
    
    # Create trip object (without driver_id) - explicitly set defaults
    trip_obj = models.Trip(
        passenger_id=trip_request.passenger_id,
        driver_id="",  # Empty initially - will be assigned later
        vehicle_type=trip_request.vehicle_type,  # Vehicle type from request
        status=models.TripStatusEnum.PENDING,  # Explicitly set status
        pickup=pickup_location,
        dropoff=dropoff_location,
        created_at=datetime.now(),  # Explicitly set created_at
        fare=fare_info,
        route_info=route_info,  # Add route information
        payment=payment_info,  # Add payment information
        history=initial_history,
        notes=trip_request.notes
    )
    
    # Convert to dict for MongoDB - exclude the id field to let MongoDB generate it
    trip_dict = trip_obj.model_dump(by_alias=True, exclude={"id"})
    
    # Insert to database
    result = await trips_collection.insert_one(trip_dict)
    
    # Add the inserted ID to the dict and return it directly
    trip_dict["_id"] = str(result.inserted_id)
    return trip_dict

async def assign_driver_to_trip(trip_id: str, driver_id: str) -> Optional[dict]:
    if not ObjectId.is_valid(trip_id):
        logger.warning(f"assign_driver_to_trip: trip_id không hợp lệ: {trip_id}")
        return None
    try:
        current_trip = await trips_collection.find_one({"_id": ObjectId(trip_id)})
        if not current_trip:
            logger.warning(f"Tài xế {driver_id} cố nhận chuyến {trip_id} không tồn tại.")
            return None 
    except Exception as e:
        logger.error(f"Lỗi khi lấy thông tin chuyến đi {trip_id} để kiểm tra: {e}")
        return None 


    current_status = current_trip.get("status")
    if current_status != models.TripStatusEnum.PENDING.value:
        logger.warning(f"Tài xế {driver_id} cố nhận chuyến {trip_id} không còn PENDING (status: {current_status}).")
        return None

    offer_sent_time = current_trip.get("offer_sent_at")
    if offer_sent_time:
        if offer_sent_time.tzinfo is None:
             offer_sent_time = offer_sent_time.replace(tzinfo=timezone.utc)

        time_now = datetime.now(timezone.utc)
        time_elapsed = time_now - offer_sent_time

        acceptance_limit = timedelta(seconds=16)

        if time_elapsed > acceptance_limit:
            logger.warning(f"Tài xế {driver_id} cố nhận chuyến {trip_id} QUÁ HẠN {acceptance_limit.total_seconds()} giây ({time_elapsed.total_seconds():.1f}s).")

            return None
        else:
             logger.info(f"Tài xế {driver_id} chấp nhận chuyến {trip_id} trong thời hạn ({time_elapsed.total_seconds():.1f}s).")

    else:
        logger.warning(f"Chuyến đi {trip_id} thiếu 'offer_sent_at'. Bỏ qua kiểm tra thời gian.")
        
    new_history_entry = {
        "status": models.TripStatusEnum.ACCEPTED.value,
        "timestamp": datetime.now(timezone.utc) 
    }
    try:
        result = await trips_collection.update_one(
            {"_id": ObjectId(trip_id), "status": models.TripStatusEnum.PENDING.value},
            {
                "$set": {
                    "driver_id": driver_id,
                    "status": models.TripStatusEnum.ACCEPTED.value
                },
                "$push": {"history": new_history_entry}
            }
        )
    except Exception as e:
        logger.error(f"Lỗi khi update_one để gán tài xế {driver_id} cho chuyến {trip_id}: {e}")
        return None 

    if result.modified_count == 0:
        logger.warning(f"Tài xế {driver_id} THẤT BẠI khi nhận chuyến {trip_id} (Race condition - người khác nhanh hơn).")
        return None
    
    logger.info(f"Tài xế {driver_id} THÀNH CÔNG nhận chuyến {trip_id} (Thắng race condition).")
    updated_trip = await get_trip_by_id(trip_id) 
    if not updated_trip: return None 
    notified_ids = updated_trip.get("notified_driver_ids", [])
    winner_id = driver_id
    loser_ids = [id for id in notified_ids if id != winner_id]
    if loser_ids:
        logger.info(f"Thông báo 'TRIP_CANCELLED' cho {len(loser_ids)} tài xế thua cuộc.")
        cancel_payload = {"type": "TRIP_CANCELLED", "trip_id": trip_id, "reason": "Đã được tài xế khác nhận"}
        await notify_drivers_via_location_service(loser_ids, cancel_payload)

    logger.info(f"Lấy thông tin tài xế {winner_id} để báo cho hành khách.")
    driver_details = await get_driver_details_from_driver_service(winner_id)
    if driver_details is None: driver_details = {"name": "Tài xế", "vehicle": {"license_plate": "N/A"}}

    logger.info(f"Thông báo 'DRIVER_ASSIGNED' cho hành khách chuyến {trip_id}.")
    passenger_payload = {"type": "DRIVER_ASSIGNED", "trip_id": trip_id, "driver_info": driver_details}
    await notify_passenger_via_location_service(trip_id, passenger_payload)

    return updated_trip

async def deny_trip(trip_id: str, driver_id: str) -> Optional[dict]:
    """Driver denies/rejects assigned trip - removes driver and sets back to PENDING"""
    if not ObjectId.is_valid(trip_id):
        return None
    
    # Only allow denial if trip is ACCEPTED and belongs to this driver
    new_history_entry = {
        "status": models.TripStatusEnum.PENDING.value,
        "timestamp": datetime.now()
    }
    
    result = await trips_collection.update_one(
        {
            "_id": ObjectId(trip_id), 
            "status": models.TripStatusEnum.ACCEPTED.value,
            "driver_id": driver_id
        },
        {
            "$set": {
                "driver_id": "",  # Remove driver
                "status": models.TripStatusEnum.PENDING.value
            },
            "$push": {"history": new_history_entry}
        }
    )
    
    if result.modified_count == 0:
        return None
        
    return await get_trip_by_id(trip_id)

async def update_trip_status(trip_id: str, new_status: models.TripStatusEnum) -> Optional[dict]:
    """Update trip status and add to history"""
    if not ObjectId.is_valid(trip_id):
        return None
    
    # Get current trip
    current_trip = await get_trip_by_id(trip_id)
    if not current_trip:
        return None
    
    # Create new status history entry
    new_history_entry = {
        "status": new_status.value,
        "timestamp": datetime.now()
    }
    
    # Prepare update data
    set_data = {
        "status": new_status.value
    }
    
    # Add specific timestamp fields based on status
    if new_status == models.TripStatusEnum.ON_TRIP:
        set_data["startTime"] = datetime.now()
    elif new_status == models.TripStatusEnum.COMPLETED:
        set_data["endTime"] = datetime.now()
    
    # Update with both $set and $push operations
    result = await trips_collection.update_one(
        {"_id": ObjectId(trip_id)},
        {
            "$set": set_data,
            "$push": {"history": new_history_entry}
        }
    )
    
    if result.modified_count:
        return await get_trip_by_id(trip_id)
    return None

async def update_trip_fare(trip_id: str, actual_fare: float, discount: float = 0, tax: float = 0) -> Optional[dict]:
    """Update trip fare information"""
    if not ObjectId.is_valid(trip_id):
        return None
    
    update_data = {
        "fare.actual": actual_fare,
        "fare.discount": discount,
        "fare.tax": tax
    }
    
    result = await trips_collection.update_one(
        {"_id": ObjectId(trip_id)},
        {"$set": update_data}
    )
    
    if result.modified_count:
        return await get_trip_by_id(trip_id)
    return None

async def add_payment_info(trip_id: str, payment: schemas.PaymentCreate) -> Optional[dict]:
    """Add payment information to trip"""
    if not ObjectId.is_valid(trip_id):
        return None
    
    payment_data = models.PaymentInfo(
        method=payment.method,
        transaction_id=payment.transaction_id,
        status=models.PaymentStatusEnum.PENDING
    )
    
    result = await trips_collection.update_one(
        {"_id": ObjectId(trip_id)},
        {"$set": {"payment": payment_data.dict()}}
    )
    
    if result.modified_count:
        return await get_trip_by_id(trip_id)
    return None

async def update_payment_status(trip_id: str, payment_update: schemas.PaymentUpdate) -> Optional[dict]:
    """Update payment status"""
    if not ObjectId.is_valid(trip_id):
        return None
    
    update_data = {
        "payment.status": payment_update.status.value
    }
    
    if payment_update.transaction_id:
        update_data["payment.transaction_id"] = payment_update.transaction_id
    
    if payment_update.paid_at:
        update_data["payment.paid_at"] = payment_update.paid_at
    elif payment_update.status == models.PaymentStatusEnum.SUCCESS:
        update_data["payment.paid_at"] = datetime.now()
    
    result = await trips_collection.update_one(
        {"_id": ObjectId(trip_id)},
        {"$set": update_data}
    )
    
    if result.modified_count:
        return await get_trip_by_id(trip_id)
    return None

async def add_trip_rating(trip_id: str, rating: schemas.RatingCreate) -> Optional[dict]:
    """Add rating to trip (embedded)"""
    if not ObjectId.is_valid(trip_id):
        return None
    
    rating_data = models.RatingInfo(
        stars=rating.stars,
        comment=rating.comment,
        rated_at=datetime.now()
    )
    
    result = await trips_collection.update_one(
        {"_id": ObjectId(trip_id)},
        {"$set": {"rating": rating_data.dict()}}
    )
    
    if result.modified_count:
        return await get_trip_by_id(trip_id)
    return None

async def cancel_trip(trip_id: str, cancellation: schemas.CancellationCreate) -> Optional[dict]:
    """Cancel trip with reason"""
    if not ObjectId.is_valid(trip_id):
        return None
    
    cancellation_data = models.CancellationInfo(
        cancelled_by=cancellation.cancelled_by,
        reason=cancellation.reason,
        cancelled_at=datetime.now()
    )
    
    update_data = {
        "status": models.TripStatusEnum.CANCELLED.value,
        "cancellation": cancellation_data.dict(),
        "$push": {
            "history": {
                "status": models.TripStatusEnum.CANCELLED.value,
                "timestamp": datetime.now()
            }
        }
    }
    
    result = await trips_collection.update_one(
        {"_id": ObjectId(trip_id)},
        {"$set": update_data}
    )
    
    if result.modified_count:
        return await get_trip_by_id(trip_id)
    return None

async def delete_trip(trip_id: str) -> bool:
    """Delete trip"""
    if not ObjectId.is_valid(trip_id):
        return False
    
    result = await trips_collection.delete_one({"_id": ObjectId(trip_id)})
    return result.deleted_count > 0

async def get_trip_statistics(driver_id: Optional[str] = None, passenger_id: Optional[str] = None) -> dict:
    """Get trip statistics"""
    match_condition = {}
    
    if driver_id:
        match_condition["driver_id"] = driver_id
    if passenger_id:
        match_condition["passenger_id"] = passenger_id
    
    pipeline = [
        {"$match": match_condition},
        {
            "$group": {
                "_id": None,
                "total_trips": {"$sum": 1},
                "completed_trips": {
                    "$sum": {
                        "$cond": [{"$eq": ["$status", "COMPLETED"]}, 1, 0]
                    }
                },
                "cancelled_trips": {
                    "$sum": {
                        "$cond": [{"$eq": ["$status", "CANCELLED"]}, 1, 0]
                    }
                },
                "total_revenue": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$status", "COMPLETED"]},
                            "$fare.actual",
                            0
                        ]
                    }
                },
                "average_rating": {"$avg": "$rating.stars"}
            }
        }
    ]
    
    result = await trips_collection.aggregate(pipeline).to_list(length=1)
    return result[0] if result else {
        "total_trips": 0,
        "completed_trips": 0, 
        "cancelled_trips": 0,
        "total_revenue": 0,
        "average_rating": None
    }
    
async def find_nearby_drivers_from_location_service(latitude: float, longitude: float) -> List[Dict[str, Any]]:
    search_radii = [3, 7, 15] 
    limit_per_search = 10 

    nearby_drivers = [] 
    for radius_km in search_radii:
        logger.info(f"Đang tìm tài xế trong bán kính {radius_km}km...")
        
        url = f"{LOCATION_SERVICE_URL}/drivers/nearby"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "radius_km": radius_km,
            "limit": limit_per_search
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    nearby_drivers = response.json()
                    logger.info(f"Tìm thấy {len(nearby_drivers)} tài xế trong bán kính {radius_km}km.")
                    break 
                elif response.status_code == 404:
                    logger.warning(f"Không tìm thấy tài xế nào trong bán kính {radius_km}km. Mở rộng tìm kiếm...")
                    continue 
                else:
                    response.raise_for_status() 

        except httpx.HTTPStatusError as e:
            logger.error(f"Lỗi khi gọi LocationService (HTTP {e.response.status_code}): {e.response.text}")
            return [] 
        except httpx.RequestError as e:
            logger.error(f"Không thể kết nối đến LocationService: {e}")
            return [] 

    return nearby_drivers

async def notify_drivers_via_location_service(driver_ids: List[str], payload: Dict[str, Any]):
    """Gọi LocationService để gửi thông báo WebSocket cho danh sách tài xế."""
    if not driver_ids:
        return

    url = f"{LOCATION_SERVICE_URL}/notify/drivers" 
    request_data = {"driver_ids": driver_ids, "payload": payload}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=request_data, timeout=10.0)
            response.raise_for_status() 
            logger.info(f"TripService: Đã yêu cầu LocationService thông báo (loại: {payload.get('type')}) cho {len(driver_ids)} tài xế.")
    except httpx.RequestError as e:
        logger.error(f"TripService: Không thể kết nối LocationService (để thông báo): {e}")
    except httpx.HTTPStatusError as e:
        logger.error(f"TripService: LocationService trả lỗi khi thông báo: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        logger.error(f"TripService: Lỗi không xác định khi thông báo tài xế: {e}")

async def notify_passenger_via_location_service(trip_id: str, payload: Dict[str, Any]):
    url = f"{LOCATION_SERVICE_URL}/notify/trip/{trip_id}/passenger"
    request_data = {"payload": payload}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=request_data, timeout=10.0)
            response.raise_for_status()
            logger.info(f"TripService: Đã yêu cầu LocationService thông báo cho hành khách (chuyến {trip_id}, loại: {payload.get('type')}).")
    except Exception as e:
        logger.error(f"TripService: Lỗi khi thông báo hành khách: {e}")


async def get_driver_details_from_driver_service(driver_id: str) -> Optional[Dict[str, Any]]:
    """Lấy thông tin tài xế từ DriverService (dùng OAuth2 Service Token)."""

    service_token = await _get_service_token()
    if not service_token:
        logger.error("Không thể lấy Service Token để gọi DriverService.")
        return None 
    if not DRIVER_SERVICE_URL:
        logger.error("DRIVER_SERVICE_URL chưa được cấu hình!")
        return None

    url = f"{DRIVER_SERVICE_URL}/drivers/internal/{driver_id}"
    headers = {"Authorization": f"Bearer {service_token}"} 

    logger.info(f"Đang gọi DriverService (internal) cho driver {driver_id} với Service Token...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=5.0)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401 or response.status_code == 403:
                 logger.error(f"Lỗi gọi DriverService: Service Token không hợp lệ hoặc bị từ chối.")
                 global _service_token_cache, _token_expiry_time
                 _service_token_cache = None
                 _token_expiry_time = None
                 return None
            else:
                logger.warning(f"DriverService trả lỗi {response.status_code} khi lấy thông tin {driver_id}")
                return None
    except Exception as e:
        logger.error(f"Lỗi khi gọi DriverService để lấy thông tin: {e}")
        return None

async def add_notified_drivers_to_trip(trip_id: str, driver_ids: List[str]):
    
    if not ObjectId.is_valid(trip_id) or not driver_ids:
        return
    
    await trips_collection.update_one(
        {"_id": ObjectId(trip_id)},
        {"$set": {"notified_driver_ids": driver_ids}}
    )

async def reject_trip_by_driver(trip_id: str, driver_id: str) -> bool:
    if not ObjectId.is_valid(trip_id):
        return False
        
    result = await trips_collection.update_one(
        {"_id": ObjectId(trip_id)},
        {"$addToSet": {"rejected_driver_ids": driver_id}} 
    )
    
    return result.modified_count > 0

async def _get_service_token() -> Optional[str]:
    global _service_token_cache, _token_expiry_time

    if _service_token_cache and _token_expiry_time and \
       _token_expiry_time > (datetime.now(timezone.utc) + timedelta(minutes=1)):
        logger.info("Sử dụng Service Token từ cache.")
        return _service_token_cache

    if not USER_SERVICE_URL or not MY_CLIENT_ID or not MY_CLIENT_SECRET:
        logger.error("Client ID/Secret hoặc UserService URL chưa được cấu hình!")
        return None

    token_url = f"{USER_SERVICE_URL}/auth/token"
    data = {
        "username": MY_CLIENT_ID, 
        "password": MY_CLIENT_SECRET 
    }

    logger.info(f"Đang xin Service Token từ {token_url} cho client {MY_CLIENT_ID}...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data, timeout=10.0)
            response.raise_for_status() 

            token_data = response.json()
            new_token = token_data.get("access_token")

            if new_token:
                logger.info("Lấy Service Token mới thành công.")
                _service_token_cache = new_token
                _token_expiry_time = datetime.now(timezone.utc) + timedelta(minutes=14)
                return new_token
            else:
                logger.error("Phản hồi từ UserService không chứa access_token.")
                return None

    except httpx.RequestError as e:
        logger.error(f"Lỗi kết nối đến UserService để lấy token: {e}")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"UserService trả lỗi khi cấp token: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Lỗi không xác định khi lấy Service Token: {e}")
        return None

    
