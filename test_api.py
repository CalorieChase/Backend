import requests
import json
import sys

# Ensure UTF-8 output for emojis in console
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

url = "http://localhost:8000/generate-route"
payload = {
    "starting_point": "Central Park",
    "ending_point": "Central Park",
    "activity_type": "run",
    "distance": 3.0,
    "prompt": "I want a quick run around central park."
}

try:
    print(f"Testing API at {url}...")
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("Success! Response received.")
        data = response.json()
        print(f"Summary: {data['summary']}")
        print(f"Distance: {data['est_distance']} km")
        print(f"Calories: {data['est_cal']} kcal")
        
        # Show sample waypoints
        route = data.get('route', [])
        print(f"\nRoute points: {len(route)}")
        if route:
            print(f"First 2 points: {route[:2]}")
            print(f"Last point: {route[-1]}")
            
        # Show sample coins
        coins = data.get('coins', [])
        print(f"Coins count: {len(coins)}")
        if coins:
            print(f"Sample coin locations: {[{ 'lat': c['lat'], 'lng': c['lng'], 'val': c['val'] if 'val' in c else c.get('value') } for c in coins[:3]]}")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Connection error: {e}")
