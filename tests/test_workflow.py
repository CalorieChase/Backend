from app.agents.workflow import goal_normalizer_node, route_generator_node
from app.models.domain import LatLng


def test_goal_normalizer_for_distance_goal() -> None:
    result = goal_normalizer_node(
        {
            "starting_location": "37.7749,-122.4194",
            "weight_kg": 70.0,
            "goal_type": "distance",
            "goal_value": 4.8,
            "route_type": "LOOP",
            "start_coords": None,
            "target_distance_km": 0.0,
            "estimated_active_calories": 0.0,
            "route_coordinates": [],
            "route_polyline": "",
            "total_distance_km": 0.0,
            "final_route_type": "LOOP",
            "gold_coins": [],
        }
    )

    assert result["target_distance_km"] == 4.8
    assert result["estimated_active_calories"] == 196.0


def test_goal_normalizer_for_active_calorie_goal() -> None:
    result = goal_normalizer_node(
        {
            "starting_location": "37.7749,-122.4194",
            "weight_kg": 70.0,
            "goal_type": "active_calories",
            "goal_value": 196.0,
            "route_type": "TURNAROUND",
            "start_coords": None,
            "target_distance_km": 0.0,
            "estimated_active_calories": 0.0,
            "route_coordinates": [],
            "route_polyline": "",
            "total_distance_km": 0.0,
            "final_route_type": "TURNAROUND",
            "gold_coins": [],
        }
    )

    assert result["estimated_active_calories"] == 196.0
    assert result["target_distance_km"] == 4.8


def test_route_generator_uses_auto_candidate(monkeypatch) -> None:
    from app.agents import workflow
    from app.models.domain import RouteCandidate

    def fake_choose_route_candidate(start: LatLng, route_type: str, target_distance_km: float) -> RouteCandidate:
        assert start == LatLng(lat=37.7749, lng=-122.4194)
        assert route_type == "AUTO"
        assert target_distance_km == 3.2
        return RouteCandidate(
            route_type="TURNAROUND",
            coordinates=[
                LatLng(lat=37.7749, lng=-122.4194),
                LatLng(lat=37.7849, lng=-122.4194),
                LatLng(lat=37.7749, lng=-122.4194),
            ],
            distance_km=3.1,
        )

    monkeypatch.setattr(workflow, "choose_route_candidate", fake_choose_route_candidate)
    monkeypatch.setattr(workflow, "is_valid_route_distance", lambda actual, target: True)

    result = route_generator_node(
        {
            "starting_location": "37.7749,-122.4194",
            "weight_kg": 70.0,
            "goal_type": "distance",
            "goal_value": 3.2,
            "route_type": "AUTO",
            "start_coords": LatLng(lat=37.7749, lng=-122.4194),
            "target_distance_km": 3.2,
            "estimated_active_calories": 0.0,
            "route_coordinates": [],
            "route_polyline": "",
            "total_distance_km": 0.0,
            "final_route_type": "AUTO",
            "gold_coins": [],
        }
    )

    assert result["final_route_type"] == "TURNAROUND"
    assert result["total_distance_km"] == 3.1
    assert len(result["route_coordinates"]) == 3
