import hashlib
import math
import os
import random
from typing import Optional

import httpx
from dotenv import load_dotenv

from app.models.domain import Coin, LatLng, RouteCandidate, RouteType

load_dotenv(override=True)

EARTH_RADIUS_KM = 6371.0088
WALKING_SPEED_KMH = 4.8
COIN_VALUES = [10, 10, 10, 20, 20, 50]
AUTO_ROUTE_TOLERANCE_KM = 0.35
MAX_ROUTE_DISTANCE_ERROR_RATIO = 0.35


def get_maps_api_key() -> Optional[str]:
    """Returns only the Google Maps API key for location services."""
    return os.getenv("GOOGLE_MAPS_API_KEY")


def parse_lat_lng(value: str) -> Optional[LatLng]:
    """Parse a simple 'lat,lng' string before attempting remote geocoding."""
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 2:
        return None

    try:
        lat = float(parts[0])
        lng = float(parts[1])
    except ValueError:
        return None

    if not -90 <= lat <= 90 or not -180 <= lng <= 180:
        return None

    return LatLng(lat=lat, lng=lng)


def geocode_address(address: str) -> Optional[LatLng]:
    """Geocode an address string into coordinates using Google Maps."""
    parsed = parse_lat_lng(address)
    if parsed:
        return parsed

    api_key = get_maps_api_key()
    if not api_key:
        return None

    params = {"address": address, "key": api_key}
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    try:
        response = httpx.get(url, params=params, timeout=30.0, verify=False)
        data = response.json()
        if data["status"] == "OK":
            loc = data["results"][0]["geometry"]["location"]
            return LatLng(lat=loc["lat"], lng=loc["lng"])
    except Exception:
        return None

    return None


def decode_polyline(polyline_str: str) -> list[LatLng]:
    """Decode a Google Maps polyline string into coordinates."""
    index, lat, lng = 0, 0, 0
    coordinates: list[LatLng] = []
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


def encode_polyline(points: list[LatLng]) -> str:
    """Encode coordinates using the Google polyline algorithm."""

    def encode_value(value: int) -> str:
        value = ~(value << 1) if value < 0 else value << 1
        output = []
        while value >= 0x20:
            output.append(chr((0x20 | (value & 0x1F)) + 63))
            value >>= 5
        output.append(chr(value + 63))
        return "".join(output)

    last_lat = 0
    last_lng = 0
    encoded: list[str] = []

    for point in points:
        lat = int(round(point.lat * 1e5))
        lng = int(round(point.lng * 1e5))
        encoded.append(encode_value(lat - last_lat))
        encoded.append(encode_value(lng - last_lng))
        last_lat = lat
        last_lng = lng

    return "".join(encoded)


def get_directions(
    origin: LatLng,
    destination: LatLng,
    waypoints: Optional[list[LatLng]] = None,
) -> tuple[list[LatLng], float]:
    """Fetch walking directions and total distance from Google Maps."""
    api_key = get_maps_api_key()
    if not api_key:
        return [], 0.0

    params = {
        "origin": f"{origin.lat},{origin.lng}",
        "destination": f"{destination.lat},{destination.lng}",
        "mode": "walking",
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
                return decode_polyline(poly_str), total_dist_meters / 1000.0
    except Exception:
        return [], 0.0

    return [], 0.0


def calculate_workout_metrics(weight_kg: float, distance_km: float, mode: str) -> tuple[float, float]:
    """Calculate estimated duration and calories burned using MET values."""
    mets = {"walking": 3.5, "jogging": 7.0, "running": 11.5}
    speeds = {"walking": 5.0, "jogging": 8.5, "running": 12.0}

    normalized_mode = mode.lower()
    met = mets.get(normalized_mode, 3.5)
    speed = speeds.get(normalized_mode, 5.0)
    duration_hours = distance_km / speed
    calories = met * weight_kg * duration_hours
    return duration_hours, calories


def haversine_distance_km(start: LatLng, end: LatLng) -> float:
    """Calculate great-circle distance between two points."""
    lat1 = math.radians(start.lat)
    lon1 = math.radians(start.lng)
    lat2 = math.radians(end.lat)
    lon2 = math.radians(end.lng)
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def total_path_distance_km(points: list[LatLng]) -> float:
    """Calculate total path length across coordinate segments."""
    if len(points) < 2:
        return 0.0

    return sum(haversine_distance_km(points[index], points[index + 1]) for index in range(len(points) - 1))


def project_point(start: LatLng, distance_km: float, bearing_degrees: float) -> LatLng:
    """Project a point from a start coordinate at a fixed bearing and distance."""
    angular_distance = distance_km / EARTH_RADIUS_KM
    bearing = math.radians(bearing_degrees)
    lat1 = math.radians(start.lat)
    lng1 = math.radians(start.lng)

    lat2 = math.asin(
        math.sin(lat1) * math.cos(angular_distance)
        + math.cos(lat1) * math.sin(angular_distance) * math.cos(bearing)
    )
    lng2 = lng1 + math.atan2(
        math.sin(bearing) * math.sin(angular_distance) * math.cos(lat1),
        math.cos(angular_distance) - math.sin(lat1) * math.sin(lat2),
    )

    return LatLng(lat=math.degrees(lat2), lng=math.degrees(lng2))


def build_turnaround_route(start: LatLng, target_distance_km: float) -> RouteCandidate:
    """Build a deterministic out-and-back route, falling back to geometry when needed."""
    outward_target_km = max(target_distance_km / 2.0, 0.1)

    for bearing in (0.0, 90.0, 180.0, 270.0):
        destination = project_point(start, outward_target_km, bearing)
        outward_path, outward_distance_km = get_directions(start, destination)
        if outward_path and outward_distance_km > 0:
            return_path = list(reversed(outward_path[:-1])) if len(outward_path) > 1 else [start]
            coordinates = outward_path + return_path
            return RouteCandidate(
                route_type="TURNAROUND",
                coordinates=coordinates,
                distance_km=outward_distance_km * 2.0,
            )

    destination = project_point(start, outward_target_km, 0.0)
    coordinates = [start, destination, start]
    return RouteCandidate(
        route_type="TURNAROUND",
        coordinates=coordinates,
        distance_km=total_path_distance_km(coordinates),
    )


def build_loop_route(start: LatLng, target_distance_km: float) -> RouteCandidate:
    """Build a deterministic loop route near the requested target distance."""
    loop_radius_km = max(target_distance_km / (2.0 * math.pi), 0.08)
    best_candidate: Optional[RouteCandidate] = None

    for rotation in (0.0, 45.0):
        bearings = [rotation, rotation + 90.0, rotation + 180.0, rotation + 270.0]
        waypoints = [project_point(start, loop_radius_km, bearing) for bearing in bearings]
        loop_waypoints = waypoints + [start]
        path, distance_km = get_directions(start, start, waypoints=waypoints)
        if path and distance_km > 0:
            candidate = RouteCandidate(
                route_type="LOOP",
                coordinates=path,
                distance_km=distance_km,
            )
        else:
            candidate = RouteCandidate(
                route_type="LOOP",
                coordinates=[start] + loop_waypoints,
                distance_km=total_path_distance_km([start] + loop_waypoints),
            )

        if best_candidate is None or abs(candidate.distance_km - target_distance_km) < abs(
            best_candidate.distance_km - target_distance_km
        ):
            best_candidate = candidate

    if best_candidate is None:
        return RouteCandidate(route_type="LOOP", coordinates=[start], distance_km=0.0)

    return best_candidate


def is_valid_route_distance(actual_distance_km: float, target_distance_km: float) -> bool:
    """Validate a generated route against the target distance."""
    if target_distance_km <= 0:
        return False

    allowed_error = max(AUTO_ROUTE_TOLERANCE_KM, target_distance_km * MAX_ROUTE_DISTANCE_ERROR_RATIO)
    return abs(actual_distance_km - target_distance_km) <= allowed_error


def choose_route_candidate(start: LatLng, route_type: RouteType, target_distance_km: float) -> RouteCandidate:
    """Generate a route candidate based on the requested route type."""
    if route_type == "LOOP":
        return build_loop_route(start, target_distance_km)

    if route_type == "TURNAROUND":
        return build_turnaround_route(start, target_distance_km)

    candidates = [
        build_loop_route(start, target_distance_km),
        build_turnaround_route(start, target_distance_km),
    ]
    valid_candidates = [
        candidate for candidate in candidates if is_valid_route_distance(candidate.distance_km, target_distance_km)
    ]
    pool = valid_candidates or candidates
    return min(pool, key=lambda candidate: abs(candidate.distance_km - target_distance_km))


def interpolate_path(path: list[LatLng], min_points: int = 25) -> list[LatLng]:
    """Ensure a path has enough points for coin placement."""
    if len(path) >= min_points or len(path) < 2:
        return path

    new_path: list[LatLng] = []
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


def build_route_seed(path: list[LatLng]) -> int:
    """Build a deterministic seed from the final route geometry."""
    digest = hashlib.sha256(
        "|".join(f"{point.lat:.5f},{point.lng:.5f}" for point in path).encode("utf-8")
    ).hexdigest()
    return int(digest[:16], 16)


def place_route_coins(path: list[LatLng], num_coins: int = 12) -> list[Coin]:
    """Place deterministic coins directly on the route coordinates."""
    smooth_path = interpolate_path(path)
    if len(smooth_path) < 3:
        return []

    eligible_points = smooth_path[1:-1]
    count = min(num_coins, len(eligible_points))
    rng = random.Random(build_route_seed(smooth_path))
    chosen_indices = sorted(rng.sample(range(len(eligible_points)), count))

    coins: list[Coin] = []
    for idx in chosen_indices:
        point = eligible_points[idx]
        coins.append(Coin(lat=point.lat, lng=point.lng, value=rng.choice(COIN_VALUES)))

    return coins
