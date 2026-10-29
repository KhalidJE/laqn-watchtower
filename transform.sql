CREATE OR REPLACE TABLE sites AS
SELECT * FROM read_json('data/catalogue/sites.json');

CREATE OR REPLACE TABLE site_species AS
SELECT * FROM read_json('data/catalogue/site_species.json');

CREATE OR REPLACE TABLE index_health_advice AS
SELECT * FROM read_json('data/index/health_advice.json');

CREATE OR REPLACE TABLE daqi_thresholds AS
SELECT * FROM read_csv('data/index/daqi_thresholds.csv', header=true,
columns={
    'species_code':'VARCHAR',
    'index_level':'INTEGER',
    'band':'VARCHAR',
    'lower':'INTEGER',
    'upper':'INTEGER'
    });

-- table for things that would be flagged in readings (e.g. lack of data, values that are too high, etc.)
CREATE OR REPLACE TABLE reading_flags AS
SELECT r.site_code, r.species_code, r.measured_at, r.value, dt.index_level, dt.band,
CASE
    WHEN r.value IS NULL THEN 'no_data'
    WHEN r.value < 0 THEN 'impossible_negative'
    WHEN r.value > 2000 THEN 'impossible_high'
    WHEN dt.band = 'Very High' THEN 'extreme'
    ELSE 'ok'
END AS flag
FROM readings r
LEFT JOIN daqi_thresholds dt ON dt.species_code = r.species_code
AND round(r.value) >= dt.lower
AND (dt.upper IS NULL OR round(r.value) <= dt.upper);

-- table for data completeness per-site
CREATE OR REPLACE TABLE site_health AS
WITH expected AS (
    SELECT site_code, species_code FROM site_species
),
actual AS (
    SELECT site_code, species_code, count(value) AS readings_got, max(measured_at) AS last_reading
    FROM readings
    WHERE measured_at >= now() - INTERVAL 7 day
    GROUP BY 1, 2
)
SELECT
    e.site_code, e.species_code,
    coalesce(a.readings_got, 0) AS readings_got,
    168 AS readings_expected,
    round(100.0 * coalesce(a.readings_got, 0) / 168, 1) AS completeness_percent,
    a.last_reading
FROM expected e
LEFT JOIN actual a USING (site_code, species_code);

-- table showing whether data is being fed in or not per-site
CREATE OR REPLACE TABLE feed_status AS
SELECT
    ss.site_code, ss.species_code,
    max(r.measured_at) AS last_reading,
    date_diff('hour', max(r.measured_at), now()) AS hours_since,
    CASE
        WHEN max(r.measured_at) IS NULL THEN 'silent'
        WHEN date_diff('hour', max(r.measured_at), now()) <= 2 THEN 'live'
        WHEN date_diff('hour', max(r.measured_at), now()) <= 24 THEN 'late'
        ELSE 'down'
    END AS status
FROM site_species ss
LEFT JOIN readings r USING (site_code, species_code)
GROUP BY 1, 2;

-- table showing when a flatline occurs - data remaining stale for 8 hours counts as a flatline
CREATE OR REPLACE TABLE flatline_runs AS
WITH ordered AS (
    SELECT site_code, species_code, measured_at, value,
        CASE
            WHEN value is DISTINCT FROM lag(value) OVER (PARTITION BY site_code, species_code ORDER BY measured_at) THEN 1 ELSE 0 END AS changed
    FROM readings
    WHERE value IS NOT NULL
),
grouped AS (
    SELECT *,
        sum(changed) OVER (PARTITION BY site_code, species_code ORDER BY measured_at) AS run_id
    FROM ordered
)
SELECT site_code, species_code, VALUE AS stuck_value,
    min(measured_at) AS run_start,
    max(measured_at) AS run_end,
    count(*) AS run_length
FROM grouped
GROUP BY site_code, species_code, value, run_id
HAVING count(*) >= 8; -- set to 8 hours