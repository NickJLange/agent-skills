---
name: car_tracker
description: Publishes a daily bulletin of new arrivals and cheapest listings for specified vehicle trims on the market, tracking seen units in a state file.
version: 1.0.0
author: Antigravity Agent
license: MIT
metadata:
  hermes:
    tags: [monitoring, tracking, daily-bulletin, visor-api, auto-pricing]
---

# Daily Car Tracker Skill

This skill tracks and publishes a daily bulletin of new arrivals and cheapest active listings for your monitored vehicle trims. It compares fresh API listings against a local database of already-seen VINs (`data/seen_listings.json`) to identify brand-new inventory alerts as they hit the market.

## Setup & Credentials

Configure the following environment variables or add them to your `.env` file:
*   `VISOR.VIN_API_KEY` (or `VISOR_API_KEY`): Required. Bearer token to fetch live listings.

## Target Config

The tracker monitors target trims specified in `data/tracked_trims.json`. If this file is missing, it defaults to monitoring target vehicles configured in `vehicle_profiles.py`.

## How to Run

Execute the tool via the project's virtualenv Python interpreter:

```bash
python research/car_tracker/scripts/publish_deals.py
```
