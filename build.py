import duckdb

conn = duckdb.connect("feed.db")
with open("transform.sql", encoding="utf-8") as f:
    conn.execute(f.read())
conn.close()
print("Created feed.db from transform.sql")