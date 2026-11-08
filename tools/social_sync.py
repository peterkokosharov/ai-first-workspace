#!/usr/bin/env python3
# =============================================================================
# tools/social_sync.py – Unified posting to Facebook, Gmail, Google Drive,
# Google Calendar.
#
# Stdlib only. Reads API keys/tokens from tools/secret.py (native credential
# store via kikolib.factory / secret-tool / kwallet / dcop / wcm / keychain).
#
# Key paths expected (set them first with tools/secret.py --backend auto set ...):
#   facebook/personal/api_key   -> Facebook Graph API access token
#   facebook/personal/page_id   -> Facebook Page ID (optional, for page posts)
#   google/personal/api_key     -> Google OAuth access token (OAuth2 bearer)
# -----------------------------------------------------------------------------

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

# Import secret tool the same way other project scripts do
sys.path.insert(0, str(ROOT / "tools"))
from secret import validate_path, SecretError  # noqa: E402

# ------------------------------------------------------------------ helpers

def _post(url: str, data: dict | None = None, headers: dict | None = None,
          timeout: float = 30.0) -> dict:
    """POST JSON to ``url`` and return parsed JSON response (or {} on error)."""
    headers = headers or {}
    headers.setdefault("Content-Type", "application/json")
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            try:
                return json.loads(raw.decode("utf-8")) if raw else {}
            except json.JSONDecodeError:
                return {"raw": raw.decode("utf-8", errors="replace")}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"error": True, "status": exc.code, "body": body[:500]}
    except urllib.error.URLError as exc:
        return {"error": True, "reason": str(exc.reason)}
    except Exception as exc:  # noqa: BLE001
        return {"error": True, "reason": repr(exc)}


def _get(url: str, params: dict | None = None, timeout: float = 30.0) -> dict:
    """GET ``url`` with optional query params, return parsed JSON."""
    full = url
    if params:
        full += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(full, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            try:
                return json.loads(raw.decode("utf-8")) if raw else {}
            except json.JSONDecodeError:
                return {"raw": raw.decode("utf-8", errors="replace")}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"error": True, "status": exc.code, "body": body[:500]}
    except urllib.error.URLError as exc:
        return {"error": True, "reason": str(exc.reason)}
    except Exception as exc:  # noqa: BLE001
        return {"error": True, "reason": repr(exc)}


# ------------------------------------------------------------------ Facebook

def fb_post(message: str, page_id: str | None = None,
            link: str | None = None) -> dict:
    """Post a text message (and optional link) to a Facebook Page feed.

    Requires:
      - key path ``facebook/personal/api_key``  -> Graph API access token
      - key path ``facebook/personal/page_id``  -> Page ID (optional;
        if omitted, posts to the authenticated user's timeline)
    """
    from secret import validate_path  # noqa: F401  (already imported)
    # secret.py imports kikolib internally; we just need the value
    import secret as secret_tool  # noqa: F401

    token = None
    page_id_val = None

    # We cannot easily import secret.py's internal state without re-running
    # its imports; instead we read via subprocess to avoid import side effects.
    import subprocess, tempfile, os
    # Better: read directly from secret tool via subprocess to avoid
    # import-time side effects on Linux (ctypes/wcm) that may fail here.
    def _get_secret(name: str) -> str | None:
        try:
            r = subprocess.run(
                ["python3", str(ROOT / "tools" / "secret.py"),
                 "--backend", "auto", "get", name],
                capture_output=True, text=True, timeout=15)
            if r.returncode == 0:
                return r.stdout.strip()
            return None
        except Exception:
            return None

    token = _get_secret("facebook/personal/api_key")
    if not token:
        return {"error": True, "reason": "no facebook/personal/api_key in secret store"}

    page_id_val = _get_secret("facebook/personal/page_id")

    target = f"https://graph.facebook.com/v18.0/{page_id_val}/feed" \
        if page_id_val else "https://graph.facebook.com/v18.0/me/feed"

    payload = {"message": message, "access_token": token}
    if link:
        payload["link"] = link

    return _post(target, data=payload)


# ------------------------------------------------------------------ Gmail

def gmail_send(to: str, subject: str, body_text: str) -> dict:
    """Send an email via Gmail API.

    Requires:
      - key path ``google/personal/api_key`` -> OAuth2 access token (Bearer)
    """
    import secret as secret_tool  # noqa: F401

    def _get_secret(name: str) -> str | None:
        try:
            r = subprocess.run(
                ["python3", str(ROOT / "tools" / "secret.py"),
                 "--backend", "auto", "get", name],
                capture_output=True, text=True, timeout=15)
            if r.returncode == 0:
                return r.stdout.strip()
            return None
        except Exception:
            return None

    token = _get_secret("google/personal/api_key")
    if not token:
        return {"error": True, "reason": "no google/personal/api_key in secret store"}

    import base64
    raw = f"To: {to}\r\nSubject: {subject}\r\n\r\n{body_text}"
    raw_b64 = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")

    payload = {"raw": raw_b64}
    return _post("https://gmail.googleapis.com/gmail/v1/users/me/messages",
                 data=payload)


# ------------------------------------------------------------------ Google Drive

def drive_upload(file_path: str, name: str | None = None,
                 parent_folder_id: str | None = None) -> dict:
    """Upload a file to Google Drive.

    Requires:
      - key path ``google/personal/api_key`` -> OAuth2 access token
    """
    import secret as secret_tool  # noqa: F401

    def _get_secret(name: str) -> str | None:
        try:
            r = subprocess.run(
                ["python3", str(ROOT / "tools" / "secret.py"),
                 "--backend", "auto", "get", name],
                capture_output=True, text=True, timeout=15)
            if r.returncode == 0:
                return r.stdout.strip()
            return None
        except Exception:
            return None

    token = _get_secret("google/personal/api_key")
    if not token:
        return {"error": True, "reason": "no google/personal/api_key in secret store"}

    metadata = {"name": name or Path(file_path).name}
    if parent_folder_id:
        metadata["parents"] = [parent_folder_id]

    # Multipart upload is more complex; for a first version we do simple upload
    # if the file is small, otherwise we'd need resumable upload.
    try:
        data = Path(file_path).read_bytes()
    except OSError as exc:
        return {"error": True, "reason": f"cannot read file: {exc}"}

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Upload-Content-Type": "application/octet-stream",
        "X-Upload-File-Name": Path(file_path).name,
    }

    url = ("https://www.googleapis.com/upload/drive/v3/files"
           "?uploadType=media&fields=id,name,webViewLink")
    if parent_folder_id:
        url += f"&fields=parents%2Cid%2Cname%2CwebViewLink"

    return _post(url, data=data, headers=headers)


# ------------------------------------------------------------------ Google Calendar

def calendar_create_event(summary: str, description: str | None = None,
                          start_iso: str | None = None,
                          end_iso: str | None = None,
                          attendees: list[str] | None = None) -> dict:
    """Create a Google Calendar event.

    Requires:
      - key path ``google/personal/api_key`` -> OAuth2 access token
    """
    import secret as secret_tool  # noqa: F401

    def _get_secret(name: str) -> str | None:
        try:
            r = subprocess.run(
                ["python3", str(ROOT / "tools" / "secret.py"),
                 "--backend", "auto", "get", name],
                capture_output=True, text=True, timeout=15)
            if r.returncode == 0:
                return r.stdout.strip()
            return None
        except Exception:
            return None

    token = _get_secret("google/personal/api_key")
    if not token:
        return {"error": True, "reason": "no google/personal/api_key in secret store"}

    event = {
        "summary": summary,
        "description": description or "",
        "start": {"dateTime": start_iso, "timeZone": "Europe/Sofia"},
        "end": {"dateTime": end_iso, "timeZone": "Europe/Sofia"},
    }
    if attendees:
        event["attendees"] = [{"email": a} for a in attendees]

    return _post("https://www.googleapis.com/calendar/v3/calendars/primary/events",
                 data=event)


# ------------------------------------------------------------------ CLI

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        prog="social_sync.py",
        description="Post to Facebook, Gmail, Google Drive, Google Calendar")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("fb", help="post to Facebook")
    p.add_argument("message")
    p.add_argument("--link", help="optional link to attach")
    p.set_defaults(func=lambda a: fb_post(a.message, link=a.link))

    p = sub.add_parser("gmail", help="send email via Gmail")
    p.add_argument("to")
    p.add_argument("subject")
    p.add_argument("body")
    p.set_defaults(func=lambda a: gmail_send(a.to, a.subject, a.body))

    p = sub.add_parser("drive", help="upload file to Google Drive")
    p.add_argument("file")
    p.add_argument("--name")
    p.add_argument("--parent")
    p.set_defaults(func=lambda a: drive_upload(a.file, a.name, a.parent))

    p = sub.add_parser("cal", help="create Google Calendar event")
    p.add_argument("summary")
    p.add_argument("--desc")
    p.add_argument("--start", help="ISO 8601 datetime, e.g. 2026-11-15T10:00:00+03:00")
    p.add_argument("--end", help="ISO 8601 datetime")
    p.set_defaults(func=lambda a: calendar_create_event(
        a.summary, a.desc, a.start, a.end))

    args = parser.parse_args()
    result = args.func(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not result.get("error") else 1


if __name__ == "__main__":
    raise SystemExit(main())