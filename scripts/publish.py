#!/usr/bin/env python3
"""Publish reel.mp4 + caption.txt (from this commit) as an Instagram Reel.

Instagram API with Instagram Login (graph.instagram.com). Meta fetches the
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
HOST = f"https://graph.instagram.com/{API}"
TOKEN = os.environ["IG_ACCESS_TOKEN"]
IG_ID = os.environ["IG_USER_ID"]
VIDEO_URL = os.environ["VIDEO_URL"]
DRY_RUN = os.environ.get("DRY_RUN", "").lower() == "true"
CAPTION_FILE = os.environ.get("CAPTION_FILE", "caption.txt")


def log(msg):
    print(msg, flush=True)


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
        summary(f"**Erreur API {e.code}** sur `{method} {path}` : `{body}`")
        sys.exit(f"API error {e.code} on {method} {path}: {body}")


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
    sys.exit(f"Video URL never became reachable: {VIDEO_URL}")


def main():
    with open(CAPTION_FILE, encoding="utf-8") as f:
        caption = f.read().strip()
    if len(caption) > 2200:
        sys.exit("Caption longer than 2200 characters")

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
            summary(f"**Traitement Meta en échec** : `{info}`")
            sys.exit(f"Container failed: {info}")
    else:
        sys.exit(f"Container not ready after 10 minutes (last status {status})")

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
