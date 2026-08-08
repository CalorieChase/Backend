from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from agent import track_app
import uvicorn

app = FastAPI(title="Location Agent API")

class RouteRequest(BaseModel):
    starting_point: str
    ending_point: Optional[str] = None
    prompt: Optional[str] = ""
    activity_type: str  # walk, jog, run
    distance: float
    height: Optional[float] = 175.0
    weight: Optional[float] = 70.0

class LatLngModel(BaseModel):
    lat: float
    lng: float

class CoinModel(BaseModel):
    lat: float
    lng: float
    value: int

class RouteResponse(BaseModel):
    route: List[LatLngModel]
    coins: List[CoinModel]
    est_distance: float
    est_cal: float
    summary: str
    destination: LatLngModel

@app.get("/")
async def root():
    return {"message": "Location Agent API is running"}

@app.post("/generate-route", response_model=RouteResponse)
async def generate_route(request: RouteRequest):
    try:
        # Map activity names for consistency with tool logic
        activity_mapping = {
            "walk": "walking",
            "jog": "jogging",
            "run": "running"
        }
        mode = activity_mapping.get(request.activity_type.lower(), request.activity_type.lower())

        # Prepare the initial state for the LangGraph agent
        # Mapping our parameters to the AgentState keys
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
            "total_score": 0
        }
        
        # Invoke the LangGraph track_app
        print(f"DEBUG: Generating route for: {request.starting_point} -> {request.ending_point} ({mode})")
        result = track_app.invoke(initial_state)
        
        return RouteResponse(
            route=[LatLngModel(lat=p.lat, lng=p.lng) for p in result["waypoints"]],
            coins=[CoinModel(lat=c.lat, lng=c.lng, value=c.value) for c in result["coins"]],
            est_distance=result["actual_distance"],
            est_cal=result["estimated_calories"],
            summary=result["summary"],
            destination=LatLngModel(lat=result["dest_coords"].lat, lng=result["dest_coords"].lng)
        )
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"ERROR in /generate-route: {str(e)}")
        print(error_trace)
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "trace": error_trace if os.environ.get("DEBUG") == "True" else "Check server logs for traceback"
            }
        )

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
