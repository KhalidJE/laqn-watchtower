# London Air Quality Network Watchtower
Reliability monitoring for the London Air Quality Network feed. Tracks sensor liveness, data completeness, and data quality so a support engineer is able to detect problems before their clients do.

## What I Built & Who For
This pipeline exists to serve a support engineer at an environmental-data company whose product is an air quality feed. The data-as-a-service company provides the LAQN data as a cleaned, reliable feed to paying clients, so it's important that they maintain sensor uptime, otherwise they risk losing clients' trust. Clients include property developers tracking site compliance, logistics firms routing around pollution, etc.

Currently, when a sensor goes down, the assigned support engineer is most likely to find out from an upset client. The pipeline is used to create a dashboard tool that shows feed health, including liveness of sensors, completeness of data, and how normal readings are. This way, the support engineer can complete planned maintenance to keep the sensors healthy as well as undertake reactive work as soon as a real issue crops up. The engineer could also make clients aware of the problem as it happens so they're not left in the dark, improving rapport and building trust.

It makes use of both the data to measure how normal it is (e.g. is a particular pollutant not changing levels? Is it at a logically impossible level?), and the presence of data to determine the state of sensors (are they reporting on time? Are they showing gaps?).

The LAQN data is not clean or consistent. A data vendor reselling it can't promise clients reliability so this tool exists to help the firm patch up its gaps, uneven ratification lag and dead channels. It makes these problems visible to the support engineer before a client runs into them. The messiness of the data makes this tool incredibly valuable.

## The Data
The data used in this pipeline is managed by the Environmental Research Group of Imperial College London, and is sourced from the London Air Quality Network API. It uses fixed sensors at several locations scattered across different boroughs in London. The gases/pollutants it tracks include Nitrogen Dioxide (NO<sub>2</sub>), Ozone (O<sub>3</sub>), fine particulate matter (PM<sub>10</sub> and PM<sub>2.5</sub>), and more.

As the pipeline aims to continuously collect data over time, duplication is explicitly avoided. Data is also not overwritten due to the use case of this pipeline; if there was an issue with a sensor and it output illogical results (such as a large spike or a flatline), the data from that sensor may later be rectified for the sake of keeping the data clean. If this happens and the original data is overwritten, the support engineer would likely lose critical information linked to what exactly happened to that sensor on that specific date as all they'll see is a gap in the information (for example, a sensor previously reporting absurd numbers can be noted as the sensor spiking, but a gap could mistakenly indicate that the sensor was down instead). This harms their ability to establish patterns and make judgements on what work needs to be done to prevent future sensor issues or downtime.

A 48-hour lookback is also used, counting back from the last watermark. Monitoring stations don't always sync in real-time so late data arrivals need to be accounted for. If data is uploaded hours later, there's a high risk of the wider dataset having gaps. If a snapshot is initially excluded, it can be added later, but once a snapshot is in the database, it can't be overwritten. This avoids the issue highlighted previously while protecting against the unique problem of missing data.

Initial data pulls for a new site backfill for 90 days to provide comparison for sensor and data health information between this season and the previous one (e.g. are the sensors behaving more normally in the autumn compared to the hot days of summer?) and once again allows the support engineer to find patterns in data reliability. The first fetch brought in 599,240 readings (from 29/07/26 to 28/10/26) and 72 responsive sites (sites that have sent data). The 90 days of backfill are chunked to avoid pulling an entire 90 days worth of hourly data for each site; instead, each site provides 14 days of data at a time, with 60 seconds given before timeout and the ability to retry if a fetch initially fails. Due to the nature of the pipeline, any missing data can be added on retries or future attempts without overwriting pre-existing data. Data is saved in .json files that each hold a max of 14 days worth of data.

### Additional Notes
Data flags:
- No Data -> null reading
- Impossible Negative -> a value that is below 0
- Impossible High -> a value above 2000 (an absurd number)
- Extreme -> a reading matched to the DAQI threshold in the Very High band

Flatline runs are counted as 8 consecutive observations, rather than 8 uninterrupted hours. Since the data isn't currently fetched hourly, the flatline instead looks at the first instance of this repeated value and the most recent to determine a start and end date. Null values don't interrupt this since they're no longer added to the table, meaning if a run is detected, that means that every time that sensor has reported a value, it has been the same as the last 8+ times.

All tables:
- readings -> initial data returned by the API
- sites -> all site information
- site_species -> all species in each given site
- index_health_advice -> health advice from IndexHealthAdvice endpoint (not currently in use)
- daqi_thresholds -> information brought in from the seed file in data/index
- reading_flags -> any readings that are flagged as concerning or impossible
- site_health -> stores data completeness per-site
- feed_status -> shows sensor liveness by showing which channels are providing data on time
- flatline_runs -> holds information regarding channels that return the same value consecutively
- site_map -> shows liveness and completeness of data per-site, exported to a map in Tableau
- site_validity -> for a tooltip showing suspect readings

## How It Works
Initial data was pulled from the following endpoints and fed into a 'readings' table:
- /Information/MonitoringSiteSpecies/GroupName=London/Json - for the site/species monitoring information
- /Data/Site/SiteCode={SiteCode}/StartDate={start}/EndDate={end}/Json - for information on all London sites

The 'readings' table is created once if it doesn't exist and uses site, species and measurement time combinations as its primary key. Raw API responses are saved to data/raw. Data from the monitoring site catalogue is turned into two lists: site details and pollutants (species) measured at each site. These two lists are saved as .json files in data/catalogue. Closed sites are kept in the catalogue but aren't included in the database.

Health advice data was pulled from the following endpoint:
- /Information/IndexHealthAdvice/AirQualityIndex={i}/Json

It fetches information for index levels 1 - 10. During development, the bulk endpoint was returning a HTTP 400 error so this function makes per-index requests. It uses a set to get rid of duplicate bands in the output. This data is saved to data/index/health_advice.json. Alongside this data, a seed file is also placed in data/index: daqi_thresholds.csv. This holds consistent information regarding what low, moderate, high and very high values look like for supported pollutants (does not support all of the LAQN's measured pollutants), according to the Data Air Quality Index (uses the 1-10 index scale) provided by the DEFRA (see attributions). The health advice is fetched and loaded into the database but is no longer planned to be used for the current version of the dashboard.

The final dashboard makes use of as much data as possible to paint a picture of what's happening behind the scenes. This dashboard shows two maps: one for general feed status per site (colour coded based on worst status (i.e. if a site has 3 live channels and 1 down, it will still show red)), and one for status per species (i.e. individual sensor status). It also a shows a chart for data completeness per site (presence of all expected data), as well as a table for flagged readings. Tooltips provide all necessary data for identifying faulty sensors or issues with data consistency, allowing the engineer to know which sites need to be worked on and prioritised.

## How To Run It
Requires Python 3.11+. API Credentials are not needed for any fetches.

Install the Python dependencies from the project root:
```pip install -r requirements.txt```

1. Run 'extract.py' from the project root to pull new readings.
2. Optional: run 'extract_index.py' to pull index health advice data. This is already saved to data/index so this step is optional.
3. Run 'build.py' from the project root to build the model ('feed.db'). This also exports 'site_map.csv' and 'feed_status.csv'.

### Viewing the Dashboard
The pipeline outputs site_map.csv, feed_status.csv, and flagged_readings.csv to be read by the Tableau workbook (support_dashboard.twb). Open it in Tableau Public/Desktop and navigate to Data > Refresh to see the latest data after completing steps 1 and 3. A packaged .twbx is included so it opens with the data bundled if needed.

## What I Would Do Next
I would add a 'retrieved_at' field for data being fed into the pipeline to compare provisional and ratified data; since data can be changed after its initial upload, it would be a good idea to have the original value as well as the new value. For instance, if a reading initially shows 1000 then drops down to 10 a few days later, the table could hold information that would show the engineer when exactly the data was changed and what it was changed to.

Another piece of future work is to pull data from a 2nd API to validate the accuracy of the data coming from LAQN. Since this is a reliability tool and the firm hypothetically prides itself on providing clean, reliable data to paying customers, it would be a big upgrade to the integrity of their product. LAQN also seems to struggle with providing accurate data in a timely manner so this would be a good way to counteract that and even add placeholder data when none is available from LAQN, thus keeping the firm's clients always provided for.

## Where AI Helped
- Initial resources/links for learning
- Debugging of extract.py and transform.sql
- Troubleshooting issues with IndexHealthAdvice endpoint
- Switching to chunking for data backfill
- SQL queries for troubleshooting
- Implementing flatline runs into the map filter

### Attributions
Air quality information is obtained from the Environmental Research Group of Imperial College London, using data from the London Air Quality Network (https://www.londonair.org.uk), and is licensed under the Open Government Licence Version 2.0.

DAQI threshold information is sourced from the Department for Environment, Food and Rural Affairs (DEFRA), approved by the Committee on the Medical Effects of Air Pollutants (COMEAP). Licenced under the Open Government Licence.

### Note on Difference Between Raw Data Files
- Watermarks are created using a SELECT statement that returns the latest inserted reading for a site.
- These watermarks are used to decide when the latest data added was, and then check a further 48 hours prior (the lookback). In other words, the lookback only counts from the watermark, not from the current time. For this reason, earlier files may overlap their readings, but this data is not duplicated when inserted into the database.
- If data hasn't been inserted for a couple of days, a file can end up spanning a couple of days (further than the 48 hours), until new, none-null values are found and inserted into the database to update the watermark for a site.
- Originally (pre-Oct 29th), the load() function in extract.py converted Null values to Python None and inserted the rows into the readings table regardless. This meant that empty readings were inserted up until Oct 29th, leading to watermarks pointing at this date as the last date of data entry, despite data not having been entered.
- This has been resolved since but earlier files were not deleted or replaced in the interest of preserving raw data and not hiding any part of the development process.