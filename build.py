import duckdb, pathlib

conn = duckdb.connect("feed.db")
with open("transform.sql", encoding="utf-8") as f:
    conn.execute(f.read())
    pathlib.Path("exports").mkdir(exist_ok=True)
    conn.execute("COPY site_map TO 'exports/site_map.csv' (HEADER, DELIMITER ',')")
    conn.execute("COPY (SELECT f.*, s.site_name, s.latitude, s.longitude, s.site_type FROM feed_status f JOIN sites s USING(site_code)) TO 'exports/feed_status.csv' (HEADER)")
conn.close()
print("Created feed.db from transform.sql")
print("Created site_map.csv and feed_status.csv")