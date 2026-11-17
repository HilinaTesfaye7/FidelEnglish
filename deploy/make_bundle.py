"""Make fidel-bot.zip: everything the server needs to run the bot.

Run on your computer, from the FidelEnglish folder, AFTER stopping the bot here (Ctrl + C):
    python deploy/make_bundle.py
Then upload deploy/fidel-bot.zip and deploy/setup_server.sh to the server.
The zip holds your bot token and student list: keep it private and never put it on GitHub.
"""
import json, os, sys, zipfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TG = os.path.join(ROOT, "telegram")
OUT = os.path.join(ROOT, "deploy", "fidel-bot.zip")

cfg = json.load(open(os.path.join(TG, "config.json"), encoding="utf-8"))
problems = []
if str(cfg.get("bot_token", "")).startswith("PASTE"): problems.append("bot_token is not filled in")
if not str(cfg.get("admin_id", "")).strip().isdigit(): problems.append("admin_id is not a number")
url = str(cfg.get("webapp_url", ""))
if not url.startswith("https://") or "PASTE" in url or "YOUR" in url: problems.append("webapp_url is not a real https link")
if problems:
    sys.exit("Fix config.json first: " + "; ".join(problems))

files = ["bot.py", "config.json"] + ["offline/" + f for f in sorted(os.listdir(os.path.join(TG, "offline"))) if f.endswith(".html")]
if os.path.exists(os.path.join(TG, "data.json")): files.append("data.json")
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for f in files:
        z.write(os.path.join(TG, f), "telegram/" + f)
users = len(json.load(open(os.path.join(TG, "data.json"), encoding="utf-8")).get("users", {})) if "data.json" in files else 0
print("Made %s (%d KB): %d files, %d people in the student list." % (os.path.relpath(OUT, ROOT), os.path.getsize(OUT) // 1024, len(files), users))
print("Course link in the bot: %s" % url)
print("AI tutor: %s" % ("ON" if cfg.get("tutor_enabled") else "OFF (coming soon)"))
