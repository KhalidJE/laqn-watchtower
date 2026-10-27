import requests, json, pathlib, datetime as dt
import duckdb

RAW_DATA = pathlib.Path("data/raw");
RAW_DATA.mkdir(parents=True, exist_ok=True)
DB = "feed.db"

BASE_URL = "https://api.erg.ic.ac.uk/AirQuality"

def fetch_window(site_code, start, end):
    url = f"{BASE_URL}/Data/Site/SiteCode={site_code}/StartDate={start}/EndDate={end}/Json"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return json.loads(r.content.decode("utf-8-sig"))

def save_raw(site_code, payload, start, end):
    path = RAW_DATA / f"{site_code}_{start}_{end}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path

def load(conn, site_code, payload):
    rows = []
    for entry in payload["AirQualityData"]["Data"]:
        measured_at = entry.get("@MeasurementDateGMT")
        actual_val = entry.get("@Value")
        if (actual_val is not None and actual_val != ""):
            value = float(actual_val)
        else:
            value = None
        species = entry.get("@SpeciesCode")
        rows.append((site_code, species, measured_at, value))

    conn.executemany(
        "INSERT INTO readings VALUES (?, ?, ?, ?) ON CONFLICT DO NOTHING", # prevents original data from being overwritten - makes the tool more diagnostic
        rows
    )
    fetched = len(rows)
    return fetched

def run():
    conn = duckdb.connect(DB)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS readings (
        site_code    VARCHAR,
        species_code VARCHAR,
        measured_at  TIMESTAMP,
        value        DOUBLE,
        PRIMARY KEY (site_code, species_code, measured_at)
    )
""")
    today = dt.date.today()
    watermark = conn.execute("SELECT max(measured_at) FROM readings").fetchone()[0]
    if watermark is None:
        start = today - dt.timedelta(days=90) #backfills by ~3 months on the first run so data from the previous season can be compared too
    else:
        start = watermark.date() - dt.timedelta(days=2)
    end = today + dt.timedelta(days=1)

    site = "HK6"

    before = conn.execute("SELECT count(*) FROM readings").fetchone()[0]
    payload = fetch_window(site, start, end)
    save_raw(site, payload, start, end)
    fetched = load(conn, site, payload)
    after = conn.execute("SELECT count(*) FROM readings").fetchone()[0]
    inserted = after - before

    print(f"{site} ~ window: {start} -> {end} ~ fetched {fetched} \n"
          f"inserted {inserted} new & skipped {fetched - inserted} duplicates")

if __name__ == "__main__":
    run()