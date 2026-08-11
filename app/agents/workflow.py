from typing import Any

from langgraph.graph import END, StateGraph

from app.models.domain import RouteWorkflowState, WorkoutState
from app.services.maps import (
    WALKING_SPEED_KMH,
    calculate_workout_metrics,
    choose_route_candidate,
    encode_polyline,
    geocode_address,
    is_valid_route_distance,
    place_route_coins,
)

WALKING_MET = 3.8
ACTIVE_MET = WALKING_MET - 1.0


def input_node(state: RouteWorkflowState) -> dict[str, Any]:
    """Resolve the starting location into coordinates."""
    start_coords = geocode_address(state["starting_location"])
    if not start_coords:
        raise ValueError("Unable to resolve the starting location into coordinates.")

    return {"start_coords": start_coords}


def goal_normalizer_node(state: RouteWorkflowState) -> dict[str, float]:
    """Normalize all goals into a target distance and estimated active calories."""
    goal_type = state["goal_type"]
    goal_value = state["goal_value"]
    weight_kg = state["weight_kg"]

    if goal_type == "distance":
        target_distance_km = goal_value
        time_hours = target_distance_km / WALKING_SPEED_KMH
        estimated_active_calories = ACTIVE_MET * weight_kg * time_hours
    else:
        estimated_active_calories = goal_value
        time_hours = estimated_active_calories / (ACTIVE_MET * weight_kg)
        target_distance_km = time_hours * WALKING_SPEED_KMH

    return {
        "target_distance_km": target_distance_km,
        "estimated_active_calories": estimated_active_calories,
    }


def route_generator_node(state: RouteWorkflowState) -> dict[str, Any]:
    """Generate and validate the final route candidate."""
    candidate = choose_route_candidate(
        start=state["start_coords"],
        route_type=state["route_type"],
        target_distance_km=state["target_distance_km"],
    )
    if not candidate.coordinates:
        raise ValueError("Route generation failed to produce a valid path.")

    if not is_valid_route_distance(candidate.distance_km, state["target_distance_km"]):
        raise ValueError("Generated route is too far from the target distance.")

    return {
        "route_coordinates": candidate.coordinates,
        "total_distance_km": candidate.distance_km,
        "final_route_type": candidate.route_type,
    }


def coin_placement_node(state: RouteWorkflowState) -> dict[str, Any]:
    """Place gold coins directly on the final route path."""
    return {"gold_coins": place_route_coins(state["route_coordinates"])}


def response_node(state: RouteWorkflowState) -> dict[str, Any]:
    """Assemble the API-ready response fields."""
    return {"route_polyline": encode_polyline(state["route_coordinates"])}


route_workflow = StateGraph(RouteWorkflowState)
route_workflow.add_node("input", input_node)
route_workflow.add_node("goal_normalizer", goal_normalizer_node)
route_workflow.add_node("route_generator", route_generator_node)
route_workflow.add_node("coin_placement", coin_placement_node)
route_workflow.add_node("response", response_node)
route_workflow.set_entry_point("input")
route_workflow.add_edge("input", "goal_normalizer")
route_workflow.add_edge("goal_normalizer", "route_generator")
route_workflow.add_edge("route_generator", "coin_placement")
route_workflow.add_edge("coin_placement", "response")
route_workflow.add_edge("response", END)
route_app = route_workflow.compile()


def workout_calc_node(state: WorkoutState) -> dict[str, Any]:
    duration, calories = calculate_workout_metrics(state["weight"], state["distance_crossed"], state["mode"])
    return {"duration_hours": duration, "calories_burned": calories}


def workout_summary_node(state: WorkoutState) -> dict[str, str]:
    summary = (
        f"Completed {state['distance_crossed']:.2f} km of {state['mode']} and burned "
        f"about {state['calories_burned']:.1f} calories."
    )
    return {"summary": summary}


workout_workflow = StateGraph(WorkoutState)
workout_workflow.add_node("calculate", workout_calc_node)
workout_workflow.add_node("summarize", workout_summary_node)
workout_workflow.set_entry_point("calculate")
workout_workflow.add_edge("calculate", "summarize")
workout_workflow.add_edge("summarize", END)
workout_app = workout_workflow.compile()
