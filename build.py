import duckdb, pathlib

conn = duckdb.connect("feed.db")
with open("transform.sql", encoding="utf-8") as f:
    conn.execute(f.read())
    pathlib.Path("exports").mkdir(exist_ok=True)
    conn.execute("COPY site_map TO 'exports/site_map.csv' (HEADER, DELIMITER ',')")
conn.close()
print("Created feed.db from transform.sql")