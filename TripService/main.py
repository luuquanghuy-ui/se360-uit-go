from fastapi import FastAPI, HTTPException, status, Query
from typing import List, Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

import crud
import models
import schemas

import os
import httpx
from fastapi import Body
import logging

# Load environment variables
load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
                           
app = FastAPI(title="UIT-Go Trip Service (MongoDB)", version="1.0.0")

@app.get("/")
async def get_service_info():
    return {"service": "UIT-Go Trip Service", "version": "1.0", "status": "running", "database": "MongoDB"}

@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes probes"""
    try:
        # Test MongoDB connection
        from database import get_database
        db = get_database()
        await db.command("ping")
        return {
            "status": "healthy",
            "service": "tripservice",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

# Trip CRUD routes
# New flow: FE sends coordinates -> BE returns fare estimates for all vehicle types
@app.post("/fare-estimate/", response_model=schemas.FareEstimateResponse)
async def estimate_fare(fare_request: schemas.FareEstimateRequest):
    """Estimate fare for all vehicle types based on pickup/dropoff coordinates"""
    pickup_coords = (fare_request.pickup.longitude, fare_request.pickup.latitude)
    dropoff_coords = (fare_request.dropoff.longitude, fare_request.dropoff.latitude)
    
    estimates = await crud.estimate_fare_for_all_vehicles(pickup_coords, dropoff_coords)
    
    if not estimates:
        raise HTTPException(status_code=400, detail="Could not calculate fare estimates")
    
    return schemas.FareEstimateResponse(estimates=estimates)


@app.post(
    "/trip-requests/complete/",
    response_model=schemas.TripCreationResponse, 
)
async def create_complete_trip_request(trip_request: schemas.TripRequestComplete):

    try:
        trip_data = await crud.create_trip_request_complete(trip_request)
        if not trip_data: 
             raise HTTPException(status_code=500, detail="Lỗi không xác định khi tạo chuyến đi.")
        return {"trip": trip_data}

    except ValueError as e: 
        logger.error(f"Lỗi khi tạo chuyến đi: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as http_exc: 
         raise http_exc
    except Exception as e: 
        logger.error(f"Lỗi không xác định khi tạo chuyến đi: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Lỗi server khi tạo chuyến đi.")




@app.put("/trips/{trip_id}/assign-driver", response_model=schemas.TripResponse)
async def assign_driver(trip_id: str, assign_data: schemas.AssignDriver):
    """Assign driver to a pending trip"""
    trip_data = await crud.assign_driver_to_trip(trip_id, assign_data.driver_id)
    if trip_data is None:
        raise HTTPException(status_code=409, detail="Chuyến đi không hợp lệ, đã được nhận, bị hủy hoặc đã quá hạn chấp nhận.")
    return schemas.TripResponse(**trip_data)



@app.get("/trips/{trip_id}", response_model=schemas.TripResponse)
async def get_trip(trip_id: str):
    """Get trip by ID with all nested information"""
    trip_data = await crud.get_trip_by_id(trip_id)
    if trip_data is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return schemas.TripResponse(**trip_data)

@app.delete("/trips/{trip_id}")
async def delete_trip(trip_id: str):
    success = await crud.delete_trip(trip_id)
    if not success:
        raise HTTPException(status_code=404, detail="Trip not found")
    return {"message": "Trip deleted successfully"}

# Trip listing routes
@app.get("/trips/passenger/{passenger_id}", response_model=List[schemas.TripSummaryResponse])
async def get_passenger_trips(
    passenger_id: str, 
    skip: int = Query(0, ge=0), 
    limit: int = Query(100, ge=1, le=100)
):
    """Get trips for a specific passenger"""
    trips = await crud.get_trips_by_passenger(passenger_id, skip=skip, limit=limit)
    return [_convert_to_summary(trip) for trip in trips]

@app.get("/trips/driver/{driver_id}", response_model=List[schemas.TripSummaryResponse])
async def get_driver_trips(
    driver_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
):
    """Get trips for a specific driver"""
    trips = await crud.get_trips_by_driver(driver_id, skip=skip, limit=limit)
    return [_convert_to_summary(trip) for trip in trips]

@app.get("/trips/available/", response_model=List[schemas.TripSummaryResponse])
async def get_available_trips(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
):
    """Get available trips (PENDING status)"""
    trips = await crud.get_available_trips(skip=skip, limit=limit)
    return [_convert_to_summary(trip) for trip in trips]

@app.get("/trips/near/", response_model=List[schemas.TripSummaryResponse])
async def get_trips_near_location(
    longitude: float = Query(..., ge=-180, le=180),
    latitude: float = Query(..., ge=-90, le=90),
    max_distance: int = Query(5000, ge=100, le=50000),  # meters
    limit: int = Query(50, ge=1, le=100)
):
    """Get trips near a specific location using GeoJSON"""
    trips = await crud.get_trips_near_location(longitude, latitude, max_distance, limit)
    return [_convert_to_summary(trip) for trip in trips]

# Trip status management
@app.post("/trips/{trip_id}/accept")
async def accept_trip(trip_id: str):
    """Accept a trip (PENDING -> ACCEPTED)"""
    trip_data = await crud.update_trip_status(trip_id, models.TripStatusEnum.ACCEPTED)
    if trip_data is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return {"message": "Trip accepted successfully", "trip_id": trip_id, "status": "ACCEPTED"}

@app.post("/trips/{trip_id}/start")
async def start_trip(trip_id: str):
    """Start a trip (ACCEPTED -> ON_TRIP)"""
    trip_data = await crud.update_trip_status(trip_id, models.TripStatusEnum.ON_TRIP)
    if trip_data is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return {"message": "Trip started successfully", "trip_id": trip_id, "status": "ON_TRIP"}

@app.post("/trips/{trip_id}/deny")
async def deny_trip(trip_id: str, deny_data: schemas.AssignDriver):
    """Driver denies/rejects assigned trip - removes driver and sets back to PENDING"""
    trip_data = await crud.deny_trip(trip_id, deny_data.driver_id)
    if trip_data is None:
        raise HTTPException(status_code=404, detail="Trip not found or cannot be denied")
    return {"message": "Trip denied successfully - returned to pending", "trip_id": trip_id, "status": "PENDING"}

@app.post("/trips/{trip_id}/complete")
async def complete_trip(trip_id: str, data: dict = Body(...)):
    """
    Hoàn thành chuyến đi và xử lý thanh toán với hệ thống mới.
    Tự động tính cước phí dựa trên khoảng cách và hỗ trợ thanh toán ngân hàng giả lập.
    """
    distance_km = data.get("distance_km")
    user_bank_info = data.get("user_bank_info")  # Optional, cho chuyển khoản

    if distance_km is None:
        raise HTTPException(status_code=400, detail="distance_km is required in the request body")

    trip = await crud.get_trip_by_id(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Lấy thông tin payment method từ trip data
    payment_method = trip.get("payment", {}).get("method", "CASH")
    # Convert E-Wallet to BANK_TRANSFER cho hệ thống mới
    if payment_method.upper() == "E-WALLET":
        payment_method = "BANK_TRANSFER"

    PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL")
    if not PAYMENT_SERVICE_URL:
        raise HTTPException(status_code=500, detail="PAYMENT_SERVICE_URL is not configured")

    # Tạo request cho PaymentService mới
    payment_completion_request = {
        "trip_id": trip_id,
        "driver_id": trip.get("driver_id"),
        "user_id": trip.get("passenger_id"),
        "distance_km": distance_km,
        "payment_method": payment_method,
        "user_bank_info": user_bank_info if payment_method == "BANK_TRANSFER" else None
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{PAYMENT_SERVICE_URL}/v1/trip-completion/complete",
                json=payment_completion_request,
                timeout=30.0
            )
            response.raise_for_status()
            payment_result = response.json()
    except (httpx.RequestError, httpx.TimeoutException) as e:
        logger.error(f"Payment service connection error: {e}")
        raise HTTPException(status_code=503, detail="Could not connect to Payment Service")
    except httpx.HTTPStatusError as e:
        logger.error(f"Payment service error: {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json())

    # Cập nhật trạng thái trip
    await crud.update_trip_status(trip_id, models.TripStatusEnum.COMPLETED)

    # Cập nhật fare nếu payment thành công
    if payment_result.get("success") and payment_result.get("fare_details"):
        fare_details = payment_result["fare_details"]
        await crud.update_trip_fare(trip_id, fare_details["total_fare"])

    return {
        "message": "Trip completed and payment processed successfully",
        "payment_result": payment_result
    }

@app.post("/trips/{trip_id}/cancel")
async def cancel_trip(trip_id: str, cancellation: schemas.CancellationCreate):
    """Cancel a trip with reason"""
    trip_data = await crud.cancel_trip(trip_id, cancellation)
    if trip_data is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return {"message": "Trip cancelled successfully", "trip_id": trip_id, "status": "CANCELLED"}

# Payment management
@app.post("/trips/{trip_id}/payment")
async def add_payment_info(trip_id: str, payment: schemas.PaymentCreate):
    """Add payment information to trip"""
    trip_data = await crud.add_payment_info(trip_id, payment)
    if trip_data is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return {"message": "Payment info added successfully", "trip_id": trip_id}

@app.put("/trips/{trip_id}/payment", status_code=status.HTTP_200_OK, tags=["Payment Internal"])
async def update_trip_payment_status_internal(
    trip_id: str,
    payment_update: schemas.PaymentUpdate 
):
    """[API NỘI BỘ] Cập nhật trạng thái thanh toán từ PaymentService."""
    logger.info(f"Nhận yêu cầu cập nhật thanh toán cho chuyến {trip_id}: Status={payment_update.status}")
    updated_trip = await crud.update_payment_status(trip_id, payment_update)
    if updated_trip is None:
        logger.error(f"Không thể cập nhật trạng thái thanh toán cho chuyến đi {trip_id}")
        raise HTTPException(status_code=404, detail="Trip not found or update failed.")
    logger.info(f"Đã cập nhật trạng thái thanh toán cho chuyến {trip_id}")
    return {"message": "Payment status updated successfully"}


@app.post("/trips/{trip_id}/rating")
async def add_trip_rating(trip_id: str, rating: schemas.RatingCreate):
    trip_data = await crud.get_trip_by_id(trip_id)
    if trip_data is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if trip_data["status"] != models.TripStatusEnum.COMPLETED.value:
        raise HTTPException(status_code=400, detail="Can only rate completed trips")
    
    if trip_data.get("rating"):
        raise HTTPException(status_code=400, detail="Trip already rated")
    
    updated_trip = await crud.add_trip_rating(trip_id, rating)
    return {"message": "Rating added successfully", "trip_id": trip_id, "rating": rating.stars}

@app.get("/trips/{trip_id}/rating")
async def get_trip_rating(trip_id: str):
    """Get rating for a trip"""
    trip_data = await crud.get_trip_by_id(trip_id)
    if trip_data is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    rating = trip_data.get("rating")
    if not rating:
        raise HTTPException(status_code=404, detail="No rating found for this trip")
    
    return rating

# Statistics
@app.get("/statistics/driver/{driver_id}", response_model=schemas.TripStatistics)
async def get_driver_statistics(driver_id: str):
    """Get trip statistics for a driver"""
    stats = await crud.get_trip_statistics(driver_id=driver_id)
    return schemas.TripStatistics(**stats)

@app.get("/statistics/passenger/{passenger_id}", response_model=schemas.TripStatistics)
async def get_passenger_statistics(passenger_id: str):
    """Get trip statistics for a passenger"""
    stats = await crud.get_trip_statistics(passenger_id=passenger_id)
    return schemas.TripStatistics(**stats)

# Helper function
def _convert_to_summary(trip: dict) -> schemas.TripSummaryResponse:
    """Convert full trip to summary response"""
    return schemas.TripSummaryResponse(
        _id=str(trip["_id"]),
        passenger_id=trip["passenger_id"],
        driver_id=trip["driver_id"],
        status=trip["status"],
        pickup_address=trip["pickup"]["address"],
        dropoff_address=trip["dropoff"]["address"],
        estimated_fare=trip.get("fare", {}).get("estimated"),
        actual_fare=trip.get("fare", {}).get("actual"),
        created_at=trip["created_at"],
        startTime=trip.get("startTime"),
        endTime=trip.get("endTime")
    )
    
@app.post("/trips/{trip_id}/reject")
async def reject_trip(trip_id: str, reject_data: schemas.AssignDriver):
    driver_id = reject_data.driver_id
    success = await crud.reject_trip_by_driver(trip_id, driver_id)
    
    if success:
        logger.info(f"Tài xế {driver_id} đã TỪ CHỐI/HẾT GIỜ với chuyến {trip_id}.")
        return {"message": "Đã ghi nhận từ chối."}
    else:
        raise HTTPException(status_code=404, detail="Không tìm thấy chuyến đi để từ chối.")