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
      SMARTTHINGS_CLIENT_ID: "smartthings_client_id"
      SMARTTHINGS_CLIENT_SECRET: "smartthings_client_secret"
      SMARTTHINGS_ACCESS_TOKEN: "smartthings_access_token"
      SMARTTHINGS_REFRESH_TOKEN: "smartthings_refresh_token"
      SMARTTHINGS_TOKEN_EXPIRES_AT: "smartthings_token_expires_at"
    bins: ["python3", "node"]
    primaryEnv: SMARTTHINGS_ACCESS_TOKEN
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
SmartThings. SmartThings requires OAuth 2.0 — Personal Access Tokens now
expire after 24 hours and are not suitable for ongoing use.

### Step 1 — Register an OAuth App

You need a `client_id` and `client_secret` from a registered SmartThings
OAuth application. This is a one-time step.

1. Install the SmartThings CLI:
   ```
   npm install -g @smartthings/cli
   ```
2. Authenticate the CLI:
   ```
   smartthings login
   ```
3. Create an OAuth app:
   ```
   smartthings apps:create
   ```
   When prompted:
   - **Redirect URI**: `http://localhost:8080/callback`
   - **Scopes**: `r:devices:*  x:devices:*  r:locations:*  r:scenes:*  x:scenes:*`
4. The CLI will display a `client_id` and `client_secret`. **Copy both immediately.**

### Step 2 — Store Client Credentials

Add the following to `~/.openclaw/.env`:

```
SMARTTHINGS_CLIENT_ID=your-client-id-here
SMARTTHINGS_CLIENT_SECRET=your-client-secret-here
```

### Step 3 — Authorize and Obtain Tokens

Run the OAuth flow script:

```
python3 scripts/auth.py
```

This will:
1. Open the SmartThings authorization page in your browser
2. Ask you to log in and grant permissions
3. Automatically capture the callback and exchange for tokens
4. Save `SMARTTHINGS_ACCESS_TOKEN`, `SMARTTHINGS_REFRESH_TOKEN`, and
   `SMARTTHINGS_TOKEN_EXPIRES_AT` to `~/.openclaw/.env`

### Step 4 — Verify Setup

```
python3 scripts/list_devices.py
```

Expected output: a JSON array of devices. An empty array `[]` means the
account has no devices or the app lacks the required scopes.

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

### Handling an expired token (exit code 2)

1. Run `python3 scripts/auth.py --refresh`
2. Retry the original command.
3. If `auth.py --refresh` itself exits 2, the refresh token has expired (>30 days).
   Re-run First-Run Setup (Step 3 only — client credentials do not need to change).

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
| `2`       | Authentication error (401) — token missing or expired    | Run `python3 scripts/auth.py --refresh`; if that also fails (exit 2), re-run First-Run Setup |
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

- `client_secret` and tokens grant access to the associated SmartThings
  account. Treat them like passwords.
- All credentials are read from environment variables only — never from
  command-line arguments, avoiding shell history exposure.
- **Access tokens** expire after 24 hours. Run `python3 scripts/auth.py --refresh`
  to renew (the agent will do this automatically when it sees exit code 2).
- **Refresh tokens** expire after 30 days of non-use. If refresh fails, run
  `python3 scripts/auth.py` to re-authorize.
- To revoke access entirely: delete the OAuth app via `smartthings apps:delete`
  and remove credentials from `~/.openclaw/.env`.
- Never commit `~/.openclaw/.env` or any file containing credentials.
