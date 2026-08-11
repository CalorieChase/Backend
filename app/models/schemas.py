from pydantic import BaseModel, Field

from app.models.domain import GoalType, RouteType


class RouteRequest(BaseModel):
    starting_location: str = Field(alias="startingLocation")
    weight_kg: float = Field(alias="weightKg", gt=0)
    goal_type: GoalType = Field(alias="goalType")
    goal_value: float = Field(alias="goalValue", gt=0)
    route_type: RouteType = Field(alias="routeType")

    model_config = {"populate_by_name": True}


class LatLngModel(BaseModel):
    lat: float
    lng: float


class CoinModel(BaseModel):
    lat: float
    lng: float
    value: int


class RouteResponse(BaseModel):
    route_coordinates: list[LatLngModel] = Field(alias="routeCoordinates")
    route_polyline: str = Field(alias="routePolyline")
    route_type: RouteType = Field(alias="routeType")
    total_distance_km: float = Field(alias="totalDistanceKm")
    estimated_active_calories: float = Field(alias="estimatedActiveCalories")
    gold_coins: list[CoinModel] = Field(alias="goldCoins")

    model_config = {"populate_by_name": True}
