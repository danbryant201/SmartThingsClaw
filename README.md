# SmartThingsClaw

An [OpenClaw](https://openclaw.ai) skill for Samsung SmartThings. List your connected devices and get their live status through natural language.

## What it does

- **List devices** — see every device on your SmartThings account with its components and capabilities
- **Get status** — retrieve the current state of any device or all devices at once

## Setup

1. Generate a Personal Access Token at **https://account.smartthings.com/tokens**
   (scopes: List all devices, See all devices)
2. Add it to `~/.openclaw/.env`:
   ```
   SMARTTHINGS_TOKEN=your-token-here
   ```
3. Verify: `python3 scripts/list_devices.py`

Full setup instructions are in [SKILL.md](SKILL.md).

## Usage

```bash
# List all devices with components and capabilities
python3 scripts/list_devices.py

# Get status of a single device
python3 scripts/get_status.py --device-id <deviceId>

# Get status of all devices
python3 scripts/get_status.py --all
```

## Files

| File | Purpose |
|------|---------|
| [SKILL.md](SKILL.md) | OpenClaw skill definition and agent instructions |
| [scripts/smartthings_client.py](scripts/smartthings_client.py) | SmartThings API client |
| [scripts/list_devices.py](scripts/list_devices.py) | List devices entry point |
| [scripts/get_status.py](scripts/get_status.py) | Get device status entry point |
| [references/smartthings_api.md](references/smartthings_api.md) | API quick reference |

## Requirements

Python 3.10+ (stdlib only — no pip install required)

## License

MIT
