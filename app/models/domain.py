from typing import Literal, Optional, TypedDict

from pydantic import BaseModel, Field


GoalType = Literal["distance", "active_calories"]
RouteType = Literal["AUTO", "LOOP", "TURNAROUND"]


class LatLng(BaseModel):
    lat: float
    lng: float


class Coin(BaseModel):
    lat: float
    lng: float
    value: int = 10


class RouteCandidate(BaseModel):
    route_type: RouteType
    coordinates: list[LatLng]
    distance_km: float


class RouteWorkflowState(TypedDict):
    starting_location: str
    weight_kg: float
    goal_type: GoalType
    goal_value: float
    route_type: RouteType
    start_coords: Optional[LatLng]
    target_distance_km: float
    estimated_active_calories: float
    route_coordinates: list[LatLng]
    route_polyline: str
    total_distance_km: float
    final_route_type: RouteType
    gold_coins: list[Coin]


class WorkoutState(TypedDict):
    height: float
    weight: float
    distance_crossed: float
    mode: str
    duration_hours: float
    calories_burned: float
    summary: str


class WorkoutRequest(BaseModel):
    """Schema for tracking workout progress."""

    height: float = Field(description="Height in cm")
    weight: float = Field(description="Weight in kg")
    distance_crossed: float = Field(description="Actual distance completed in km")
    mode: str = Field(description="The mode: running, walking, or jogging")
