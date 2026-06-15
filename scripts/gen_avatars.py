"""Generate age/gender-matched AI portraits for the org-chart agents.

Reads OPENAI_API_KEY from the shared env file, calls gpt-image-1, and writes
JPEGs to website/public/avatars/<slug>.jpg. Resumable: a slug whose .jpg was
already (re)generated this run is skipped via a .done marker. Run again with
no args to fill in whatever is still missing.

Usage:
  python scripts/gen_avatars.py            # generate all that aren't done yet
  python scripts/gen_avatars.py omri dafna # only these slugs (force regenerate)
"""

import base64
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

SHARED_ENV = Path(os.environ.get("TAKT_SHARED_ENV", r"C:\Users\User\Aiprojects\env\.env"))
OUT_DIR = Path(__file__).resolve().parent.parent / "website" / "public" / "avatars"
API_URL = "https://api.openai.com/v1/images/generations"

STYLE = (
    "Professional corporate headshot portrait photograph of a single Israeli "
    "tech-company {who}. {desc}. Friendly, approachable, looking at the camera, "
    "natural soft studio lighting, plain softly-blurred warm neutral background, "
    "shoulders-up framing, sharp focus, photorealistic, high detail, no text."
)

# slug -> (who, descriptive prompt). VPs read ~40-50, employees ~30-40.
AGENTS = {
    # ── הנהלה / VPs (~40-50) ──
    "ceo":            ("man",   "a distinguished man in his early 50s, short neatly-styled greying hair, confident warm smile, dark tailored blazer over a shirt"),
    "cfo":            ("man",   "a man in his late 40s, short hair, thin-framed glasses, composed trustworthy expression, button-up shirt and blazer"),
    "coo":            ("man",   "a man in his late 40s, short dark hair, calm confident expression, crisp business shirt"),
    "ronit":          ("woman", "a woman in her mid 40s, shoulder-length styled hair, warm confident professional smile, elegant blazer"),
    "yuval":          ("man",   "a man in his late 40s, short hair with light stubble, approachable assured smile, smart-casual collared shirt"),
    "amir":           ("man",   "a man in his late 40s, short hair, modern glasses, thoughtful professional expression, dark blazer"),
    "control-center": ("man",   "a man in his mid 40s, short hair, attentive focused expression, business-casual shirt"),
    "saas":           ("man",   "a man in his mid 40s, short modern haircut, relaxed tech-executive look, smart-casual shirt"),
    # ── סוכנים / עוזרים (~30-40) ──
    "ran":            ("man",   "a man in his mid 30s, short tidy hair, friendly helpful expression, casual collared shirt"),
    "leads":          ("man",   "a man in his late 30s, short hair, energetic friendly smile, casual button-up shirt"),
    "yaron":          ("man",   "a man in his early 30s, short hair with light stubble, easygoing friendly smile, casual shirt"),
    "guy":            ("man",   "a man in his mid 30s, short hair, warm welcoming smile, casual polo shirt"),
    "zubin":          ("man",   "a man in his late 30s, short dark hair, calm thoughtful expression, casual shirt"),
    "email-summary":  ("man",   "a man in his early 30s, short neat hair, friendly organized look, casual collared shirt"),
    "omri":           ("man",   "a man in his early 30s, short hair, cheerful upbeat expression, casual shirt"),
    "dafna":          ("woman", "a woman in her mid 30s, shoulder-length hair, bright friendly smile, casual blouse"),
    "dror":           ("man",   "a man in his late 30s, short hair, slim glasses, friendly professional expression, casual shirt"),
}


def load_key():
    for line in SHARED_ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("OPENAI_API_KEY=") and not line.startswith("#"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(f"OPENAI_API_KEY not found in {SHARED_ENV}")


def generate(slug, who, desc, key):
    body = json.dumps({
        "model": "gpt-image-1",
        "prompt": STYLE.format(who=who, desc=desc),
        "size": "1024x1024",
        "quality": "medium",
        "output_format": "jpeg",
        "n": 1,
    }).encode("utf-8")
    req = urllib.request.Request(
        API_URL, data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
    img = base64.b64decode(data["data"][0]["b64_json"])
    (OUT_DIR / f"{slug}.jpg").write_bytes(img)
    (OUT_DIR / f"{slug}.done").write_text("ok", encoding="utf-8")


def main():
    key = load_key()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    wanted = sys.argv[1:] or list(AGENTS)
    forced = bool(sys.argv[1:])
    todo = [s for s in wanted if forced or not (OUT_DIR / f"{s}.done").exists()]
    print(f"{len(todo)} to generate: {', '.join(todo) or '(none)'}", flush=True)
    for i, slug in enumerate(todo, 1):
        who, desc = AGENTS[slug]
        t0 = time.time()
        try:
            generate(slug, who, desc, key)
            print(f"[{i}/{len(todo)}] {slug:16} ok  ({time.time()-t0:.0f}s)", flush=True)
        except Exception as e:  # noqa: BLE001 — keep going, report at end
            print(f"[{i}/{len(todo)}] {slug:16} FAIL  {e}", flush=True)
    print("done.", flush=True)


if __name__ == "__main__":
    main()
