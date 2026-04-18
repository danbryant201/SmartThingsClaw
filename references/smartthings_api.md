# SmartThings API Quick Reference

**Base URL:** `https://api.smartthings.com/v1`  
**Auth:** `Authorization: Bearer <SMARTTHINGS_ACCESS_TOKEN>`  
**Content-Type:** `application/json`

---

## Authentication (OAuth 2.0)

SmartThings uses Authorization Code Flow. Personal Access Tokens expire after
24 hours and are unsuitable for production.

| | |
|-|-|
| Authorization URL | `https://api.smartthings.com/oauth/authorize` |
| Token URL | `https://api.smartthings.com/oauth/token` |
| Token auth | HTTP Basic — `Authorization: Basic base64(client_id:client_secret)` |
| Access token lifetime | 24 hours |
| Refresh token lifetime | 30 days |

**Token request body** (`application/x-www-form-urlencoded`):

```
# Exchange authorization code
grant_type=authorization_code&code=<code>&redirect_uri=<uri>

# Refresh
grant_type=refresh_token&refresh_token=<token>
```

**Token response:**
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "expires_in": 86400,
  "scope": "r:devices:* x:devices:* ..."
}
```

**App registration** (one-time, via SmartThings CLI):
```
npm install -g @smartthings/cli
smartthings login
smartthings apps:create   # set redirect URI to http://localhost:8080/callback
```

---

## Devices

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/devices` | List all devices (paginated) |
| `GET` | `/devices/{deviceId}` | Get single device descriptor |
| `GET` | `/devices/{deviceId}/status` | Full status — all components and capabilities |
| `GET` | `/devices/{deviceId}/components/{componentId}/capabilities/{capabilityId}/status` | Status for a specific capability |
| `POST` | `/devices/{deviceId}/commands` | Send commands to a device *(future)* |

### Device descriptor shape

```json
{
  "deviceId": "string",
  "label": "string",
  "name": "string",
  "type": "LAN | ZIGBEE | ZWAVE | MATTER | ...",
  "roomId": "string",
  "components": [
    {
      "id": "main",
      "capabilities": [
        { "id": "switch", "version": 1 }
      ]
    }
  ]
}
```

### Status response shape

```json
{
  "components": {
    "main": {
      "switch": {
        "switch": { "value": "on", "timestamp": "..." }
      },
      "switchLevel": {
        "level": { "value": 75, "unit": "%", "timestamp": "..." }
      }
    }
  }
}
```

Note: `smartthings_client.get_device_status()` returns the `components` object
directly (the inner map), not the wrapper.

---

## Pagination

List endpoints return an envelope. Follow `_links.next.href` until absent.

```json
{
  "items": [ ... ],
  "_links": {
    "next": { "href": "https://api.smartthings.com/v1/devices?..." },
    "previous": { "href": "..." }
  }
}
```

`SmartThingsClient._paginate()` handles this automatically.

---

## Commands *(future)*

```
POST /devices/{deviceId}/commands
```

```json
{
  "commands": [
    {
      "component": "main",
      "capability": "switch",
      "command": "on",
      "arguments": []
    }
  ]
}
```

Common command examples:

| Capability    | Command  | Arguments              |
|---------------|----------|------------------------|
| `switch`      | `on`     | `[]`                   |
| `switch`      | `off`    | `[]`                   |
| `switchLevel` | `setLevel` | `[<0-100>, <duration_ms>]` |
| `lock`        | `lock`   | `[]`                   |
| `lock`        | `unlock` | `[]`                   |
| `colorControl`| `setHue` | `[<0-100>]`            |
| `colorControl`| `setSaturation` | `[<0-100>]`     |
| `colorTemperature` | `setColorTemperature` | `[<kelvin>]` |

---

## Scenes *(future)*

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/scenes` | List all scenes |
| `POST` | `/scenes/{sceneId}/execute` | Execute a scene |

---

## Rules *(future)*

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/rules`  | List all rules |
| `POST` | `/rules`  | Create a rule |
| `GET`  | `/rules/{ruleId}` | Get a rule |
| `PUT`  | `/rules/{ruleId}` | Update a rule |
| `DELETE` | `/rules/{ruleId}` | Delete a rule |

---

## Subscriptions / Events *(future)*

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/installedapps/{appId}/subscriptions` | List subscriptions |
| `POST` | `/installedapps/{appId}/subscriptions` | Create subscription |
| `DELETE` | `/installedapps/{appId}/subscriptions/{subscriptionId}` | Delete subscription |

---

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| `200` | OK |
| `204` | No Content (typical for command responses) |
| `400` | Bad Request — malformed body or missing required fields |
| `401` | Unauthorized — token missing, invalid, or expired |
| `403` | Forbidden — token lacks required scope |
| `404` | Not Found — device or resource does not exist |
| `422` | Unprocessable Entity — valid JSON but semantically invalid |
| `429` | Too Many Requests — rate limited |
| `5xx` | Server Error — retry after a delay |

---

## Token Scopes (minimum required for v1)

- `r:devices:*` — List and read all devices
- `r:scenes:*` — List scenes *(for future use)*
- `x:scenes:*` — Execute scenes *(for future use)*
