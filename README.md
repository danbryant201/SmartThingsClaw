# SmartThingsClaw

An [OpenClaw](https://openclaw.ai) skill for Samsung SmartThings. Monitor and control your connected devices through natural language.

## What it does

- **List devices** — see every device on your SmartThings account with its components and capabilities
- **Get status** — retrieve the current state of any device or all devices at once
- **Control devices** — send commands: turn on/off, set brightness, lock/unlock, set temperature, and any other capability command

## Setup

App registration uses the **SmartThings CLI** (not the Developer Console — the Console is for hardware device certification only).

1. Generate a Personal Access Token at **https://account.smartthings.com/tokens** (no scopes needed — it's only used to authenticate the CLI)
2. Register the OAuth app: `python3 scripts/setup.py register-app --pat <PAT>`
3. Authorize: `python3 scripts/auth.py` (opens browser; follow prompts)
4. Verify: `python3 scripts/list_devices.py`

Full setup instructions are in [SKILL.md](SKILL.md).

## Usage

```bash
# List all devices with components and capabilities
python3 scripts/list_devices.py

# Get status of a single device
python3 scripts/get_status.py --device-id <deviceId>

# Get status of all devices
python3 scripts/get_status.py --all

# Turn a switch on or off
python3 scripts/send_command.py --device-id <deviceId> --capability switch --command on

# Set brightness (0-100)
python3 scripts/send_command.py --device-id <deviceId> --capability switchLevel --command setLevel --args '[75]'

# Lock a door
python3 scripts/send_command.py --device-id <deviceId> --capability lock --command lock
```

## Files

| File | Purpose |
|------|---------|
| [SKILL.md](SKILL.md) | OpenClaw skill definition and agent instructions |
| [scripts/smartthings_client.py](scripts/smartthings_client.py) | SmartThings API client |
| [scripts/setup.py](scripts/setup.py) | First-time setup helper |
| [scripts/auth.py](scripts/auth.py) | OAuth 2.0 authorization flow |
| [scripts/list_devices.py](scripts/list_devices.py) | List devices entry point |
| [scripts/get_status.py](scripts/get_status.py) | Get device status entry point |
| [scripts/send_command.py](scripts/send_command.py) | Send device commands entry point |
| [references/smartthings_api.md](references/smartthings_api.md) | API quick reference |

## Requirements

Python 3.10+ (stdlib only — no pip install required)  
Node.js / npm (for first-time app registration via `@smartthings/cli`)

## License

MIT
