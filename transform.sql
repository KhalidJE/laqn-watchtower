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