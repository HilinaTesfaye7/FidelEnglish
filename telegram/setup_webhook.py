"""Connect Telegram to the bot's web app (webhook mode), or switch back to running on a computer.

On PythonAnywhere, in a Bash console:
    cd ~/fidel/telegram
    python3 setup_webhook.py https://YOURNAME.pythonanywhere.com
To go back to running bot.py on a computer (polling):
    python3 setup_webhook.py off
"""
import json, os, secrets, sys
HERE = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(HERE, "config.json")
sys.path.insert(0, HERE)
import bot

if len(sys.argv) != 2:
    sys.exit(__doc__)
arg = sys.argv[1].strip().rstrip("/")

if arg == "off":
    print("Webhook removed:", bot.api("deleteWebhook"))
    sys.exit(0)
if not arg.startswith("https://"):
    sys.exit("Give the full https:// address of your web app.")

cfg = json.load(open(CFG_PATH, encoding="utf-8"))
if not cfg.get("webhook_secret"):
    cfg["webhook_secret"] = secrets.token_urlsafe(24)
me = bot.api("getMe")
if not me:
    sys.exit("Could not reach Telegram. Check bot_token in config.json.")
cfg["bot_username"] = me["username"]
json.dump(cfg, open(CFG_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

ok = bot.api("setWebhook", url=arg + "/telegram", secret_token=cfg["webhook_secret"],
             allowed_updates=["message", "callback_query"], max_connections=1)
bot.api("setMyCommands", commands=[{"command": "start", "description": "Open the menu · ምናሌ"},
                                   {"command": "reminders_off", "description": "Stop daily reminders"}])
info = bot.api("getWebhookInfo") or {}
print("Webhook set:", ok, "| Telegram will send messages to:", info.get("url"))
print()
print("NOW: reload your web app (Web tab -> Reload), then send /start to @%s." % me["username"])
print("For reminders and the daily backup, add this link to cron-job.org, every 15 minutes:")
print("   %s/tick?key=%s" % (arg, cfg["webhook_secret"]))
print("(Keep that link private.)")
