import os
import traceback

from fastapi import APIRouter, HTTPException

from app.agents.workflow import route_app
from app.models.schemas import CoinModel, LatLngModel, RouteRequest, RouteResponse

router = APIRouter()


@router.get("/")
async def root() -> dict[str, str]:
    return {"message": "CalorieChase backend is running"}


@router.post("/generate-route", response_model=RouteResponse)
async def generate_route(request: RouteRequest) -> RouteResponse:
    try:
        initial_state = {
            "starting_location": request.starting_location,
            "weight_kg": request.weight_kg,
            "goal_type": request.goal_type,
            "goal_value": request.goal_value,
            "route_type": request.route_type,
            "start_coords": None,
            "target_distance_km": 0.0,
            "estimated_active_calories": 0.0,
            "route_coordinates": [],
            "route_polyline": "",
            "total_distance_km": 0.0,
            "final_route_type": request.route_type,
            "gold_coins": [],
        }
        result = route_app.invoke(initial_state)

        return RouteResponse(
            routeCoordinates=[
                LatLngModel(lat=point.lat, lng=point.lng) for point in result["route_coordinates"]
            ],
            routePolyline=result["route_polyline"],
            routeType=result["final_route_type"],
            totalDistanceKm=result["total_distance_km"],
            estimatedActiveCalories=result["estimated_active_calories"],
            goldCoins=[
                CoinModel(lat=coin.lat, lng=coin.lng, value=coin.value) for coin in result["gold_coins"]
            ],
        )
    except Exception as exc:
        error_trace = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(exc),
                "trace": error_trace
                if os.environ.get("DEBUG") == "True"
                else "Check server logs for traceback",
            },
        ) from exc
