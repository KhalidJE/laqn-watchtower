from api_config import BASE_URL, DB, get_json
import json, pathlib, time, datetime as dt
import duckdb

RAW_DATA = pathlib.Path("data/raw");
RAW_DATA.mkdir(parents=True, exist_ok=True)

# per-site watermarks instead of global so each site's window starts from its own last reading
def site_watermarks(conn):
    rows = conn.execute(
        "SELECT site_code, max(measured_at) FROM readings GROUP BY site_code"
    ).fetchall()
    return {code: ts for code, ts in rows}

def fetch_sites():
    url = f"{BASE_URL}/Information/MonitoringSiteSpecies/GroupName=London/Json"
    data = get_json(url)
    return data["Sites"]["Site"]

def flatten_sites(sites):
    site_rows, ss_rows = [], []
    for s in sites:
        code = s["@SiteCode"]
        site_rows.append({
            "site_code": code,
            "site_name": s.get("@SiteName"),
            "site_type": s.get("@SiteType"),
            "latitude": float(s["@Latitude"]) if s.get("@Latitude") else None,
            "longitude": float(s["@Longitude"]) if s.get("@Longitude") else None,
            "local_authority": s.get("@LocalAuthorityName"),
            "date_opened": s.get("@DateOpened") or None,
            "date_closed": s.get("@DateClosed") or None
        })
        species = s.get("Species", [])
        if isinstance(species, dict):
            species = [species]
        for sp in species:
            ss_rows.append({"site_code": code, "species_code": sp["@SpeciesCode"]})
    return site_rows, ss_rows

def fetch_window(site_code, start, end):
    url = f"{BASE_URL}/Data/Site/SiteCode={site_code}/StartDate={start}/EndDate={end}/Json"
    return get_json(url)

def save_raw(site_code, payload, start, end):
    path = RAW_DATA / f"{site_code}_{start}_{end}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path

def load(conn, site_code, payload):
    if not payload:
        return 0, 0
    data = payload.get("AirQualityData", {}).get("Data")
    if not data:
        return 0, 0
    rows = []
    for entry in data:
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

def chunks(start, end, days=14):
    cursor = start
    while cursor < end:
        next = min(cursor + dt.timedelta(days=days), end)
        yield cursor, next
        cursor = next

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

    sites = fetch_sites()

    CATALOGUE = pathlib.Path("data/catalogue"); CATALOGUE.mkdir(parents=True, exist_ok=True)
    site_rows, ss_rows = flatten_sites(sites)
    (CATALOGUE / "sites.json").write_text(json.dumps(site_rows, indent=1), encoding="utf-8")
    (CATALOGUE / "site_species.json").write_text(json.dumps(ss_rows, indent=1), encoding="utf-8")

    sites = [s for s in sites if not s.get("@DateClosed")] # some sites are decommissioned so should be skipped
    
    today = dt.date.today()
    end = today + dt.timedelta(days=1)
    marks = site_watermarks(conn)
    before_count = conn.execute("SELECT count(*) FROM readings").fetchone()[0]

    for s in sites:
        s_code = s["@SiteCode"]
        wm = marks.get(s_code)
        start = (wm.date() - dt.timedelta(days=2)) if wm else (today - dt.timedelta(days=90))
        for chunk_start, chunk_end in chunks(start, end):
            try:
                payload = fetch_window(s_code, chunk_start, chunk_end)
                save_raw(s_code, payload, chunk_start, chunk_end)
                load(conn, s_code, payload)
            except Exception as e:
                print(f"{s_code} {chunk_start}->{chunk_end} skipped: {type(e).__name__}: {e}") # gives an error if one site is faulty but run doesn't get aborted
            time.sleep(0.3) # delay of 0.3s between calls

    after_count = conn.execute("SELECT count(*) FROM readings").fetchone()[0]
    print(f"{len(sites)} sites ~ inserted {after_count - before_count} new readings")

if __name__ == "__main__":
    run()