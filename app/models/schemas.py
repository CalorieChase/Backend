from typing import List, Optional

from pydantic import BaseModel


class RouteRequest(BaseModel):
    starting_point: str
    ending_point: Optional[str] = None
    prompt: Optional[str] = ""
    activity_type: str
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
