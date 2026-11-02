CREATE TABLE IF NOT EXISTS readings (
    site_code    VARCHAR,
    species_code VARCHAR,
    measured_at  TIMESTAMP,
    value        DOUBLE,
    PRIMARY KEY (site_code, species_code, measured_at)
);

-- ingest raw files
INSERT INTO readings (site_code, species_code, measured_at, value)
SELECT
    json_extract_string(raw.json, '$.AirQualityData."@SiteCode"'),
    json_extract_string(data.value, '$."@SpeciesCode"'),
    CAST(json_extract_string(data.value, '$."@MeasurementDateGMT"') AS TIMESTAMP),
    CAST(json_extract_string(data.value, '$."@Value"') AS DOUBLE)
FROM read_json_objects(?) AS raw,
LATERAL json_each(raw.json, '$.AirQualityData.Data') AS data
WHERE NULLIF(json_extract_string(data.value, '$."@Value"'), '') IS NOT NULL
ON CONFLICT (site_code, species_code, measured_at) DO UPDATE
SET value = excluded.value
WHERE readings.value IS NULL AND excluded.value IS NOT NULL;

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
    168 AS readings_expected, -- note 168 = hrs in 7 days
    round(100.0 * coalesce(a.readings_got, 0) / 168, 1) AS completeness_percent,
    a.last_reading
FROM expected e
LEFT JOIN actual a USING (site_code, species_code);

-- table showing when a flatline occurs - data remaining stale across 8+ pulls counts as a flatline
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
    count(*) AS run_length,
    CASE
        WHEN value <= 1 THEN 'low_or_resolution'
        ELSE 'suspect_stuck'
    END AS flatline_type
FROM grouped
GROUP BY site_code, species_code, value, run_id
HAVING count(*) >= 8; -- set to 8 hours