import os
import traceback

from fastapi import APIRouter, HTTPException

from app.agents.workflow import track_app
from app.models.schemas import CoinModel, LatLngModel, RouteRequest, RouteResponse

router = APIRouter()


@router.get("/")
async def root() -> dict[str, str]:
    return {"message": "Location Agent API is running"}


@router.post("/generate-route", response_model=RouteResponse)
async def generate_route(request: RouteRequest) -> RouteResponse:
    try:
        activity_mapping = {"walk": "walking", "jog": "jogging", "run": "running"}
        mode = activity_mapping.get(request.activity_type.lower(), request.activity_type.lower())

        initial_state = {
            "start_location": request.starting_point,
            "destination": request.ending_point,
            "target_distance": request.distance,
            "mode": mode,
            "keyword_search": None,
            "height": request.height,
            "weight": request.weight,
            "summary": request.prompt or f"I want to {mode} {request.distance}km from {request.starting_point}",
            "waypoints": [],
            "coins": [],
            "actual_distance": 0.0,
            "estimated_calories": 0.0,
            "num_coins": 0,
            "total_score": 0,
        }

        print(f"DEBUG: Generating route for: {request.starting_point} -> {request.ending_point} ({mode})")
        result = track_app.invoke(initial_state)

        return RouteResponse(
            route=[LatLngModel(lat=point.lat, lng=point.lng) for point in result["waypoints"]],
            coins=[CoinModel(lat=coin.lat, lng=coin.lng, value=coin.value) for coin in result["coins"]],
            est_distance=result["actual_distance"],
            est_cal=result["estimated_calories"],
            summary=result["summary"],
            destination=LatLngModel(
                lat=result["dest_coords"].lat,
                lng=result["dest_coords"].lng,
            ),
        )
    except Exception as exc:
        error_trace = traceback.format_exc()
        print(f"ERROR in /generate-route: {exc}")
        print(error_trace)
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(exc),
                "trace": error_trace
                if os.environ.get("DEBUG") == "True"
                else "Check server logs for traceback",
            },
        ) from exc
