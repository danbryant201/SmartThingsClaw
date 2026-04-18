import json
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])

from smartthings_client import (
    AuthError,
    RateLimitError,
    ServerError,
    SmartThingsError,
    SmartThingsClient,
)


def normalise_device(device: dict) -> dict:
    components = [
        {
            "id": c["id"],
            "capabilities": [cap["id"] for cap in c.get("capabilities", [])],
        }
        for c in device.get("components", [])
    ]
    return {
        "deviceId": device.get("deviceId", ""),
        "label": device.get("label", ""),
        "name": device.get("name", ""),
        "type": device.get("type", ""),
        "roomId": device.get("roomId", ""),
        "components": components,
    }


def main():
    try:
        client = SmartThingsClient()
        devices = client.list_devices()
        print(json.dumps([normalise_device(d) for d in devices], indent=2))
    except AuthError as e:
        print(f"Authentication error: {e}", file=sys.stderr)
        print("Run first-time setup: see SKILL.md for instructions.", file=sys.stderr)
        sys.exit(2)
    except RateLimitError as e:
        print(f"Rate limited: {e}", file=sys.stderr)
        print("Wait a moment and try again.", file=sys.stderr)
        sys.exit(4)
    except ServerError as e:
        print(f"SmartThings server error: {e}", file=sys.stderr)
        sys.exit(5)
    except SmartThingsError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
