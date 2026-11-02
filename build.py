import filecmp
import pathlib

import duckdb

RAW_DATA = pathlib.Path("data/raw")
ARCHIVED_DATA = pathlib.Path("data/archived")


def archive_raw_files(raw_files):
    if not raw_files:
        return

    ARCHIVED_DATA.mkdir(parents=True, exist_ok=True)
    for raw_file in raw_files:
        archived_file = ARCHIVED_DATA / raw_file.name
        if archived_file.exists():
            if filecmp.cmp(raw_file, archived_file, shallow=False):
                raw_file.unlink()
                continue

            suffix = 1
            while archived_file.exists():
                archived_file = ARCHIVED_DATA / f"{raw_file.stem}_{suffix}{raw_file.suffix}"
                suffix += 1

        raw_file.replace(archived_file)


def run():
    conn = duckdb.connect("feed.db")
    raw_files = sorted(RAW_DATA.glob("*.json"))

    bronze_sql = pathlib.Path("bronze_to_silver.sql").read_text(encoding="utf-8")
    ingest_marker = "-- ingest raw files"
    marker_start = bronze_sql.casefold().find(ingest_marker)
    if marker_start == -1:
        raise ValueError(
            f"Missing {ingest_marker!r} section in bronze_to_silver.sql"
        )

    setup_sql = bronze_sql[:marker_start]
    insert_and_transform_sql = bronze_sql[marker_start + len(ingest_marker):]
    ingest_sql, separator, transform_sql = insert_and_transform_sql.partition(";")
    if not separator:
        raise ValueError("Raw-file INSERT in bronze_to_silver.sql must end with ';'")
    ingest_sql = f"{ingest_sql};"

    conn.execute("BEGIN TRANSACTION")
    try:
        conn.execute(setup_sql)
        before_count = conn.execute(
            "SELECT count(*) FROM readings"
        ).fetchone()[0]
        for raw_file in raw_files:
            conn.execute(ingest_sql, [str(raw_file)])
        if transform_sql.strip():
            conn.execute(transform_sql)
        after_count = conn.execute(
            "SELECT count(*) FROM readings"
        ).fetchone()[0]
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    new_readings = after_count - before_count

    with open("silver_to_gold.sql", encoding="utf-8") as f:
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

    archive_raw_files(raw_files)
    print("Created feed.db from bronze_to_silver.sql and silver_to_gold.sql")
    print(f"Inserted {new_readings} new readings")
    print("Created site_map.csv, feed_status.csv & flagged_readings.csv")


if __name__ == "__main__":
    run()