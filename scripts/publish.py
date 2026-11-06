#!/usr/bin/env python3
"""Publish reel.mp4 + caption.txt (from this commit) as an Instagram Reel.

Works with a Facebook Login token (EAA..., graph.facebook.com) or an\nInstagram Login token (IG..., graph.instagram.com). Meta fetches the
video from VIDEO_URL (public raw.githubusercontent.com URL of this commit).

Env: IG_ACCESS_TOKEN, IG_USER_ID, VIDEO_URL, DRY_RUN ("true" = stop before
media_publish), IG_API_VERSION (default v26.0), CAPTION_FILE (default caption.txt).
The access token is never printed.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = os.environ.get("IG_API_VERSION", "v26.0")
TOKEN = os.environ.get("IG_ACCESS_TOKEN", "").strip()
# EAA... = Facebook Login token (graph.facebook.com); IG... = Instagram Login token.
HOST = f"https://graph.{'facebook' if TOKEN.startswith('EAA') else 'instagram'}.com/{API}"
IG_ID = os.environ.get("IG_USER_ID", "").strip()
VIDEO_URL = os.environ["VIDEO_URL"]
DRY_RUN = os.environ.get("DRY_RUN", "").lower() == "true"
CAPTION_FILE = os.environ.get("CAPTION_FILE", "caption.txt")


def log(msg):
    print(msg, flush=True)


def fail(msg):
    # ::error:: makes the message visible as a check-run annotation.
    print(f"::error::{msg}", flush=True)
    summary(f"**Échec** : {msg}")
    sys.exit(1)


def summary(msg):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")


def call(method, path, params=None):
    url = f"{HOST}/{path}"
    data = None
    if method == "GET":
        if params:
            url += "?" + urllib.parse.urlencode(params)
    else:
        data = urllib.parse.urlencode(params or {}).encode()
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        fail(f"API error {e.code} on {method} {path.split('?')[0]}: {body[:800]}")


def wait_for_public_url():
    # raw.githubusercontent.com can lag a few seconds after a push.
    for attempt in range(12):
        try:
            req = urllib.request.Request(VIDEO_URL, method="HEAD")
            with urllib.request.urlopen(req, timeout=30) as r:
                size = int(r.headers.get("Content-Length", "0"))
                if r.status == 200 and size > 0:
                    log(f"Video reachable ({size / 1e6:.1f} MB): {VIDEO_URL}")
                    return
        except urllib.error.URLError as e:
            log(f"Video not reachable yet ({e}), retrying...")
        time.sleep(10)
    fail(f"Video URL never became reachable: {VIDEO_URL}")


def main():
    if not TOKEN or not IG_ID:
        fail("IG_ACCESS_TOKEN or IG_USER_ID secret is empty")
    if TOKEN[:1] in "\"'" or TOKEN.lower().startswith("bearer"):
        fail("IG_ACCESS_TOKEN contains quotes or a 'Bearer' prefix: paste the raw token only")
    if not TOKEN.startswith(("IG", "EAA")):
        fail(f"IG_ACCESS_TOKEN has an unexpected format ({len(TOKEN)} chars, starts with neither 'IG' nor 'EAA')")
    with open(CAPTION_FILE, encoding="utf-8") as f:
        caption = f.read().strip()
    if len(caption) > 2200:
        fail("Caption longer than 2200 characters")

    account = call("GET", IG_ID, {"fields": "username"})
    log(f"Publishing as @{account.get('username')} via {HOST.split('/')[2]}")

    wait_for_public_url()

    container = call("POST", f"{IG_ID}/media", {
        "media_type": "REELS",
        "video_url": VIDEO_URL,
        "caption": caption,
        "share_to_feed": "true",
    })["id"]
    log(f"Container created: {container}")

    # Meta suggests ~1 poll/min; reels usually finish in 30-120 s.
    status = "IN_PROGRESS"
    for _ in range(30):
        time.sleep(20)
        info = call("GET", container, {"fields": "status_code,status"})
        status = info.get("status_code")
        log(f"Container status: {status} {info.get('status', '')}")
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            fail(f"Container failed: {info}")
    else:
        fail(f"Container not ready after 10 minutes (last status {status})")

    if DRY_RUN:
        log("DRY RUN: container ready, NOT published.")
        summary("Test à blanc OK : vidéo acceptée et traitée par Meta, **non publiée**.")
        return

    media_id = call("POST", f"{IG_ID}/media_publish", {"creation_id": container})["id"]
    permalink = call("GET", media_id, {"fields": "permalink"}).get("permalink", "")
    log(f"Published: media {media_id} {permalink}")
    summary(f"Reel publié : {permalink or media_id}")


if __name__ == "__main__":
    main()
