import requests, time

DB = "feed.db"

BASE_URL = "https://api.erg.ic.ac.uk/AirQuality"

# had issues with backfilled data timing out before saving, this function changes the timeout + adds retries
def get_json(url, timeout=(10, 60), retries=2):
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            return r.json() # removed BOM safeguards since they were unnecessary
        except requests.exceptions.RequestException:
            if attempt == retries:
                raise
            time.sleep(2 * (attempt + 1))