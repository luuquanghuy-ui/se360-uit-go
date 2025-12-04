from database import redis_client, DRIVER_GEO_KEY
from schemas import NearbyDriver
from typing import List


async def update_driver_location(driver_id: str, longitude: float, latitude: float):
    if redis_client:
        await redis_client.geoadd(
            DRIVER_GEO_KEY,
            (longitude, latitude, driver_id)
        )

async def remove_driver_location(driver_id: str):
    if redis_client:
        await redis_client.zrem(DRIVER_GEO_KEY, driver_id)

async def get_nearby_drivers(longitude: float, latitude: float, radius_km: int, limit: int) -> List[NearbyDriver]:
    if not redis_client:
        return []

    try:
        # Use GEORADIUS with correct parameter order for Azure Redis
        radius_m = radius_km * 1000

        print(f"DEBUG: Calling GEORADIUS with key={DRIVER_GEO_KEY}, longitude={longitude}, latitude={latitude}, radius_m={radius_m}")

        drivers = await redis_client.execute_command(
            "GEORADIUS",
            DRIVER_GEO_KEY,
            float(longitude),  # longitude first
            float(latitude),   # latitude second
            float(radius_m),   # radius in meters
            "m",
            "WITHDIST",
            "WITHCOORD",
            "COUNT",
            limit,
            "ASC"
        )

        print(f"DEBUG: GEORADIUS result type: {type(drivers)}, length: {len(drivers) if drivers else 0}")

        result_list = []
        if drivers:
            for d in drivers:
                print(f"DEBUG: Processing driver data: {d}, type: {type(d)}")
                # GEORADIUS returns: [member, distance, [longitude, latitude]]
                driver_id, distance, coords = d
                lon, lat = coords
                result_list.append(
                    NearbyDriver(
                        driver_id=driver_id,
                        distance_km=round(float(distance) / 1000, 2),  # Convert m to km
                        longitude=float(lon),
                        latitude=float(lat)
                    )
                )

        print(f"DEBUG: Returning {len(result_list)} drivers")
        return result_list

    except Exception as e:
        print(f"LỖI: GEORADIUS error: {e}")
        print(f"DEBUG - long={longitude}({type(longitude)}), lat={latitude}({type(latitude)}), radius_m={radius_m}({type(radius_m)})")
        return []