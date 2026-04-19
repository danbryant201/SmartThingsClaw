"""
Send a command to a SmartThings device capability.

Usage:
    python3 scripts/send_command.py --device-id <ID> --capability switch --command on
    python3 scripts/send_command.py --device-id <ID> --capability switchLevel --command setLevel --args '[75]'
    python3 scripts/send_command.py --device-id <ID> --capability lock --command lock
    python3 scripts/send_command.py --device-id <ID> --capability thermostatCoolingSetpoint --command setCoolingSetpoint --args '[22]'
"""

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


def main():
    parser = argparse.ArgumentParser(description="Send a command to a SmartThings device")
    parser.add_argument("--device-id", required=True, metavar="ID", help="Device ID")
    parser.add_argument("--capability", required=True, help="Capability ID (e.g. switch, switchLevel, lock)")
    parser.add_argument("--command", required=True, help="Command name (e.g. on, off, setLevel, lock)")
    parser.add_argument(
        "--args",
        metavar="JSON",
        default="[]",
        help='Command arguments as a JSON array (e.g. \'[75]\' for setLevel). Default: []',
    )
    parser.add_argument(
        "--component",
        default="main",
        help="Component ID (default: main)",
    )
    args = parser.parse_args()

    try:
        arguments = json.loads(args.args)
    except json.JSONDecodeError as e:
        print(f"ERROR: --args is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        client = SmartThingsClient()
        result = client.send_command(
            device_id=args.device_id,
            capability=args.capability,
            command=args.command,
            arguments=arguments,
            component=args.component,
        )
        print(json.dumps(result, indent=2))
    except AuthError as e:
        print(f"Authentication error: {e}", file=sys.stderr)
        print("Run: python3 scripts/auth.py --refresh", file=sys.stderr)
        sys.exit(2)
    except NotFoundError as e:
        print(f"Device not found: {e}", file=sys.stderr)
        print("Verify the device ID with: python3 scripts/list_devices.py", file=sys.stderr)
        sys.exit(3)
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
