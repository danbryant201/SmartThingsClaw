---
name: smartthings
description: >
  Monitor and control Samsung SmartThings devices. List connected devices,
  retrieve live status, and send commands (switch on/off, set brightness,
  lock/unlock, set temperature, and any other capability command).
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

This skill connects to the Samsung SmartThings cloud API using OAuth 2.0.
It lets you:

- List every device on the account with its components and capabilities
- Retrieve the current status of any device or all devices at once
- Send commands to any device (on/off, brightness, lock/unlock, temperature, etc.)

Scripts live in `scripts/` relative to this skill and are invoked directly
by the agent via `python3 scripts/<script>.py`.

---

## Setup Flow (Agent-Driven)

When the user asks to connect SmartThings, or any command returns exit code 2
with no refresh token stored, follow this flow. No CLI tools are required —
everything happens through chat.

### Step A — Check State

```
python3 scripts/setup.py check
```

Read `next_step` from the JSON output and jump to the matching step below.
If `next_step` is `"ready"`, skip to Step D to verify.

### Step B — Register an App (`next_step == "register_app"`)

> **Note:** The SmartThings Developer Console (developer.smartthings.com/console) is for hardware
> device certification only — it cannot create OAuth-In apps. App registration must go through
> the SmartThings CLI.

Tell the user:

> "I need to register a SmartThings OAuth app — this only needs to be done once, and I'll handle
> most of it automatically. I just need a short-lived Personal Access Token (PAT) from you.
>
> 1. Open **account.smartthings.com/tokens** in any browser and sign in with your Samsung account.
> 2. Click **Generate new token**, give it any name (e.g. "OpenClaw setup"). Under
>    **Applications**, check **See all apps** and **Manage all apps**. Then click **Generate**.
> 3. Copy the token that appears (it's only shown once) and paste it here."

Once the user provides the PAT, run:

```
python3 scripts/setup.py register-app --pat <PAT>
```

This will:
- Install the SmartThings CLI if not already present (`npm install -g @smartthings/cli`)
- Create the OAuth app with redirect URI `http://127.0.0.1:8080/callback` and the required scopes
- Save the Client ID and Client Secret automatically

> **Important:** The redirect URI is `http://127.0.0.1:8080/callback` (not `localhost`).
> SmartThings has a known issue with the hostname "localhost" in redirect URIs.

On success the command prints `{"status": "ok", "client_id": "..."}`. Then continue to Step C.

### Step C — Authorize (`next_step == "authorize"`, or after Step B)

> ⚠️ **Critical guardrails — read before running anything:**
> - **Never** call the authorization URL with WebFetch or any automated tool.
>   It must be opened in the user's real browser.
> - **Never** try to exchange the code yourself — always pass it to `--exchange-code`.
> - The code is **single-use**. Consuming it twice (e.g. callback server + manual exchange)
>   causes `invalid_grant` errors. Follow the two steps below exactly.

#### Step C.1 — Get the authorization URL

Run:

```
python3 scripts/auth.py --get-url
```

Copy the full URL printed after `AUTHORIZATION_URL:` and relay it to the user:

> "Please open this URL in your browser and sign in with your Samsung account, then click
> **Allow**:
>
> `<URL>`
>
> After authorizing, your browser will try to redirect to `127.0.0.1:8080` — that page
> will likely fail to load. That's fine. Just copy the full address bar URL (it will look
> like `http://127.0.0.1:8080/callback?code=...`) and paste it back here."

Wait for the user to paste the callback URL before proceeding. Do **not** run Step C.2
in the same turn as Step C.1.

#### Step C.2 — Exchange the code

When the user pastes the callback URL (or just the bare code value), run:

```
python3 scripts/auth.py --exchange-code "<paste exactly what the user provided>"
```

`--exchange-code` accepts both the full callback URL and a bare code value.
Exit 0 means tokens are saved. Proceed to Step D.

### Step D — Verify

```
python3 scripts/list_devices.py
```

If it returns a JSON array (even `[]`), tell the user setup is complete. An empty array
means the account has no devices or the OAuth app is missing scopes.

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

### Send Device Command

Sends a command to a specific device capability.

```
python3 scripts/send_command.py --device-id <deviceId> --capability <cap> --command <cmd>
python3 scripts/send_command.py --device-id <deviceId> --capability <cap> --command <cmd> --args '<json_array>'
```

**Common examples:**

```bash
# Turn a switch on or off
python3 scripts/send_command.py --device-id abc-123 --capability switch --command on
python3 scripts/send_command.py --device-id abc-123 --capability switch --command off

# Set brightness (0–100)
python3 scripts/send_command.py --device-id abc-123 --capability switchLevel --command setLevel --args '[75]'

# Lock or unlock
python3 scripts/send_command.py --device-id abc-123 --capability lock --command lock
python3 scripts/send_command.py --device-id abc-123 --capability lock --command unlock

# Set thermostat cooling setpoint (degrees)
python3 scripts/send_command.py --device-id abc-123 --capability thermostatCoolingSetpoint --command setCoolingSetpoint --args '[22]'
```

**Output format** (JSON to stdout — SmartThings API acknowledgement):

```json
{ "results": [{ "id": "main/switch/on", "status": "ACCEPTED" }] }
```

Exit 0 means the command was accepted by SmartThings. The device carries it out asynchronously.

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

### "Turn off the living room light" / "Set the thermostat to 21 degrees" / control requests

1. If you do not have the device ID, run `list_devices.py` first.
2. Match the user's description to a device label. Note its `deviceId` and which capabilities it has.
3. Map the user's intent to a capability and command:
   - Switch on/off → capability `switch`, command `on` or `off`
   - Dim/brighten → capability `switchLevel`, command `setLevel`, args `[<0-100>]`
   - Lock/unlock → capability `lock`, command `lock` or `unlock`
   - Set temperature → capability `thermostatCoolingSetpoint` or `thermostatHeatingSetpoint`, command `setCoolingSetpoint`/`setHeatingSetpoint`, args `[<degrees>]`
4. Run `send_command.py` with the resolved parameters.
5. Confirm to the user that the command was sent.

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
| `3`       | Not found (404) — device ID does not exist (device scripts only; `auth.py` uses 3 as a legacy fallback, not reachable via SKILL.md flow) | Confirm device ID via `list_devices.py` |
| `4`       | Rate limited (429)                                       | Wait a few seconds and retry                      |
| `5`       | SmartThings server error (5xx)                           | Inform user; retry after a short delay            |

---

## Future Expansion (Planned)

The following are not yet implemented. The architecture in
`scripts/smartthings_client.py` is designed to support them cleanly:

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
