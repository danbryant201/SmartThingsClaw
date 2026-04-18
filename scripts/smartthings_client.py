import json
import os
import urllib.error
import urllib.parse
import urllib.request


class SmartThingsError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class AuthError(SmartThingsError):
    pass


class NotFoundError(SmartThingsError):
    pass


class RateLimitError(SmartThingsError):
    pass


class ServerError(SmartThingsError):
    pass


class SmartThingsClient:
    BASE_URL = "https://api.smartthings.com/v1"

    def __init__(self, token: str | None = None):
        self._token = token or os.environ.get("SMARTTHINGS_TOKEN")
        if not self._token:
            raise AuthError(
                "No SmartThings token found. Set SMARTTHINGS_TOKEN in ~/.openclaw/.env"
            )

    def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        body: dict | None = None,
    ) -> dict | list:
        url = f"{self.BASE_URL}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method=method,
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body_text = ""
            try:
                body_text = e.read().decode()
            except Exception:
                pass
            msg = f"HTTP {e.code}: {body_text or e.reason}"
            if e.code == 401:
                raise AuthError(msg, e.code) from e
            if e.code == 404:
                raise NotFoundError(msg, e.code) from e
            if e.code == 429:
                raise RateLimitError(msg, e.code) from e
            if e.code >= 500:
                raise ServerError(msg, e.code) from e
            raise SmartThingsError(msg, e.code) from e
        except urllib.error.URLError as e:
            raise SmartThingsError(f"Network error: {e.reason}") from e

    def _paginate(self, path: str, params: dict | None = None) -> list:
        items = []
        url = path
        while url:
            data = self._request("GET", url, params=params if url == path else None)
            items.extend(data.get("items", []))
            next_link = data.get("_links", {}).get("next", {}).get("href")
            if next_link:
                # next href is an absolute URL; strip the base to get the path+query
                url = next_link.replace(self.BASE_URL, "")
            else:
                url = None
        return items

    def list_devices(self) -> list[dict]:
        return self._paginate("/devices")

    def get_device(self, device_id: str) -> dict:
        return self._request("GET", f"/devices/{device_id}")

    def get_device_status(self, device_id: str) -> dict:
        return self._request("GET", f"/devices/{device_id}/status")

    # ── Future methods (not yet implemented) ────────────────────────────
    # def send_command(self, device_id, component, capability, command, arguments=None): ...
    # def list_scenes(self): ...
    # def execute_scene(self, scene_id): ...
    # def list_rules(self): ...
    # def list_subscriptions(self, installed_app_id): ...
