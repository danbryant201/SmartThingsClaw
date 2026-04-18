"""
OAuth 2.0 Authorization Code Flow for SmartThings.

Usage:
    python3 scripts/auth.py           # Start interactive OAuth flow (first-time setup)
    python3 scripts/auth.py --refresh # Refresh using stored refresh token
"""

import argparse
import base64
import http.server
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

AUTH_URL = "https://api.smartthings.com/oauth/authorize"
TOKEN_URL = "https://api.smartthings.com/oauth/token"
REDIRECT_PORT = 8080
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"
DEFAULT_SCOPES = "r:devices:* x:devices:* r:locations:* r:scenes:* x:scenes:*"
ENV_FILE = os.path.expanduser("~/.openclaw/.env")


def build_auth_url(client_id: str, scopes: str = DEFAULT_SCOPES) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "scope": scopes,
        "redirect_uri": REDIRECT_URI,
    }
    return AUTH_URL + "?" + urllib.parse.urlencode(params)


def exchange_code(client_id: str, client_secret: str, code: str) -> dict:
    """Exchange an authorization code for access + refresh tokens."""
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    body = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }).encode()
    req = urllib.request.Request(
        TOKEN_URL,
        data=body,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        tokens = json.loads(resp.read().decode())
    tokens["expires_at"] = int(time.time()) + tokens.get("expires_in", 86400)
    return tokens


def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> dict:
    """Obtain a new access token using a refresh token."""
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }).encode()
    req = urllib.request.Request(
        TOKEN_URL,
        data=body,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        tokens = json.loads(resp.read().decode())
    tokens["expires_at"] = int(time.time()) + tokens.get("expires_in", 86400)
    return tokens


def save_tokens(tokens: dict, env_path: str = ENV_FILE) -> None:
    """Write/update token values in the OpenClaw env file."""
    updates = {
        "SMARTTHINGS_ACCESS_TOKEN": tokens.get("access_token", ""),
        "SMARTTHINGS_REFRESH_TOKEN": tokens.get("refresh_token", ""),
        "SMARTTHINGS_TOKEN_EXPIRES_AT": str(tokens.get("expires_at", "")),
    }

    os.makedirs(os.path.dirname(os.path.abspath(env_path)), exist_ok=True)
    try:
        with open(env_path) as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []

    updated_keys: set[str] = set()
    new_lines = []
    for line in lines:
        key = line.split("=", 1)[0].strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}\n")
            updated_keys.add(key)
        else:
            new_lines.append(line)
    for key, val in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={val}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)


def _wait_for_callback() -> str:
    """Start a local HTTP server and block until the OAuth callback arrives."""
    auth_code: list[str] = []

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if "code" in params:
                auth_code.append(params["code"][0])
                self.send_response(200)
                self.end_headers()
                self.wfile.write(
                    b"<html><body><h2>Authorization successful!</h2>"
                    b"<p>You can close this tab and return to the terminal.</p>"
                    b"</body></html>"
                )
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"<html><body><h2>Authorization failed.</h2></body></html>")

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("localhost", REDIRECT_PORT), _Handler)
    server.timeout = 120
    print(f"Waiting for callback on http://localhost:{REDIRECT_PORT}/callback (timeout: 120s)...")
    server.handle_request()

    if not auth_code:
        raise RuntimeError("Authorization failed: no code received in callback.")
    return auth_code[0]


def run_auth_flow() -> None:
    """Interactive first-time OAuth flow: open browser, capture callback, save tokens."""
    client_id = os.environ.get("SMARTTHINGS_CLIENT_ID", "")
    client_secret = os.environ.get("SMARTTHINGS_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        print(
            "ERROR: SMARTTHINGS_CLIENT_ID and SMARTTHINGS_CLIENT_SECRET must be set "
            "in ~/.openclaw/.env before running this script.",
            file=sys.stderr,
        )
        print("\nTo register an OAuth app:", file=sys.stderr)
        print("  1. Install the SmartThings CLI:  npm install -g @smartthings/cli", file=sys.stderr)
        print("  2. Authenticate:                  smartthings login", file=sys.stderr)
        print("  3. Create the app:                smartthings apps:create", file=sys.stderr)
        print("     - Set redirect URI to:         http://localhost:8080/callback", file=sys.stderr)
        print("  4. Copy client_id and client_secret into ~/.openclaw/.env", file=sys.stderr)
        sys.exit(1)

    auth_url = build_auth_url(client_id)
    print("\nOpening SmartThings authorization page in your browser...")
    print(f"If it does not open automatically, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    code = _wait_for_callback()
    print("Code received. Exchanging for tokens...")
    tokens = exchange_code(client_id, client_secret, code)
    save_tokens(tokens)

    hours = tokens.get("expires_in", 86400) // 3600
    print(f"Done. Access token saved (expires in {hours}h).")
    print("Tokens are stored in ~/.openclaw/.env")


def run_refresh() -> None:
    """Non-interactive token refresh using the stored refresh token."""
    client_id = os.environ.get("SMARTTHINGS_CLIENT_ID", "")
    client_secret = os.environ.get("SMARTTHINGS_CLIENT_SECRET", "")
    stored_refresh = os.environ.get("SMARTTHINGS_REFRESH_TOKEN", "")

    if not client_id or not client_secret:
        print("ERROR: SMARTTHINGS_CLIENT_ID and SMARTTHINGS_CLIENT_SECRET not set.", file=sys.stderr)
        sys.exit(1)
    if not stored_refresh:
        print(
            "ERROR: SMARTTHINGS_REFRESH_TOKEN not set. "
            "Run python3 scripts/auth.py to complete first-time setup.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        tokens = refresh_access_token(client_id, client_secret, stored_refresh)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print(
                "ERROR: Refresh token is invalid or expired (>30 days). "
                "Run python3 scripts/auth.py to re-authorize.",
                file=sys.stderr,
            )
            sys.exit(2)
        raise

    save_tokens(tokens)
    hours = tokens.get("expires_in", 86400) // 3600
    print(f"Tokens refreshed. New access token expires in {hours}h.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SmartThings OAuth authentication")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh tokens using the stored refresh token (non-interactive)",
    )
    args = parser.parse_args()
    if args.refresh:
        run_refresh()
    else:
        run_auth_flow()
