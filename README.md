# London Air Quality Network Watchtower
Reliability monitoring for the London Air Quality Network feed. Tracks sensor liveness, data completeness, and data quality so a support engineer is able to detect problems before their clients do.

## What I Built & Who For
This pipeline exists to serve a support engineer at an environmental-data company whose product is an air quality feed. The data-as-a-service company provides the LAQN data as a cleaned, reliable feed to paying clients, so it's important that they maintain sensor uptime, otherwise they risk losing clients' trust. Clients include property developers tracking site compliance, logistics firms routing around pollution, etc.

Currently, when a sensor goes down, the assigned support engineer is most likely to find out from an upset client. The pipeline is used to create a tool that shows feed health, including liveness of sensors, completeness of data, and how normal readings are. This way, the support engineer can undertake reactive work before a real issue pops up, or even make clients aware of the problem as it happens so they're not left in the dark, improving rapport and building trust.

It makes use of both the data to measure how normal it is (e.g. is a particular pollutant not changing levels? Is it at a logically impossible level?), and the presence of data to determine the state of sensors (are they reporting on time? Are they showing gaps?).

## The Data


## How It Works

## How To Run It

## What I Would Do Next

## Where AI Helped

### Attribution
This information is obtained from the Environmental Research Group of Imperial College London, using data from the London Air Quality Network (https://www.londonair.org.uk), and is licensed under the Open Government Licence Version 2.0.