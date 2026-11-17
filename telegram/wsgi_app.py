"""Fidel English bot as a small web app (webhook mode), for free hosts like PythonAnywhere.

Telegram sends every message to  https://<your-site>/telegram
cron-job.org opens            https://<your-site>/tick?key=<webhook_secret>  every 15 minutes
                              (daily reminders, trial and renewal messages, daily backup)
Uses only Python's standard library.
"""
import hmac, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bot

SECRET = str(bot.CFG.get("webhook_secret", ""))

def _reply(start_response, status, text):
    body = text.encode("utf-8")
    start_response(status, [("Content-Type", "text/plain; charset=utf-8"), ("Content-Length", str(len(body)))])
    return [body]

def _same(a, b):
    return bool(SECRET) and hmac.compare_digest(str(a or ""), str(b or ""))

def application(environ, start_response):
    path = environ.get("PATH_INFO", "")
    method = environ.get("REQUEST_METHOD", "GET")
    if path == "/telegram" and method == "POST":
        # only Telegram knows the secret it was given in setWebhook
        if not _same(environ.get("HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN"), SECRET):
            return _reply(start_response, "403 Forbidden", "no")
        try:
            size = int(environ.get("CONTENT_LENGTH") or 0)
            update = json.loads(environ["wsgi.input"].read(size).decode("utf-8"))
        except Exception:
            return _reply(start_response, "400 Bad Request", "bad update")
        bot.ensure_username()
        bot.handle_update(update)
        bot.tick(min_gap=600)
        return _reply(start_response, "200 OK", "ok")
    if path == "/tick":
        from urllib.parse import parse_qs
        key = parse_qs(environ.get("QUERY_STRING", "")).get("key", [""])[0]
        if not _same(key, SECRET):
            return _reply(start_response, "403 Forbidden", "no")
        bot.ensure_username()
        bot.tick(min_gap=0)
        return _reply(start_response, "200 OK", "tick done")
    return _reply(start_response, "200 OK", "Fidel English bot is running.")
