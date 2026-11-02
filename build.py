import duckdb, pathlib

conn = duckdb.connect("feed.db")
with open("transform.sql", encoding="utf-8") as f:
    conn.execute(f.read())
    pathlib.Path("exports").mkdir(exist_ok=True)
    conn.execute("COPY (SELECT m.*, coalesce(v.suspect_readings, 0) AS suspect_readings, coalesce(v.total_readings, 0) AS total_readings FROM site_map m LEFT JOIN site_validity v USING (site_code)) TO 'exports/site_map.csv' (HEADER, DELIMITER ',')")
    conn.execute("COPY (SELECT f.*, s.site_name, s.latitude, s.longitude, s.site_type FROM feed_status f JOIN sites s USING(site_code)) TO 'exports/feed_status.csv' (HEADER)")
    conn.execute("""
        COPY (
            SELECT
                rf.site_code,
                s.site_name,
                rf.species_code,
                rf.measured_at,
                rf.value,
                rf.flag,
                rf.index_level,
                rf.band
            FROM reading_flags rf
            LEFT JOIN sites s USING (site_code)
            WHERE rf.flag <> 'ok'
              AND rf.measured_at >= (
                  SELECT max(measured_at) FROM readings
              ) - INTERVAL 7 DAY
            ORDER BY rf.measured_at DESC
        )
        TO 'exports/flagged_readings.csv' (HEADER, DELIMITER ',')
    """)
print("Created feed.db from transform.sql")
print("Created site_map.csv & feed_status.csv")