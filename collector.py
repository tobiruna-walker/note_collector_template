import os, time, json, requests, hmac, hashlib

NOTE_BASE   = "https://note.com"
COOKIE      = os.environ["NOTE_COOKIE"]     # "_note_session_v5=...; XSRF-TOKEN=..."
XSRF        = os.environ["NOTE_XSRF"]       # "abcd1234"
INGEST_URL  = os.environ["INGEST_URL"]      # "https://YOURDOMAIN/wp-json/note-stats/v1/ingest"
API_KEY     = os.environ["API_KEY"]         # WPプロフィールで設定した秘密キー

def fetch_page(page=1):
  h = {"Cookie": COOKIE, "X-XSRF-TOKEN": XSRF, "User-Agent": "Mozilla/5.0", "Accept": "application/json"}
  r = requests.get(f"{NOTE_BASE}/api/v1/stats/pv?filter=all&page={page}&sort=pv", headers=h, timeout=20)
  r.raise_for_status(); return r.json()

def collect():
  rows, p = [], 1
  while True:
    js = fetch_page(p)
    items = js.get("data") or js.get("notes") or []
    if not items: break
    for it in items:
      rows.append({
        "note_id": str(it.get("id") or it.get("note_id")),
        "title":   it.get("name") or it.get("title") or "",
        "pv":      int(it.get("pv") or it.get("view_count") or 0),
        "likes":   int(it.get("likes") or it.get("like_count") or 0),
        "comments":int(it.get("comments") or it.get("comment_count") or 0),
      })
    if not (js.get("has_more") or js.get("next_page")): break
    p += 1; time.sleep(0.5)
  return rows[:500]

def sign_and_post(rows):
  payload = {"rows": rows}
  raw = json.dumps(payload, separators=(',',':'), ensure_ascii=False)
  ts  = str(int(time.time()))
  sig = hmac.new(API_KEY.encode(), (ts+"\n"+raw).encode(), hashlib.sha256).hexdigest()
  r = requests.post(INGEST_URL, data=raw.encode('utf-8'),
                    headers={"Content-Type":"application/json",
                             "X-Api-Key":API_KEY, "X-Timestamp":ts, "X-Signature":sig},
                    timeout=30)
  r.raise_for_status()
  print("ingested:", len(rows))

if __name__ == "__main__":
  sign_and_post(collect())
