from api_config import BASE_URL, DB, get_json
import json, pathlib, duckdb

INDEX_DATA = pathlib.Path("data/index");
INDEX_DATA.mkdir(parents=True, exist_ok=True)

# IndexHealthAdvice bulk endpoint returns error 400, this function fetches per-index and reassembles the same table
def fetch_index_advice():
    rows = []
    for i in range(1, 11):
        payload = get_json(f"{BASE_URL}/Information/IndexHealthAdvice/AirQualityIndex={i}/Json")
        if payload:
            rows.append(payload)
    return rows

# flattened for transform.sql
def load_advice(payloads):
    out = []
    seen = set()

    for p in payloads:
        rec = p["AirQualityIndexHealthAdvice"]["AirQualityBanding"]
        band = rec["@AirQualityBand"]
        if band in seen:
            continue
        seen.add(band)

        advice = {a["@Population"]: a["@Advice"] for a in rec["HealthAdvice"]}
        out.append({
            "band": rec["@AirQualityBand"],
            "lower_index": int(rec["@LowerAirQualityIndex"]),
            "upper_index": int(rec["@UpperAirQualityIndex"]),
            "advice_general": advice.get("General population"),
            "advice_at_risk": advice.get("At-risk individuals"),
        })
    return out

def run():
    #conn = duckdb.connect(DB)
    payloads = fetch_index_advice()
    flat_advice = load_advice(payloads)

    with open(f"{INDEX_DATA}/health_advice.json", "w", encoding="utf-8") as f:
        json.dump(flat_advice, f, indent=1)
    print(f"Saved index health advice to {INDEX_DATA}/health_advice.json")

if __name__ == "__main__":
    run()