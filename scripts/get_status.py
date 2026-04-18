import argparse
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])

from smartthings_client import (
    AuthError,
    NotFoundError,
    RateLimitError,
    ServerError,
    SmartThingsError,
    SmartThingsClient,
)


def fetch_single(client: SmartThingsClient, device_id: str) -> dict:
    device = client.get_device(device_id)
    status = client.get_device_status(device_id)
    return {
        "deviceId": device_id,
        "label": device.get("label", ""),
        "status": status.get("components", status),
    }


def main():
    parser = argparse.ArgumentParser(description="Get SmartThings device status")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--device-id", metavar="ID", help="Device ID to query")
    group.add_argument("--all", action="store_true", help="Query all devices")
    args = parser.parse_args()

    try:
        client = SmartThingsClient()

        if args.device_id:
            print(json.dumps(fetch_single(client, args.device_id), indent=2))
        else:
            devices = client.list_devices()
            results = []
            for d in devices:
                device_id = d.get("deviceId", "")
                try:
                    results.append(fetch_single(client, device_id))
                except NotFoundError as e:
                    print(
                        f"Skipping {device_id} ({d.get('label', '')}): {e}",
                        file=sys.stderr,
                    )
            print(json.dumps(results, indent=2))

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
