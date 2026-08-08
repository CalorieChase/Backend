import os
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from app.models.domain import AgentState, LatLng, TrackRequest, WorkoutState
from app.services.maps import (
    calculate_workout_metrics,
    find_destination_via_api,
    find_loop_waypoint,
    geocode_address,
    get_directions,
    place_random_coins,
)

load_dotenv(override=True)

api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_API_KEY")
if not api_key:
    print("CRITICAL: OPENAI_API_KEY not found in environment!")
else:
    print(f"DEBUG: OpenAI API Key loaded (masked): {api_key[:5]}...{api_key[-4:]}")

llm = ChatOpenAI(model="gpt-4o", api_key=api_key)


def parse_request_node(state: AgentState) -> Dict[str, Any]:
    """Parse the user prompt into structured fields using AI, or reuse provided fields."""
    user_input = state.get("summary", "")

    try:
        print(f"DEBUG: AI Parsing request from prompt: {user_input}")
        structured_llm = llm.with_structured_output(TrackRequest)
        request = structured_llm.invoke(
            "Extract workout details from this prompt. IMPORTANT: Only look for local "
            f"destinations near the starting point. Prompt: {user_input}"
        )
    except Exception as exc:
        print(f"ERROR: AI Parsing failed: {exc}. Using fallback values.")
        request = None

    return {
        "start_location": state.get("start_location")
        or (request.start_location if request else "Current Location"),
        "destination": state.get("destination")
        or (request.destination if request else None)
        or state.get("start_location"),
        "target_distance": state.get("target_distance") or (request.target_distance if request else 2.0),
        "mode": state.get("mode") or (request.mode if request else "running"),
        "keyword_search": request.keyword_search if request else None,
        "height": state.get("height") or (request.height if request else 175.0) or 175.0,
        "weight": state.get("weight") or (request.weight if request else 70.0) or 70.0,
    }


def generate_track_node(state: AgentState) -> Dict[str, Any]:
    """Geocode locations and generate the route path and waypoints."""
    start_loc = state["start_location"]
    start_coords = geocode_address(start_loc)

    if not start_coords:
        llm_coords = llm.with_structured_output(LatLng).invoke(
            f"What are the approximate latitude and longitude coordinates of {start_loc}? "
            "Respond only with the coordinates."
        )
        start_coords = llm_coords

    dest_loc = state.get("destination", "")
    keyword = state.get("keyword_search", "")
    target_dist = state["target_distance"]

    is_loop = False
    if not dest_loc or dest_loc.strip() == "" or dest_loc == start_loc:
        print(f"DEBUG: Loop Mode requested (dist={target_dist}km). Finding goal at {target_dist / 2}km.")
        is_loop = True
        try:
            dest_coords = find_destination_via_api(start_coords, keyword, target_dist / 2.0)
        except Exception as exc:
            print(f"Places API failed: {exc}")
            dest_coords = None

        if not dest_coords:
            dest_coords = find_loop_waypoint(start_coords, target_dist / 2.0)
    else:
        print(f"DEBUG: Point-to-Point Mode requested: {dest_loc}")
        dest_coords = geocode_address(dest_loc)
        if not dest_coords:
            dest_coords = llm.with_structured_output(LatLng).invoke(
                f"What are the approximate latitude and longitude coordinates of {dest_loc}? "
                "Respond only with the coordinates."
            )

    if not start_coords or not dest_coords:
        raise ValueError("Failed to resolve stable coordinates.")

    if is_loop:
        path, actual_dist = get_directions(start_coords, start_coords, state["mode"], waypoints=[dest_coords])
    else:
        path, actual_dist = get_directions(start_coords, dest_coords, state["mode"])

    if not path or actual_dist == 0:
        actual_dist = target_dist
        path = [start_coords, dest_coords]
        if is_loop:
            path.append(start_coords)

    if actual_dist > target_dist * 5.0:
        print(f"CRITICAL: Track too long ({actual_dist}km). Forcing micro-loop.")
        dest_coords = find_loop_waypoint(start_coords, target_dist / 4.0)
        path, actual_dist = get_directions(start_coords, start_coords, state["mode"], waypoints=[dest_coords])

    coins = place_random_coins(path, num_coins=12)
    return {
        "start_coords": start_coords,
        "dest_coords": dest_coords,
        "waypoints": path,
        "coins": coins,
        "actual_distance": actual_dist,
        "num_coins": len(coins),
        "total_score": len(coins) * 10,
    }


def calculate_planned_workout_node(state: AgentState) -> Dict[str, Any]:
    """Calculate estimated calories for the generated track."""
    _, calories = calculate_workout_metrics(state["weight"], state["actual_distance"], state["mode"])
    return {"estimated_calories": calories}


def summarize_node(state: AgentState) -> Dict[str, Any]:
    """Generate the final summary string for the user."""
    prompt = (
        f"Write a friendly summary for a {state['mode']} track: {state['actual_distance']}km long, "
        f"{state['num_coins']} coins hidden, {state['total_score']} total points, and estimated "
        f"{round(state['estimated_calories'], 1)} calories burned."
    )
    summary_resp = llm.invoke(prompt)
    summary_content = summary_resp.content

    if isinstance(summary_content, list):
        summary = "".join(
            part["text"]
            for part in summary_content
            if isinstance(part, dict) and "text" in part
        )
    else:
        summary = str(summary_content)

    return {"summary": summary}


track_workflow = StateGraph(AgentState)
track_workflow.add_node("parse", parse_request_node)
track_workflow.add_node("generate", generate_track_node)
track_workflow.add_node("calculate_workout", calculate_planned_workout_node)
track_workflow.add_node("summarize", summarize_node)
track_workflow.set_entry_point("parse")
track_workflow.add_edge("parse", "generate")
track_workflow.add_edge("generate", "calculate_workout")
track_workflow.add_edge("calculate_workout", "summarize")
track_workflow.add_edge("summarize", END)
track_app = track_workflow.compile()


def workout_calc_node(state: WorkoutState) -> Dict[str, Any]:
    duration, calories = calculate_workout_metrics(state["weight"], state["distance_crossed"], state["mode"])
    return {"duration_hours": duration, "calories_burned": calories}


def workout_summary_node(state: WorkoutState) -> Dict[str, Any]:
    prompt = (
        f"Great job! The user just finished a {state['distance_crossed']}km {state['mode']}. "
        f"They burned approximately {round(state['calories_burned'], 2)} calories. "
        "Write a motivational 1-sentence summary."
    )
    summary = llm.invoke(prompt).content
    return {"summary": summary}


workout_workflow = StateGraph(WorkoutState)
workout_workflow.add_node("calculate", workout_calc_node)
workout_workflow.add_node("summarize", workout_summary_node)
workout_workflow.set_entry_point("calculate")
workout_workflow.add_edge("calculate", "summarize")
workout_workflow.add_edge("summarize", END)
workout_app = workout_workflow.compile()
