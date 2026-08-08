from agent import track_app, workout_app
import sys

# Ensure UTF-8 output for emojis in console
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def test_track_agent():
    print("\n--- TESTING TRACK AGENT ---")
    initial_state = {
        "summary": "I want to go for a 3km run starting and ending at Central Park. My height is 180cm and weight is 75kg.",
        "waypoints": [],
        "coins": [],
        "actual_distance": 0,
        "estimated_calories": 0,
        "num_coins": 0,
        "total_score": 0,
        "height": 0, # Will be set by parser
        "weight": 0  # Will be set by parser
    }
    
    print("Generating your track and calculating workout metrics...")
    result = track_app.invoke(initial_state)
    print(f"Summary: {result['summary']}")
    print(f"Distance: {result['actual_distance']} km")
    print(f"Estimated Calories: {result['estimated_calories']:.1f} kcal")
    print(f"Coins: {result['num_coins']}")

def test_workout_agent():
    print("\n--- TESTING WORKOUT AGENT ---")
    initial_state = {
        "height": 180.0,
        "weight": 75.0,
        "distance_crossed": 5.0,
        "mode": "running",
        "summary": ""
    }
    
    print("Calculating post-workout calories...")
    result = workout_app.invoke(initial_state)
    print(f"Summary: {result['summary']}")
    print(f"Calories Burned: {result['calories_burned']:.2f} kcal")
    print(f"Duration Estimate: {result['duration_hours']:.2f} hours")

if __name__ == "__main__":
    test_track_agent()
    # test_workout_agent()
