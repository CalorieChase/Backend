import requests


def main() -> None:
    url = "http://localhost:8000/generate-route"
    payload = {
        "starting_point": "Central Park",
        "ending_point": "Central Park",
        "activity_type": "run",
        "distance": 3.0,
        "prompt": "I want a quick run around central park.",
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

            route = data.get("route", [])
            print(f"\nRoute points: {len(route)}")
            if route:
                print(f"First 2 points: {route[:2]}")
                print(f"Last point: {route[-1]}")

            coins = data.get("coins", [])
            print(f"Coins count: {len(coins)}")
            if coins:
                sample = [
                    {
                        "lat": coin["lat"],
                        "lng": coin["lng"],
                        "val": coin["val"] if "val" in coin else coin.get("value"),
                    }
                    for coin in coins[:3]
                ]
                print(f"Sample coin locations: {sample}")
        else:
            print(f"Error: {response.text}")
    except Exception as exc:
        print(f"Connection error: {exc}")


if __name__ == "__main__":
    main()
