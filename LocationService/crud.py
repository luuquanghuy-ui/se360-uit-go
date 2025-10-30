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
        drivers = await redis_client.geosearch(
            DRIVER_GEO_KEY, 
            longitude=longitude,
            latitude=latitude,
            radius=radius_km,
            unit="km",
            withdist=True,
            withcoord=True,
            count=limit,
            sort="ASC"
        )
        
        result_list = []
        for d in drivers:
            driver_id, distance, (lon, lat) = d
            result_list.append(
                NearbyDriver(
                    driver_id=driver_id,
                    distance_km=round(distance, 2),
                    longitude=lon,
                    latitude=lat
                )
            )
        return result_list

    except Exception as e:
        print(f"LỖI: Không thể thực hiện GEOSEARCH: {e}")
        return []