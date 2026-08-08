import os
import httpx
import random
import math
from typing import List, Tuple, Optional
from models import LatLng, Coin
from dotenv import load_dotenv

# Load and override environment variables from .env
load_dotenv(override=True)

def get_maps_api_key() -> Optional[str]:
    """
    Returns only the GOOGLE_MAPS_API_KEY for location services.
    """
    return os.getenv("GOOGLE_MAPS_API_KEY")

def geocode_address(address: str) -> Optional[LatLng]:
    """
    Geocodes an address string into LatLng coordinates using Google Maps Geocoding API.
    """
    api_key = get_maps_api_key()
    if not api_key:
        print("CRITICAL: GOOGLE_MAPS_API_KEY not found in environment for Geocoding!")
        return None
    
    # Masked key for security verification in logs
    masked_key = f"{api_key[:5]}...{api_key[-4:]}"
    print(f"API CALL (Maps): Geocoding '{address}' using Key: {masked_key}")
    
    params = {
        "address": address,
        "key": api_key
    }
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    try:
        response = httpx.get(url, params=params, timeout=30.0, verify=False)
        data = response.json()
        if data["status"] == "OK":
            loc = data["results"][0]["geometry"]["location"]
            return LatLng(lat=loc["lat"], lng=loc["lng"])
        else:
            error_msg = data.get("error_message", "No specific error message provided.")
            print(f"Geocoding API status: {data['status']}. Error: {error_msg}")
    except Exception as e:
        print(f"Geocoding error: {e}")
    return None

def find_destination_via_api(start: LatLng, keyword: str, distance_km: float) -> Optional[LatLng]:
    """
    Uses Google Maps Places API (Nearby Search) to find a destination that matches the keyword
    and is roughly around the target distance radius.
    """
    api_key = get_maps_api_key()
    if not api_key:
        print("CRITICAL: GOOGLE_MAPS_API_KEY missing for Places API!")
        return None
        
    radius_meters = int(distance_km * 1000)
    # If no keyword is provided, we can use a generic nice destination like 'park'
    search_keyword = keyword if keyword else "park"
    
    params = {
        "location": f"{start.lat},{start.lng}",
        "radius": radius_meters,
        "keyword": search_keyword,
        "key": api_key
    }
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    print(f"API CALL (Maps): Places Nearby Search for '{search_keyword}' at rad={radius_meters}m")
    
    try:
        response = httpx.get(url, params=params, timeout=30.0, verify=False)
        data = response.json()
        if data["status"] == "OK" and data.get("results"):
            # Select the first prominent result
            loc = data["results"][0]["geometry"]["location"]
            return LatLng(lat=loc["lat"], lng=loc["lng"])
        else:
            print(f"Places API status: {data['status']}")
    except Exception as e:
        print(f"Places API error: {e}")
        
    return None

def decode_polyline(polyline_str: str) -> List[LatLng]:
    """Decodes a Google Maps encoded polyline string into a list of LatLng coordinates."""
    index, lat, lng = 0, 0, 0
    coordinates = []
    length = len(polyline_str)
    
    while index < length:
        b, shift, result = 0, 0, 0
        while True:
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b >= 0x20:
                continue
            break
        dlat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += dlat
        
        shift, result = 0, 0
        while True:
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b >= 0x20:
                continue
            break
        dlng = ~(result >> 1) if (result & 1) else (result >> 1)
        lng += dlng
        
        coordinates.append(LatLng(lat=lat / 1e5, lng=lng / 1e5))
        
    return coordinates

def get_directions(origin: LatLng, destination: LatLng, mode: str, waypoints: List[LatLng] = []) -> Tuple[List[LatLng], float]:
    """
    Fetches directions and distance from Google Maps Directions API.
    """
    api_key = get_maps_api_key()
    if not api_key:
        print("CRITICAL: GOOGLE_MAPS_API_KEY not found in environment for Directions!")
        return [], 0.0
    
    masked_key = f"{api_key[:5]}...{api_key[-4:]}"
    print(f"API CALL (Maps): Directions using Key: {masked_key}")
    
    # Map app modes to Google travel modes
    travel_mode = "walking"
    if mode.lower() == "running":
        travel_mode = "walking"
    elif mode.lower() == "jogging":
        travel_mode = "walking"
        
    origin_str = f"{origin.lat},{origin.lng}"
    dest_str = f"{destination.lat},{destination.lng}"
    
    params = {
        "origin": f"{origin.lat},{origin.lng}",
        "destination": f"{destination.lat},{destination.lng}",
        "mode": travel_mode,
        "key": api_key
    }
    
    if waypoints:
        params["waypoints"] = "|".join([f"{wp.lat},{wp.lng}" for wp in waypoints])
        
    url = "https://maps.googleapis.com/maps/api/directions/json"
    
    try:
        response = httpx.get(url, params=params, timeout=30.0, verify=False)
        data = response.json()
        if data["status"] == "OK":
            route = data["routes"][0]
            total_dist_meters = 0
            
            for leg in route["legs"]:
                total_dist_meters += leg["distance"]["value"]
                
            # Use overview_polyline for a perfectly smooth, road-snapped path
            path_points = []
            poly_str = route.get("overview_polyline", {}).get("points", "")
            if poly_str:
                path_points = decode_polyline(poly_str)
            else:
                # Fallback to steps if polyline is missing
                for leg in route["legs"]:
                    for step in leg["steps"]:
                        path_points.append(LatLng(lat=step["start_location"]["lat"], lng=step["start_location"]["lng"]))
                    path_points.append(LatLng(lat=leg["end_location"]["lat"], lng=leg["end_location"]["lng"]))
                
            return path_points, total_dist_meters / 1000.0
        else:
            error_msg = data.get("error_message", "No specific error message provided.")
            print(f"Directions API status: {data['status']}. Error: {error_msg}")
    except Exception as e:
        print(f"Directions error: {e}")
    
    return [], 0.0

def find_loop_waypoint(start: LatLng, distance_km: float) -> LatLng:
    """
    Calculates a waypoint roughly distance_km/4 away to facilitate a loop track.
    """
    radius = distance_km / 4.0
    lat_offset = radius / 111.0
    lng_offset = radius / (111.0 * math.cos(math.radians(start.lat)))
    
    angle = random.uniform(0, 2 * math.pi)
    new_lat = start.lat + lat_offset * math.sin(angle)
    new_lng = start.lng + lng_offset * math.cos(angle)
    
    return LatLng(lat=new_lat, lng=new_lng)

def interpolate_path(path: List[LatLng], min_points: int = 25) -> List[LatLng]:
    """Ensures a path has enough points for coin placement by interpolating between sparse points."""
    if len(path) >= min_points or len(path) < 2:
        return path
    
    new_path = []
    points_to_add = (min_points - len(path)) // (len(path) - 1) + 1
    
    for i in range(len(path) - 1):
        p1 = path[i]
        p2 = path[i+1]
        new_path.append(p1)
        for j in range(1, points_to_add + 1):
            fraction = j / (points_to_add + 1)
            new_path.append(LatLng(
                lat = p1.lat + (p2.lat - p1.lat) * fraction,
                lng = p1.lng + (p2.lng - p1.lng) * fraction
            ))
    new_path.append(path[-1])
    return new_path

def place_random_coins(path: List[LatLng], num_coins: int) -> List[Coin]:
    """
    Randomly places gamified coins along the provided path coordinates.
    Now uses interpolation to ensure coins show up even on short tracks.
    """
    smooth_path = interpolate_path(path)
    if not smooth_path or len(smooth_path) < 2:
        return []
    
    coins = []
    # Avoid first and last points for better gameplay
    eligible_points = smooth_path[1:-1] if len(smooth_path) > 3 else smooth_path
    count = min(num_coins, len(eligible_points))
    chosen_indices = random.sample(range(len(eligible_points)), count)
    
    for idx in chosen_indices:
        p = eligible_points[idx]
        val = random.choice([10, 10, 10, 20, 20, 50])
        coins.append(Coin(lat=p.lat, lng=p.lng, value=val))
    
    return coins

def calculate_workout_metrics(weight_kg: float, distance_km: float, mode: str) -> Tuple[float, float]:
    """
    Calculates estimated duration (hours) and calories burned using MET values.
    """
    mets = {"walking": 3.5, "jogging": 7.0, "running": 11.5}
    speeds = {"walking": 5.0, "jogging": 8.5, "running": 12.0}
    
    m = mode.lower()
    met = mets.get(m, 3.5)
    speed = speeds.get(m, 5.0)
    
    duration_hours = distance_km / speed
    calories = met * weight_kg * duration_hours
    
    return duration_hours, calories
