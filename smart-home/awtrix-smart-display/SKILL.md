---
name: awtrix-smart-display
description: Submit custom notifications, animated Final Fantasy characters, static text, raw drawings, and power commands to physical Awtrix 3 smart displays. Also controls the continuous background animations.
version: 1.0.0
author: Hermes Agent 01
license: Apache-2.0
metadata:
  hermes:
    tags: [awtrix, smart-display, led-matrix, final-fantasy, notification, cron]
    required_commands: [python, awtrix]
---

# awtrix-smart-display

Integration and control CLI for Awtrix 3 smart display clocks. Exposes a unified `awtrix` CLI command to notify, post text/graphics, power cycle, or toggle background character animations.

## When to Use — natural-language → command

| User says… | Run |
|---|---|
| "Show Cecil walking on the kitchen clock with text 'Morning!'" | `awtrix notify kitchen "Morning!" --sprite cecil` |
| "Turn on the office clock display" | `awtrix power office on` |
| "Set the kitchen clock text to '90 F'" | `awtrix text kitchen "90 F" --name "temp"` |
| "Start the character walk animations background streamer" | `awtrix stream start` |
| "Stop the background character walk cycles" | `awtrix stream stop` |
| "Check if the background streamer is running" | `awtrix stream status` |

## Setup

**One-time by the human:**

1. Create the local configuration file at `~/.config/awtrix/config.json`. Populate it with the hostnames/aliases of your clocks and the path to the external Final Fantasy sprite assets directory.
   
   *Example:*
   ```json
   {
     "devices": {
       "kitchen": "awtrix-kitchen.local",
       "office": "awtrix-office.local"
     },
     "sprites_dir": "/path/to/external-sprites-directory",
     "default_text_color": "#00BCFF"
   }
   ```
   
2. Install the package locally:
   ```bash
   pip install -e /path/to/agent-skills/smart-home/awtrix-smart-display
   ```
   
3. If using the background character walk cycle animator streamer, configure the path to the `awtrix_animate.py` script by setting the `AWTRIX_ANIMATE_SCRIPT` environment variable:
   ```bash
   export AWTRIX_ANIMATE_SCRIPT="/path/to/mkulanzi/client/awtrix_animate.py"
   ```

## Agent invocation examples

```bash
# Push an animated greeting using a character
awtrix notify kitchen "HELLO NICK" --sprite locke --duration 12

# Push simple custom app text
awtrix text kitchen "ALERT!" --color "#FF0000" --name "alert_app"

# Remove a custom app to clear the screen
awtrix custom kitchen "{}" --name "alert_app"

# Start/Stop the background walk-cycle rotator streamer
awtrix stream start
awtrix stream stop
awtrix stream status
```

## Pitfalls & Best Practices

- **Logical Aliases:** Always refer to devices using the logical aliases defined in your configuration file (`kitchen`, `office`) instead of raw IP addresses.
- **Background Animator Conflict:** The background animation streamer runs continuously. When sending notifications via `awtrix notify`, they will run in a custom scene named `notify` that overrides other apps temporarily. If you want a static notification to persist, delete the `edge_scene` custom app or stop the streamer using `awtrix stream stop`.
- **Sprite Names:** Sprite resolution looks up names case-insensitively inside `sprites.json` in the external sprites directory (e.g. `rydia_child`, `cecil`, `terra`).
