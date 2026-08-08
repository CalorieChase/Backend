import math
import os
import random
from typing import List, Optional, Tuple

import httpx
from dotenv import load_dotenv

from app.models.domain import Coin, LatLng

load_dotenv(override=True)


def get_maps_api_key() -> Optional[str]:
    """Returns only the Google Maps API key for location services."""
    return os.getenv("GOOGLE_MAPS_API_KEY")


def geocode_address(address: str) -> Optional[LatLng]:
    """Geocode an address string into coordinates using Google Maps."""
    api_key = get_maps_api_key()
    if not api_key:
        print("CRITICAL: GOOGLE_MAPS_API_KEY not found in environment for Geocoding!")
        return None

    masked_key = f"{api_key[:5]}...{api_key[-4:]}"
    print(f"API CALL (Maps): Geocoding '{address}' using Key: {masked_key}")

    params = {"address": address, "key": api_key}
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    try:
        response = httpx.get(url, params=params, timeout=30.0, verify=False)
        data = response.json()
        if data["status"] == "OK":
            loc = data["results"][0]["geometry"]["location"]
            return LatLng(lat=loc["lat"], lng=loc["lng"])

        error_msg = data.get("error_message", "No specific error message provided.")
        print(f"Geocoding API status: {data['status']}. Error: {error_msg}")
    except Exception as exc:
        print(f"Geocoding error: {exc}")
    return None


def find_destination_via_api(start: LatLng, keyword: str, distance_km: float) -> Optional[LatLng]:
    """Find a nearby destination that matches the keyword around the target radius."""
    api_key = get_maps_api_key()
    if not api_key:
        print("CRITICAL: GOOGLE_MAPS_API_KEY missing for Places API!")
        return None

    radius_meters = int(distance_km * 1000)
    search_keyword = keyword if keyword else "park"
    params = {
        "location": f"{start.lat},{start.lng}",
        "radius": radius_meters,
        "keyword": search_keyword,
        "key": api_key,
    }
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    print(f"API CALL (Maps): Places Nearby Search for '{search_keyword}' at rad={radius_meters}m")

    try:
        response = httpx.get(url, params=params, timeout=30.0, verify=False)
        data = response.json()
        if data["status"] == "OK" and data.get("results"):
            loc = data["results"][0]["geometry"]["location"]
            return LatLng(lat=loc["lat"], lng=loc["lng"])
        print(f"Places API status: {data['status']}")
    except Exception as exc:
        print(f"Places API error: {exc}")

    return None


def decode_polyline(polyline_str: str) -> List[LatLng]:
    """Decode a Google Maps polyline string into coordinates."""
    index, lat, lng = 0, 0, 0
    coordinates: List[LatLng] = []
    length = len(polyline_str)

    while index < length:
        b, shift, result = 0, 0, 0
        while True:
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += dlat

        shift, result = 0, 0
        while True:
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = ~(result >> 1) if (result & 1) else (result >> 1)
        lng += dlng

        coordinates.append(LatLng(lat=lat / 1e5, lng=lng / 1e5))

    return coordinates


def get_directions(
    origin: LatLng,
    destination: LatLng,
    mode: str,
    waypoints: Optional[List[LatLng]] = None,
) -> Tuple[List[LatLng], float]:
    """Fetch directions and total distance from Google Maps."""
    api_key = get_maps_api_key()
    if not api_key:
        print("CRITICAL: GOOGLE_MAPS_API_KEY not found in environment for Directions!")
        return [], 0.0

    masked_key = f"{api_key[:5]}...{api_key[-4:]}"
    print(f"API CALL (Maps): Directions using Key: {masked_key}")

    travel_mode = "walking"
    if mode.lower() in {"running", "jogging"}:
        travel_mode = "walking"

    params = {
        "origin": f"{origin.lat},{origin.lng}",
        "destination": f"{destination.lat},{destination.lng}",
        "mode": travel_mode,
        "key": api_key,
    }

    if waypoints:
        params["waypoints"] = "|".join(f"{wp.lat},{wp.lng}" for wp in waypoints)

    url = "https://maps.googleapis.com/maps/api/directions/json"

    try:
        response = httpx.get(url, params=params, timeout=30.0, verify=False)
        data = response.json()
        if data["status"] == "OK":
            route = data["routes"][0]
            total_dist_meters = sum(leg["distance"]["value"] for leg in route["legs"])

            poly_str = route.get("overview_polyline", {}).get("points", "")
            if poly_str:
                path_points = decode_polyline(poly_str)
            else:
                path_points = []
                for leg in route["legs"]:
                    for step in leg["steps"]:
                        path_points.append(
                            LatLng(
                                lat=step["start_location"]["lat"],
                                lng=step["start_location"]["lng"],
                            )
                        )
                    path_points.append(
                        LatLng(lat=leg["end_location"]["lat"], lng=leg["end_location"]["lng"])
                    )

            return path_points, total_dist_meters / 1000.0

        error_msg = data.get("error_message", "No specific error message provided.")
        print(f"Directions API status: {data['status']}. Error: {error_msg}")
    except Exception as exc:
        print(f"Directions error: {exc}")

    return [], 0.0


def find_loop_waypoint(start: LatLng, distance_km: float) -> LatLng:
    """Calculate a waypoint that helps form a loop route."""
    radius = distance_km / 4.0
    lat_offset = radius / 111.0
    lng_offset = radius / (111.0 * math.cos(math.radians(start.lat)))
    angle = random.uniform(0, 2 * math.pi)

    return LatLng(
        lat=start.lat + lat_offset * math.sin(angle),
        lng=start.lng + lng_offset * math.cos(angle),
    )


def interpolate_path(path: List[LatLng], min_points: int = 25) -> List[LatLng]:
    """Ensure a path has enough points for coin placement."""
    if len(path) >= min_points or len(path) < 2:
        return path

    new_path: List[LatLng] = []
    points_to_add = (min_points - len(path)) // (len(path) - 1) + 1

    for index in range(len(path) - 1):
        p1 = path[index]
        p2 = path[index + 1]
        new_path.append(p1)
        for step in range(1, points_to_add + 1):
            fraction = step / (points_to_add + 1)
            new_path.append(
                LatLng(
                    lat=p1.lat + (p2.lat - p1.lat) * fraction,
                    lng=p1.lng + (p2.lng - p1.lng) * fraction,
                )
            )
    new_path.append(path[-1])
    return new_path


def place_random_coins(path: List[LatLng], num_coins: int) -> List[Coin]:
    """Place gamified coins along the provided path coordinates."""
    smooth_path = interpolate_path(path)
    if not smooth_path or len(smooth_path) < 2:
        return []

    eligible_points = smooth_path[1:-1] if len(smooth_path) > 3 else smooth_path
    count = min(num_coins, len(eligible_points))
    chosen_indices = random.sample(range(len(eligible_points)), count)

    coins: List[Coin] = []
    for idx in chosen_indices:
        point = eligible_points[idx]
        value = random.choice([10, 10, 10, 20, 20, 50])
        coins.append(Coin(lat=point.lat, lng=point.lng, value=value))

    return coins


def calculate_workout_metrics(weight_kg: float, distance_km: float, mode: str) -> Tuple[float, float]:
    """Calculate estimated duration and calories burned using MET values."""
    mets = {"walking": 3.5, "jogging": 7.0, "running": 11.5}
    speeds = {"walking": 5.0, "jogging": 8.5, "running": 12.0}

    normalized_mode = mode.lower()
    met = mets.get(normalized_mode, 3.5)
    speed = speeds.get(normalized_mode, 5.0)
    duration_hours = distance_km / speed
    calories = met * weight_kg * duration_hours
    return duration_hours, calories
