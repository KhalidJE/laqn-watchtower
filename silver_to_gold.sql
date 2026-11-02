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

-- table showing whether data is being fed in or not per-site
CREATE OR REPLACE TABLE feed_status AS
SELECT
    ss.site_code, ss.species_code,
    max(r.measured_at) AS last_reading,
    date_diff('hour', max(r.measured_at), (SELECT max(measured_at) FROM readings)) AS hours_since,
    CASE
        WHEN max(r.measured_at) IS NULL THEN 'silent'
        WHEN date_diff('hour', max(r.measured_at), (SELECT max(measured_at) FROM readings)) <= 4 THEN 'live'
        WHEN date_diff('hour', max(r.measured_at), (SELECT max(measured_at) FROM readings)) <= 24 THEN 'late'
        ELSE 'down'
    END AS status
FROM site_species ss
LEFT JOIN readings r USING (site_code, species_code)
GROUP BY 1, 2;

-- for liveness and completeness per site, gets exported for Tableau map
CREATE OR REPLACE TABLE site_map AS
WITH fs AS (
    SELECT site_code,
    count(*) AS channels,
    count(*) FILTER (WHERE status = 'live') AS live_channels,
    count(*) FILTER (WHERE status = 'late') AS late_channels,
    count(*) FILTER (WHERE status IN ('silent', 'down')) AS down_channels,
    max(last_reading) AS last_reading
    FROM feed_status GROUP BY site_code
),
sh AS (
    SELECT site_code, round(avg(completeness_percent), 1) AS avg_completeness
    FROM site_health GROUP BY site_code
),
fr AS ( -- adds suspected flatline runs to the export so they can be shown as a tooltip on the dashboard
    SELECT site_code,
        count(*) FILTER (
            WHERE flatline_type = 'suspect_stuck'
        ) AS suspect_flatline_runs
    FROM flatline_runs
    WHERE run_end >= (
        SELECT max(measured_at) FROM readings
    ) - INTERVAL 7 DAY
    GROUP BY site_code
)
SELECT s.site_code, s.site_name, s.site_type, s.local_authority, s.latitude, s.longitude,
    fs.channels, fs.live_channels, fs.late_channels, fs.down_channels, fs.last_reading, sh.avg_completeness,
    coalesce(fr.suspect_flatline_runs, 0) AS suspect_flatline_runs,
    CASE
        WHEN fs.down_channels > 0 THEN 'Down'
        WHEN fs.late_channels > 0 THEN 'Late'
        WHEN fs.live_channels > 0 THEN 'Live'
        ELSE 'Unknown'
    END AS status
FROM sites s
LEFT JOIN fs USING (site_code)
LEFT JOIN sh USING (site_code)
LEFT JOIN fr USING (site_code)
WHERE s.date_closed IS NULL AND s.latitude IS NOT NULL;

-- for data validity per-site, gets exported to Tableau map as a tooltip
CREATE OR REPLACE TABLE site_validity AS
SELECT site_code,
    count(*) FILTER (WHERE flag <> 'ok') AS suspect_readings,
    count(*) AS total_readings
FROM reading_flags
WHERE measured_at >= (SELECT max(measured_at) FROM readings) - INTERVAL 7 DAY
GROUP BY site_code;
