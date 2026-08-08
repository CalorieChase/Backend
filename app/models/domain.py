from typing import List, Optional, TypedDict

from pydantic import BaseModel, Field


class LatLng(BaseModel):
    lat: float
    lng: float


class Coin(BaseModel):
    lat: float
    lng: float
    value: int = 10


class AgentState(TypedDict):
    start_location: str
    destination: Optional[str]
    target_distance: float
    mode: str
    keyword_search: Optional[str]
    height: float
    weight: float
    start_coords: Optional[LatLng]
    dest_coords: Optional[LatLng]
    waypoints: List[LatLng]
    coins: List[Coin]
    actual_distance: float
    estimated_calories: float
    num_coins: int
    total_score: int
    summary: str


class TrackRequest(BaseModel):
    """Schema for parsing user requests for a track."""

    start_location: str = Field(description="The starting point of the track")
    destination: Optional[str] = Field(
        description="The destination point. If same as start or empty, assume a loop."
    )
    target_distance: float = Field(description="The desired distance for the track in kilometers")
    mode: str = Field(description="The mode of travel: running, walking, or jogging")
    keyword_search: Optional[str] = Field(
        description="Specific type of destination the user wants (e.g. beach, cafe, gym, lake)"
    )
    height: Optional[float] = Field(description="User height in cm", default=175.0)
    weight: Optional[float] = Field(description="User weight in kg", default=70.0)


class WorkoutRequest(BaseModel):
    """Schema for tracking workout progress."""

    height: float = Field(description="Height in cm")
    weight: float = Field(description="Weight in kg")
    distance_crossed: float = Field(description="Actual distance completed in km")
    mode: str = Field(description="The mode: running, walking, or jogging")


class WorkoutState(TypedDict):
    height: float
    weight: float
    distance_crossed: float
    mode: str
    duration_hours: float
    calories_burned: float
    summary: str
