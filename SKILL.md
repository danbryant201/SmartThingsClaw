---
name: smartthings
description: >
  Monitor Samsung SmartThings devices. List connected devices with their
  components and capabilities, and retrieve live status. Future versions will
  add device control, scenes, automations, and event subscriptions.
version: 1.0.0
metadata:
  openclaw:
    env:
      SMARTTHINGS_TOKEN: "smartthings_pat"
    bins: ["python3"]
    primaryEnv: SMARTTHINGS_TOKEN
---

# SmartThings Skill

## Overview

This skill connects to the Samsung SmartThings cloud API using a Personal
Access Token (PAT). It lets you:

- List every device on the account with its components and capabilities
- Retrieve the current status of any device or all devices at once

Scripts live in `scripts/` relative to this skill and are invoked directly
by the agent via `python3 scripts/<script>.py`.

---

## First-Run Setup

Run this checklist the **first time** a user asks to do anything with
SmartThings, or whenever the agent receives a `401 Unauthorized` error.

### Step 1 — Create a Personal Access Token

1. Open **https://account.smartthings.com/tokens** in a browser.
2. Click **Generate new token**.
3. Give it a name (e.g. "OpenClaw").
4. Under **Authorized Scopes**, enable at minimum:
   - Devices — **List all devices**, **See all devices**
   - (Recommended for future use) Scenes — **List**, **Execute**
5. Click **Generate token**.
6. **Copy the token immediately** — SmartThings only shows it once.

### Step 2 — Store the Token Securely

Add the following line to `~/.openclaw/.env`:

```
SMARTTHINGS_TOKEN=your-token-here
```

OpenClaw injects this as an environment variable at runtime. The token is
never written to the repository or any file inside the project directory.

### Step 3 — Verify Setup

Run:

```
python3 scripts/list_devices.py
```

Expected output: a JSON array of devices. An empty array `[]` means the
account has no devices or the token lacks the required scopes.

---

## Available Commands

### List Devices

Lists every device with its label, type, room, and component/capability tree.

```
python3 scripts/list_devices.py
```

**Output format** (JSON array to stdout):

```json
[
  {
    "deviceId": "abc-123",
    "label": "Living Room Light",
    "name": "LIFX Color Bulb",
    "type": "LAN",
    "roomId": "room-xyz",
    "components": [
      {
        "id": "main",
        "capabilities": ["switch", "switchLevel", "colorControl", "colorTemperature"]
      }
    ]
  }
]
```

Use `deviceId` values from this output with `get_status.py`.

### Get Device Status

Retrieves the full current state of a single device or all devices.

**Single device:**

```
python3 scripts/get_status.py --device-id <deviceId>
```

**All devices:**

```
python3 scripts/get_status.py --all
```

**Output format** (JSON to stdout):

```json
{
  "deviceId": "abc-123",
  "label": "Living Room Light",
  "status": {
    "main": {
      "switch": { "switch": { "value": "on" } },
      "switchLevel": { "level": { "value": 75, "unit": "%" } }
    }
  }
}
```

`--all` returns a JSON array of the above shape.

---

## Agent Workflow Guidance

### "What devices do I have?"

1. Run `python3 scripts/list_devices.py`
2. Parse the JSON array from stdout.
3. Present device labels, types, and key capabilities in a readable list.
4. Offer to check status for any specific device.

### "Is the front door locked?" / "What is the status of X?"

1. If you do not have the device ID, run `list_devices.py` first.
2. Match the user's description to a label in the device list.
3. Note the component ID from the device's `components` array (usually `main`).
4. Run `python3 scripts/get_status.py --device-id <deviceId>`
5. Navigate the status using the path `status.<componentId>.<capabilityId>.<attribute>.value`.

### "What's the status of all my lights?"

1. Run `list_devices.py` to find devices that have `switch` in their capabilities.
2. Run `get_status.py --all` and filter results to those devices, or run
   `get_status.py --device-id` individually for each matched device.
3. Report label, switch state, and level (if present) for each.

### "What's the temperature in the hallway?"

1. Run `list_devices.py` to find a device with `temperatureMeasurement` capability
   whose label matches the user's description.
2. Run `get_status.py --device-id <deviceId>`
3. Read `status.main.temperatureMeasurement.temperature.value` and `.unit`.

### "Give me a full status report of everything"

1. Run `python3 scripts/get_status.py --all`
2. Group results by room (using `roomId` from `list_devices.py` if needed).
3. Summarise each device's key state in plain language.

### Common Capability Value Reference

| Capability               | Attribute path (from `status.<component>`)              | Typical values          |
|--------------------------|---------------------------------------------------------|-------------------------|
| `switch`                 | `switch.switch.value`                                   | `"on"` / `"off"`        |
| `switchLevel`            | `switchLevel.level.value`                               | `0`–`100` (integer, %)  |
| `colorControl`           | `colorControl.hue.value`, `.saturation.value`           | `0`–`100`               |
| `colorTemperature`       | `colorTemperature.colorTemperature.value`               | Kelvin (e.g. `2700`)    |
| `temperatureMeasurement` | `temperatureMeasurement.temperature.value` + `.unit`    | float, `"C"` or `"F"`   |
| `contactSensor`          | `contactSensor.contact.value`                           | `"open"` / `"closed"`   |
| `motionSensor`           | `motionSensor.motion.value`                             | `"active"` / `"inactive"` |
| `lock`                   | `lock.lock.value`                                       | `"locked"` / `"unlocked"` |
| `battery`                | `battery.battery.value`                                 | `0`–`100` (integer, %)  |
| `presenceSensor`         | `presenceSensor.presence.value`                         | `"present"` / `"not present"` |

---

## Error Handling

All scripts print error details to **stderr** and exit with a non-zero code.

| Exit code | Meaning                                                  | Agent action                                      |
|-----------|----------------------------------------------------------|---------------------------------------------------|
| `0`       | Success                                                  | —                                                 |
| `1`       | General error (bad arguments, unexpected exception)      | Report the stderr message to the user             |
| `2`       | Authentication error (401) — token missing or invalid    | Re-run First-Run Setup with the user              |
| `3`       | Not found (404) — device ID does not exist               | Confirm device ID via `list_devices.py`           |
| `4`       | Rate limited (429)                                       | Wait a few seconds and retry                      |
| `5`       | SmartThings server error (5xx)                           | Inform user; retry after a short delay            |

---

## Future Expansion (Planned)

The following are not yet implemented. The architecture in
`scripts/smartthings_client.py` is designed to support them cleanly:

- `scripts/send_command.py` — turn devices on/off, set levels, lock/unlock
- `scripts/list_scenes.py` — list available scenes
- `scripts/execute_scene.py` — execute a scene by ID
- `scripts/list_rules.py` / `scripts/create_rule.py` — manage automation rules
- `scripts/subscribe.py` — register SSE/webhook event subscriptions

---

## Security Notes

- The PAT grants full access to the associated SmartThings account. Treat it
  like a password.
- Scripts read `SMARTTHINGS_TOKEN` from the environment only — the token is
  never passed as a command-line argument, avoiding shell history exposure.
- To rotate the token: delete it at **account.smartthings.com/tokens**,
  generate a new one, and update `~/.openclaw/.env`.
- Never commit `~/.openclaw/.env` or any file containing the token.
