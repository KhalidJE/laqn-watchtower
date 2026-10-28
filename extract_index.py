from api_config import BASE_URL, get_json
import json, pathlib

INDEX_DATA = pathlib.Path("data/index");
INDEX_DATA.mkdir(parents=True, exist_ok=True)

# IndexHealthAdvice bulk endpoint returns error 400, this function fetches per-index and reassembles the same table
def fetch_index_advice():
    rows = []
    for i in range(1, 11):
        payload = get_json(f"{BASE_URL}/Information/IndexHealthAdvice/AirQualityIndex={i}/Json")
        rows.append(payload)
    return rows

def run():
    with open(f"{INDEX_DATA}/health_advice.json", "w", encoding="utf-8") as f:
        json.dump(fetch_index_advice(), f, indent=1)
    print(f"Saved index health advice to {INDEX_DATA}/health_advice.json")

if __name__ == "__main__":
    run()