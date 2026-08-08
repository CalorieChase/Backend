import os
from dotenv import load_dotenv
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from models import AgentState, TrackRequest, WorkoutState, WorkoutRequest, LatLng
from tools import geocode_address, get_directions, place_random_coins, find_loop_waypoint, calculate_workout_metrics, find_destination_via_api

load_dotenv(override=True)

# Initialize Gemini-powered LLM
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPEN_API_KEY")
if not api_key:
    print("CRITICAL: GEMINI_API_KEY not found in environment!")
else:
    print(f"DEBUG: Gemini Intelligence strictly using API Key (masked): {api_key[:5]}...{api_key[-4:]}")

# Using GPT-4o as the underlying engine but branded for Gemini-tier reasoning
llm = ChatOpenAI(model="gpt-4o", api_key=api_key)

def parse_request_node(state: AgentState) -> Dict[str, Any]:
    """Parses the user prompt into structured fields using AI, or uses existing fields."""
    
    user_input = state.get("summary", "")
    
    # Run structured parsing to find the theme/keyword even if other params are known
    try:
        print(f"DEBUG: AI Parsing request from prompt: {user_input}")
        structured_llm = llm.with_structured_output(TrackRequest)
        request = structured_llm.invoke(f"Extract workout details from this prompt. IMPORTANT: Only look for local destinations near the starting point. Prompt: {user_input}")
    except Exception as e:
        print(f"ERROR: AI Parsing failed: {e}. Using fallback values.")
        request = None

    # Merge provided state with AI-parsed results
    # state values (from the UI form) take priority over AI guesses
    return {
        "start_location": state.get("start_location") or (request.start_location if request else "Current Location"),
        "destination": state.get("destination") or (request.destination if request else None) or state.get("start_location"),
        "target_distance": state.get("target_distance") or (request.target_distance if request else 2.0),
        "mode": state.get("mode") or (request.mode if request else "running"),
        "keyword_search": request.keyword_search if request else None,
        "height": state.get("height") or (request.height if request else 175.0) or 175.0,
        "weight": state.get("weight") or (request.weight if request else 70.0) or 70.0
    }

def generate_track_node(state: AgentState) -> Dict[str, Any]:
    """Geocodes locations and generates the track path and waypoints."""
    start_loc = state["start_location"]
    start_coords = geocode_address(start_loc)
    
    # Fallback for geocoding
    if not start_coords:
        llm_coords = llm.with_structured_output(LatLng).invoke(f"What are the approximate latitude and longitude coordinates of {start_loc}? Respond only with the coordinates.")
        start_coords = llm_coords
    
    dest_loc = state.get("destination", "")
    keyword = state.get("keyword_search", "")
    target_dist = state["target_distance"]
    
    is_loop = False
    if not dest_loc or dest_loc.strip() == "" or dest_loc == start_loc:
        print(f"DEBUG: Loop Mode requested (dist={target_dist}km). Finding goal at {target_dist/2}km.")
        is_loop = True
        # Find a destination roughly HALF the target distance away to make a round trip
        try:
            dest_coords = find_destination_via_api(start_coords, keyword, target_dist / 2.0)
        except Exception as e:
            print(f"Places API failed: {e}")
            dest_coords = None
            
        if not dest_coords:
            dest_coords = find_loop_waypoint(start_coords, target_dist / 2.0)
    else:
        print(f"DEBUG: Point-to-Point Mode requested: {dest_loc}")
        dest_coords = geocode_address(dest_loc)
        if not dest_coords:
            dest_coords = llm.with_structured_output(LatLng).invoke(f"What are the approximate latitude and longitude coordinates of {dest_loc}? Respond only with the coordinates.")
            
    if not start_coords or not dest_coords:
        raise ValueError("Failed to resolve stable coordinates.")

    # Get directions
    if is_loop:
        # Create a loop by adding start as the final destination
        path, actual_dist = get_directions(start_coords, start_coords, state["mode"], waypoints=[dest_coords])
    else:
        path, actual_dist = get_directions(start_coords, dest_coords, state["mode"])
    
    # Fallback for directions - create a simple path if API fails
    if not path or actual_dist == 0:
        actual_dist = target_dist
        path = [start_coords, dest_coords]
        if is_loop: path.append(start_coords)
    
    # SANITY CHECK: Hallucination Guardrail
    if actual_dist > target_dist * 5.0:
        print(f"CRITICAL: Track too long ({actual_dist}km). Forcing micro-loop.")
        dest_coords = find_loop_waypoint(start_coords, target_dist / 4.0)
        path, actual_dist = get_directions(start_coords, start_coords, state["mode"], waypoints=[dest_coords])

    # Place random coins on the path (with interpolation inside the tool)
    coins = place_random_coins(path, num_coins=12)
    
    return {
        "start_coords": start_coords,
        "dest_coords": dest_coords,
        "waypoints": path,
        "coins": coins,
        "actual_distance": actual_dist,
        "num_coins": len(coins),
        "total_score": len(coins) * 10
    }

def calculate_planned_workout_node(state: AgentState) -> Dict[str, Any]:
    """Calculates estimated calories for the generated track."""
    # We reuse the logic from the tools
    duration, calories = calculate_workout_metrics(state["weight"], state["actual_distance"], state["mode"])
    return {"estimated_calories": calories}

def summarize_node(state: AgentState) -> Dict[str, Any]:
    """Generates the final summary string for the user."""
    dist = state["actual_distance"]
    coins = state["num_coins"]
    score = state["total_score"]
    cals = round(state["estimated_calories"], 1)
    mode = state["mode"]
    
    # Ask Gemini to write a friendly summary
    prompt = f"Write a friendly summary for a {mode} track: {dist}km long, {coins} coins hidden, {score} total points, and estimated {cals} calories burned."
    summary_resp = llm.invoke(prompt)
    summary_content = summary_resp.content
    
    # Handle both string and list content (multimodal responses)
    if isinstance(summary_content, list):
        summary = "".join([part["text"] for part in summary_content if isinstance(part, dict) and "text" in part])
    else:
        summary = str(summary_content)
    
    return {"summary": summary}

# Track Workflow logic...
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

# --- Workout Workflow ---

def workout_calc_node(state: WorkoutState) -> Dict[str, Any]:
    duration, calories = calculate_workout_metrics(state["weight"], state["distance_crossed"], state["mode"])
    return {
        "duration_hours": duration,
        "calories_burned": calories
    }

def workout_summary_node(state: WorkoutState) -> Dict[str, Any]:
    calories = round(state["calories_burned"], 2)
    dist = state["distance_crossed"]
    mode = state["mode"]
    
    prompt = f"Great job! The user just finished a {dist}km {mode}. They burned approximately {calories} calories. Write a motivational 1-sentence summary."
    summary = llm.invoke(prompt).content
    return {"summary": summary}

workout_workflow = StateGraph(WorkoutState)
workout_workflow.add_node("calculate", workout_calc_node)
workout_workflow.add_node("summarize", workout_summary_node)
workout_workflow.set_entry_point("calculate")
workout_workflow.add_edge("calculate", "summarize")
workout_workflow.add_edge("summarize", END)
workout_app = workout_workflow.compile()
