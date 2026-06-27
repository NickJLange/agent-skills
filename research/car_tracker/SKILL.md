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

Option verification (Panoramic Moonroof, 360-degree camera, premium sound systems, seating configurations) is run dynamically on listings to ensure reported deals meet your exact package requirements.

## Setup & Credentials

Configure the following environment variables or add them to your `.env` file:
*   `VISOR.VIN_API_KEY` (or `VISOR_API_KEY`): Required. Bearer token to fetch live listings.

## Target Config

The script checks for configurations in the following order:
1.  **Vehicle Profiles Python Module**: Dynamically imports from `vehicle_profiles.py` if present in the working directory (loads profiles specified by `ACTIVE_SEARCH_PROFILE_KEYS`).
2.  **Custom JSON Config**: Reads target trims and required features from `data/tracked_trims.json` if present.
3.  **Built-in Fallback Targets**: Defaults to searching for option-equipped Toyota Grand Highlander (Hybrid Limited and Hybrid Nightshade), Chrysler Pacifica Pinnacle AWD, and Lexus TX 350 AWD.

### Custom JSON Config Example (`data/tracked_trims.json`)
```json
[
  {
    "key": "grand_highlander_hybrid_limited_awd",
    "make": "Toyota",
    "model": "Grand Highlander",
    "trim": "Hybrid Limited AWD",
    "year": 2026,
    "sample_vin": "5TDACAB53TS25G407",
    "target_otd_price": 58450.85,
    "must_haves": [
      "Hybrid powertrain",
      "AWD",
      "Limited trim",
      "Panoramic Moonroof",
      "Panoramic View Monitor (360 Cam)",
      "7-Passenger Seating (Captain's Chairs)",
      "Available or inbound unit that is not already sold/reserved"
    ]
  }
]
```

## How to Run

Execute the tool via the project's virtualenv Python interpreter:

```bash
python research/car_tracker/scripts/publish_deals.py
```
