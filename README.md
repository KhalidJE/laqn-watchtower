# London Air Quality Network Watchtower
Reliability monitoring for the London Air Quality Network feed. Tracks sensor liveness, data completeness, and data quality so a support engineer is able to detect problems before their clients do.

## What I Built & Who For
This pipeline exists to serve a support engineer at an environmental-data company whose product is an air quality feed. The data-as-a-service company provides the LAQN data as a cleaned, reliable feed to paying clients, so it's important that they maintain sensor uptime, otherwise they risk losing clients' trust. Clients include property developers tracking site compliance, logistics firms routing around pollution, etc.

Currently, when a sensor goes down, the assigned support engineer is most likely to find out from an upset client. The pipeline is used to create a tool that shows feed health, including liveness of sensors, completeness of data, and how normal readings are. This way, the support engineer can undertake reactive work before a real issue pops up, or even make clients aware of the problem as it happens so they're not left in the dark, improving rapport and building trust.

It makes use of both the data to measure how normal it is (e.g. is a particular pollutant not changing levels? Is it at a logically impossible level?), and the presence of data to determine the state of sensors (are they reporting on time? Are they showing gaps?).

## The Data
The data used in this pipeline is managed by the Environmental Research Group of Imperial College London, and is sourced from the London Air Quality Network API. It uses fixed sensors at several locations scattered across different boroughs in London. The gases/pollutants it tracks include Nitrogen Dioxide (NO<sub>2</sub>), Ozone (O<sub>3</sub>), and fine particulate matter (PM<sub>10</sub> and PM<sub>2.5</sub>).

As the pipeline aims to continuously collect data over time, duplication is explicitly avoided. Data is also not overwritten due to the use case of this pipeline; if there was an issue with a sensor and it output illogical results (such as a large spike or a flatline), the data from that sensor may later be rectified for the sake of keeping the data clean. If this happens and the original data is overwritten, the support engineer would likely lose critical information linked to what exactly happened to that sensor on that specific date as all they'll see is a gap in the information (for example, a sensor previously reporting absurd numbers can be noted as the sensor spiking, but a gap could mistakenly indicate that the sensor was down instead). This harms their ability to establish patterns and make judgements on what work needs to be done to prevent future sensor issues or downtime.

A 48-hour lookback is also used. Monitoring stations don't always sync in real-time so late data arrivals need to be accounted for. If data is uploaded hours later, there's a high risk of the wider dataset having gaps. If a snapshot is initially excluded, it can be added later, but once a snapshot is in the database, it can't be overwritten. This avoids the issue highlighted previously while protecting against the unique problem of missing data.

## How It Works

## How To Run It

## What I Would Do Next

## Where AI Helped

### Attribution
This information is obtained from the Environmental Research Group of Imperial College London, using data from the London Air Quality Network (https://www.londonair.org.uk), and is licensed under the Open Government Licence Version 2.0.