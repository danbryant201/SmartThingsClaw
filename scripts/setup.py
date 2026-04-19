"""
SmartThings setup helper for agent-driven configuration.

Usage:
    python3 scripts/setup.py check                        # Report configuration status as JSON
    python3 scripts/setup.py save-creds ID SECRET         # Save OAuth client credentials
    python3 scripts/setup.py register-app --pat <PAT>     # Register OAuth app via SmartThings CLI
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, __file__.rsplit("/", 1)[0])

from auth import ENV_FILE, save_credentials


def check_config() -> dict:
    client_id = bool(os.environ.get("SMARTTHINGS_CLIENT_ID"))
    client_secret = bool(os.environ.get("SMARTTHINGS_CLIENT_SECRET"))
    access_token = bool(os.environ.get("SMARTTHINGS_ACCESS_TOKEN"))
    refresh_token = bool(os.environ.get("SMARTTHINGS_REFRESH_TOKEN"))

    expires_at_str = os.environ.get("SMARTTHINGS_TOKEN_EXPIRES_AT", "")
    try:
        expires_at = int(expires_at_str) if expires_at_str else None
    except ValueError:
        expires_at = None

    token_expired = expires_at is not None and time.time() >= expires_at

    if not (client_id and client_secret):
        next_step = "register_app"
    elif not access_token or token_expired:
        next_step = "authorize"
    else:
        next_step = "ready"

    return {
        "client_id_set": client_id,
        "client_secret_set": client_secret,
        "access_token_set": access_token,
        "refresh_token_set": refresh_token,
        "token_expired": token_expired,
        "next_step": next_step,
        "ready": next_step == "ready",
    }


def _ensure_cli_installed() -> None:
    """Check the SmartThings CLI is available; install via npm if not."""
    result = subprocess.run(["smartthings", "--version"], capture_output=True)
    if result.returncode == 0:
        return
    result = subprocess.run(
        ["npm", "install", "-g", "@smartthings/cli"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to install SmartThings CLI:\n{result.stderr}")


def register_app(pat: str, name: str = "OpenClaw", env_path: str = ENV_FILE) -> dict:
    """Register a SmartThings OAuth app via the CLI and save the credentials.

    Returns a dict with 'client_id' and 'client_secret'.
    """
    _ensure_cli_installed()

    config = {
        "displayName": name,
        "description": f"{name} SmartThings integration",
        "oauth": {
            "scope": [
                "r:devices:*",
                "x:devices:*",
                "r:locations:*",
                "r:scenes:*",
                "x:scenes:*",
            ],
            "redirectUris": ["http://localhost:8080/callback"],
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config, f)
        config_path = f.name

    try:
        result = subprocess.run(
            ["smartthings", "apps:create", "-i", config_path, "--json", "--token", pat],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"SmartThings CLI error:\n{result.stderr or result.stdout}")

        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Unexpected CLI output (not JSON):\n{result.stdout}") from exc

        client_id = output.get("oauthClientId")
        client_secret = output.get("oauthClientSecret")
        if not client_id or not client_secret:
            raise RuntimeError(f"Credentials missing from CLI response:\n{result.stdout}")

        save_credentials(client_id, client_secret, env_path)
        return {"client_id": client_id, "client_secret": client_secret}
    finally:
        os.unlink(config_path)


def main():
    parser = argparse.ArgumentParser(description="SmartThings setup helper")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="Show configuration status as JSON")

    sp = sub.add_parser("save-creds", help="Save OAuth client credentials to ~/.openclaw/.env")
    sp.add_argument("client_id", help="OAuth client ID")
    sp.add_argument("client_secret", help="OAuth client secret")

    rp = sub.add_parser("register-app", help="Register SmartThings OAuth app via CLI using a PAT")
    rp.add_argument("--pat", required=True, help="Short-lived Personal Access Token from account.smartthings.com/tokens")
    rp.add_argument("--name", default="OpenClaw", help="Display name for the OAuth app (default: OpenClaw)")

    args = parser.parse_args()

    if args.command == "check":
        print(json.dumps(check_config(), indent=2))
    elif args.command == "save-creds":
        save_credentials(args.client_id, args.client_secret)
        print(f"Credentials saved to {ENV_FILE}")
    elif args.command == "register-app":
        try:
            creds = register_app(args.pat, name=args.name)
            print(json.dumps({"status": "ok", "client_id": creds["client_id"]}))
        except RuntimeError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
