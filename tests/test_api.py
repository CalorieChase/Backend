import requests


def main() -> None:
    url = "http://localhost:8000/generate-route"
    payload = {
        "startingLocation": "37.7749,-122.4194",
        "weightKg": 70,
        "goalType": "distance",
        "goalValue": 3.0,
        "routeType": "AUTO",
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Status: {response.status_code}")
        print(response.json())
    except Exception as exc:
        print(f"Connection error: {exc}")


if __name__ == "__main__":
    main()
