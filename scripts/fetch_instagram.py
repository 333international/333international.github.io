import os
import json
import pathlib
import requests
from datetime import datetime

# 1. read token from env (we’ll set it in GitHub Secrets)
ACCESS_TOKEN = os.environ["IG_ACCESS_TOKEN"]

# 2. folder where we store media + metadata
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
MEDIA_DIR = BASE_DIR / "instagram"
MEDIA_DIR.mkdir(exist_ok=True)

# 3. call Instagram
url = (
    "https://graph.instagram.com/me/media"
    "?fields=id,caption,media_type,media_url,thumbnail_url,permalink,timestamp"
    f"&access_token={ACCESS_TOKEN}"
)

resp = requests.get(url, timeout=20)
resp.raise_for_status()
data = resp.json()

# 4. load existing index (to avoid re-downloading)
index_file = MEDIA_DIR / "index.json"
if index_file.exists():
    existing = json.loads(index_file.read_text())
    known_ids = {item["id"] for item in existing}
else:
    existing = []
    known_ids = set()

new_items = []

for item in data.get("data", []):
    ig_id = item["id"]
    if ig_id in known_ids:
        continue  # already downloaded

    media_url = item.get("media_url")
    media_type = item.get("media_type")
    ts = item.get("timestamp")

    # figure out filename
    ext = ".jpg"
    if media_type == "VIDEO":
        ext = ".mp4"
    filename = f"{ig_id}{ext}"
    filepath = MEDIA_DIR / filename

    # download the file
    if media_url:
        r = requests.get(media_url, timeout=30)
        r.raise_for_status()
        with open(filepath, "wb") as f:
            f.write(r.content)

    # store metadata
    item_record = {
        "id": ig_id,
        "filename": filename,
        "caption": item.get("caption", ""),
        "permalink": item.get("permalink"),
        "timestamp": ts,
        "media_type": media_type,
        "saved_at": datetime.utcnow().isoformat() + "Z",
    }
    existing.append(item_record)
    new_items.append(item_record)

# write back index
index_file.write_text(json.dumps(existing, indent=2))

print(f"Fetched {len(new_items)} new posts.")
