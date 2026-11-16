"""Fidel English Telegram bot.

- New users get a 3-day free trial.
- Users pay with Telebirr and send a screenshot + transaction number.
- The owner approves or rejects each payment with one tap.
- Approved users get 30 days of the course (Mini App).
- Daily practice reminders and renewal reminders.

Needs only Python 3 (no extra packages). Settings are in config.json, user data in data.json.
Run:  python bot.py
"""
import json, os, sys, time, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "config.json"), encoding="utf-8"))
DATA_FILE = os.path.join(HERE, "data.json")
API = "https://api.telegram.org/bot%s/" % CFG["bot_token"]
ADMIN = int(CFG["admin_id"])
PRICE = int(CFG.get("price_basic", 300))
TRIAL_DAYS = int(CFG.get("trial_days", 3))
PLAN_DAYS = 30
REMIND_HOUR = int(CFG.get("reminder_hour", 19))       # Addis Ababa time
EAT = timezone(timedelta(hours=3))
DAY_MS = 86400000

def now_ms(): return int(time.time() * 1000)
def fmt_date(ms): return datetime.fromtimestamp(ms / 1000, EAT).strftime("%d %B %Y")

# ---------- storage ----------
def load():
    try:
        with open(DATA_FILE, encoding="utf-8") as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"users": {}, "payments": {}, "next_pay": 1}
DB = load()
def save():
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(DB, f, ensure_ascii=False, indent=1)
    os.replace(tmp, DATA_FILE)

# ---------- Telegram API ----------
def api(method, **params):
    body = json.dumps(params).encode("utf-8")
    req = urllib.request.Request(API + method, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r: return json.load(r).get("result")
    except urllib.error.HTTPError as e:
        print("API error", method, e.code, e.read()[:300], flush=True)
    except Exception as e:
        print("API problem", method, e, flush=True)
    return None

def send(chat, text, buttons=None, markup=None):
    p = {"chat_id": chat, "text": text, "parse_mode": "HTML"}
    if buttons: p["reply_markup"] = {"inline_keyboard": buttons}
    if markup: p["reply_markup"] = markup
    return api("sendMessage", **p)

BOT_USERNAME = None

# ---------- users ----------
def user(u):
    uid = str(u["id"])
    if uid not in DB["users"]:
        DB["users"][uid] = {"name": u.get("first_name", ""), "username": u.get("username", ""),
                            "joined": now_ms(), "trial_until": 0, "phone": None, "telegram_id": u["id"],
                            "plan": None, "until": 0, "state": None, "reminders": True,
                            "last_daily": "", "warned_for": 0, "ended_for": 0}
        save()
    return DB["users"][uid]

def access(us):
    """Returns (kind, until) — kind is 'basic', 'trial' or None."""
    t = now_ms()
    if us.get("plan") and us.get("until", 0) > t: return us["plan"], us["until"]
    if us.get("trial_until", 0) > t: return "trial", us["trial_until"]
    return None, 0

def course_button(us):
    kind, until = access(us)
    q = {"p": kind or "trial", "u": until or 1, "b": BOT_USERNAME or ""}
    url = CFG["webapp_url"].rstrip("/") + "/?" + urllib.parse.urlencode(q)
    return [{"text": "📚 Open course · ትምህርቱን ክፈት", "web_app": {"url": url}}]

def main_menu(chat, us):
    kind, until = access(us)
    if kind == "trial":
        status = "🎁 Free trial until <b>%s</b>\nነፃ ሙከራ እስከ %s" % (fmt_date(until), fmt_date(until))
    elif kind:
        status = "✅ Your plan is active until <b>%s</b>\nዕቅድዎ እስከ %s ይሰራል" % (fmt_date(until), fmt_date(until))
    else:
        status = "🔒 Your free trial has ended. Subscribe to continue.\nነፃ ሙከራዎ አልቋል። ለመቀጠል ይመዝገቡ።"
    rows = [course_button(us)] if kind else []
    rows.append([{"text": "💳 Subscribe · ይመዝገቡ", "callback_data": "sub"}, {"text": "❓ Help · እርዳታ", "callback_data": "help"}])
    send(chat, "🦁 <b>Selam %s! Welcome to Fidel English.</b>\nሰላም! እንኳን ወደ ፊደል ኢንግሊሽ በደህና መጡ።\n\n%s" % (esc(us["name"]), status), rows)

def esc(t): return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def show_plans(chat):
    send(chat, "Choose your plan · ዕቅድዎን ይምረጡ\n\n"
               "📘 <b>Basic — %d Birr / month</b>\nAll 51 lessons, quizzes, speaking and pronunciation.\nሁሉም ትምህርቶች፣ ፈተናዎችና የመናገር ልምምድ።\n\n"
               "🤖 <b>Premium + AI tutor — 1000 Birr / month</b>\nComing soon · በቅርቡ ይመጣል" % PRICE,
         [[{"text": "📘 Basic · %d Birr" % PRICE, "callback_data": "plan:basic"}]])

def pay_instructions(chat, us):
    us["state"] = "proof"; save()
    send(chat, "1️⃣ Send <b>%d Birr</b> with Telebirr to:\n📱 <b>%s</b> (%s)\n\n"
               "2️⃣ Then send the <b>screenshot</b> here, and write the <b>transaction number</b> under the photo.\n\n"
               "1️⃣ %d ብር በቴሌብር ወደ %s (%s) ይላኩ።\n2️⃣ ከዚያ ስክሪንሾቱን እዚህ ይላኩ፣ የግብይት ቁጥሩንም ይጻፉ።"
         % (PRICE, esc(CFG["telebirr_number"]), esc(CFG["telebirr_name"]), PRICE, esc(CFG["telebirr_number"]), esc(CFG["telebirr_name"])))

# ---------- payments ----------
def new_payment(uid, us, photo, txn):
    pid = str(DB["next_pay"]); DB["next_pay"] += 1
    DB["payments"][pid] = {"uid": uid, "photo": photo, "txn": txn, "plan": "basic", "status": "waiting", "at": now_ms()}
    us["state"] = None; save()
    send(int(uid), "🙏 Thank you! We are checking your payment. This usually takes less than 1 hour.\nእናመሰግናለን! ክፍያዎን እያረጋገጥን ነው።")
    cap = ("💰 <b>New payment #%s</b>\nName: %s%s\nPhone: %s\nTelegram ID: %s\nPlan: Basic · %d Birr\nTransaction: <b>%s</b>\n\n"
           "⚠️ Check your Telebirr SMS for this transaction number before approving."
           % (pid, esc(us["name"]), (" (@%s)" % esc(us["username"])) if us.get("username") else "", esc(us.get("phone") or "-"), uid, PRICE, esc(txn)))
    kb = {"inline_keyboard": [[{"text": "✅ Approve", "callback_data": "ok:" + pid}, {"text": "❌ Reject", "callback_data": "no:" + pid}]]}
    api("sendPhoto", chat_id=ADMIN, photo=photo, caption=cap, parse_mode="HTML", reply_markup=kb)

def decide(pid, ok, cb):
    p = DB["payments"].get(pid)
    if not p or p["status"] != "waiting":
        api("answerCallbackQuery", callback_query_id=cb["id"], text="Already handled"); return
    us = DB["users"][p["uid"]]
    if ok:
        start = max(now_ms(), us.get("until", 0))
        us["plan"], us["until"] = "basic", start + PLAN_DAYS * DAY_MS
        p["status"] = "approved"; save()
        send(int(p["uid"]), "🎉 <b>Payment confirmed!</b> Your Basic plan is active until <b>%s</b>.\nክፍያዎ ተረጋግጧል! ዕቅድዎ እስከ %s ይሰራል።"
             % (fmt_date(us["until"]), fmt_date(us["until"])), [course_button(us)])
        result = "✅ Approved — %s until %s" % (esc(us["name"]), fmt_date(us["until"]))
    else:
        p["status"] = "rejected"; save()
        send(int(p["uid"]), "😕 We could not confirm your payment. Please check the transaction number and send again.\nክፍያዎን ማረጋገጥ አልቻልንም። እባክዎ እንደገና ይላኩ።",
             [[{"text": "💳 Try again · እንደገና", "callback_data": "plan:basic"}]])
        result = "❌ Rejected"
    api("answerCallbackQuery", callback_query_id=cb["id"], text=result[:190])
    msg = cb["message"]
    api("editMessageCaption", chat_id=msg["chat"]["id"], message_id=msg["message_id"],
        caption=(msg.get("caption") or "") + "\n\n" + result, parse_mode="HTML")

def ask_phone(chat):
    send(chat, "🦁 <b>Welcome to Fidel English!</b>\nእንኳን ወደ ፊደል ኢንግሊሽ በደህና መጡ!\n\n"
               "To start your <b>3-day free trial</b>, tap the button below to share your phone number.\n"
               "የ3 ቀን ነፃ ሙከራ ለመጀመር ከታች ያለውን ቁልፍ ተጭነው ስልክ ቁጥርዎን ያጋሩ።",
         markup={"keyboard": [[{"text": "📱 Share my phone · ስልኬን አጋራ", "request_contact": True}]],
                 "resize_keyboard": True, "one_time_keyboard": True})

def on_contact(chat, uid, us, c):
    if str(c.get("user_id")) != uid:
        send(chat, "Please share <b>your own</b> number with the button · እባክዎ የራስዎን ቁጥር ያጋሩ"); ask_phone(chat); return
    first = not us.get("phone")
    us["phone"] = "+" + c["phone_number"].lstrip("+")
    if first: us["trial_until"] = now_ms() + TRIAL_DAYS * DAY_MS
    save()
    send(chat, "✅ Thank you! Your account is ready.\nአመሰግናለሁ! መለያዎ ዝግጁ ነው።", markup={"remove_keyboard": True})
    main_menu(chat, us)

# ---------- handlers ----------
def on_message(m):
    chat = m["chat"]["id"]
    if m["chat"].get("type") != "private": return
    us = user(m["from"]); uid = str(m["from"]["id"])
    text = (m.get("text") or "").strip()
    if m.get("contact"): on_contact(chat, uid, us, m["contact"]); return
    if not us.get("phone") and int(uid) != ADMIN: ask_phone(chat); return
    if text.startswith("/start"):
        arg = text[6:].strip()
        if arg in ("basic", "premium", "pay"): show_plans(chat)
        else: main_menu(chat, us)
        return
    if text == "/stats" and int(uid) == ADMIN: stats(chat); return
    if text in ("/stop", "/reminders_off"):
        us["reminders"] = False; save(); send(chat, "🔕 Reminders are off. Send /reminders_on to turn them on."); return
    if text == "/reminders_on":
        us["reminders"] = True; save(); send(chat, "🔔 Reminders are on."); return
    if m.get("photo"):
        photo = m["photo"][-1]["file_id"]
        txn = (m.get("caption") or "").strip()
        if txn: new_payment(uid, us, photo, txn)
        else:
            us["state"], us["photo"] = "txn", photo; save()
            send(chat, "👍 Got the screenshot. Now type the <b>transaction number</b>.\nአሁን የግብይት ቁጥሩን ይጻፉ።")
        return
    if us.get("state") == "txn" and text:
        new_payment(uid, us, us.pop("photo"), text); return
    if us.get("state") == "proof" and text:
        send(chat, "📸 Please send the <b>screenshot</b> of your Telebirr payment first.\nእባክዎ መጀመሪያ ስክሪንሾቱን ይላኩ።"); return
    main_menu(chat, us)

def on_callback(cb):
    data = cb.get("data", ""); chat = cb["message"]["chat"]["id"]
    us = user(cb["from"])
    if data.startswith(("ok:", "no:")):
        if cb["from"]["id"] != ADMIN: return
        decide(data[3:], data.startswith("ok:"), cb); return
    api("answerCallbackQuery", callback_query_id=cb["id"])
    if not us.get("phone"): ask_phone(chat); return
    if data == "sub": show_plans(chat)
    elif data == "plan:basic": pay_instructions(chat, us)
    elif data == "help":
        send(chat, "❓ <b>Help</b>\n• Tap 📚 Open course to learn.\n• To pay: 💳 Subscribe → Basic → pay with Telebirr → send the screenshot.\n• /reminders_off — stop daily reminders\n\nQuestions? Write to %s" % esc(CFG.get("support_contact", "the owner")))

def stats(chat):
    t = now_ms(); us = [u for k, u in DB["users"].items() if int(k) != ADMIN]
    active = sum(1 for u in us if u.get("plan") and u.get("until", 0) > t)
    trial = sum(1 for u in us if not (u.get("plan") and u.get("until", 0) > t) and u.get("trial_until", 0) > t)
    waiting = sum(1 for p in DB["payments"].values() if p["status"] == "waiting")
    month = sum(PRICE for p in DB["payments"].values() if p["status"] == "approved" and t - p["at"] < 30 * DAY_MS)
    send(chat, "📊 <b>Stats</b>\nUsers: %d\nPaying now: %d\nIn trial: %d\nWaiting for approval: %d\nApproved in last 30 days: %d Birr"
         % (len(us), active, trial, waiting, month))

# ---------- reminders ----------
def reminders():
    now = datetime.now(EAT); today = now.strftime("%Y-%m-%d"); t = now_ms(); changed = False
    for uid, us in DB["users"].items():
        if not us.get("phone"): continue
        kind, until = access(us)
        if us.get("plan") and us.get("until", 0):
            left = us["until"] - t
            if 0 < left < 3 * DAY_MS and us.get("warned_for") != us["until"]:
                us["warned_for"] = us["until"]; changed = True
                send(int(uid), "⏰ Your plan ends on <b>%s</b>. Renew to keep learning.\nዕቅድዎ %s ያልቃል። ለመቀጠል ያድሱ።" % (fmt_date(us["until"]), fmt_date(us["until"])),
                     [[{"text": "💳 Renew · %d Birr" % PRICE, "callback_data": "plan:basic"}]])
            elif left <= 0 and us.get("ended_for") != us["until"]:
                us["ended_for"] = us["until"]; changed = True
                send(int(uid), "🔒 Your plan has ended. Renew to continue learning.\nዕቅድዎ አልቋል።", [[{"text": "💳 Renew · %d Birr" % PRICE, "callback_data": "plan:basic"}]])
        elif not us.get("plan") and us.get("trial_until", 0) <= t and not us.get("trial_end_sent"):
            us["trial_end_sent"] = True; changed = True
            send(int(uid), "🔒 Your 3-day free trial has ended. Subscribe for %d Birr / month to keep learning.\nየ3 ቀን ነፃ ሙከራዎ አልቋል።" % PRICE,
                 [[{"text": "💳 Subscribe · %d Birr" % PRICE, "callback_data": "plan:basic"}]])
        if kind and us.get("reminders", True) and now.hour >= REMIND_HOUR and us.get("last_daily") != today:
            us["last_daily"] = today; changed = True
            send(int(uid), "🦁 It's English time, %s! Your lesson is waiting.\nየእንግሊዝኛ ሰዓት ደርሷል!" % esc(us["name"]), [course_button(us)])
    if changed: save()

# ---------- main loop ----------
def main():
    global BOT_USERNAME
    me = api("getMe")
    if not me: print("Could not connect. Check bot_token in config.json."); sys.exit(1)
    BOT_USERNAME = me["username"]
    api("setMyCommands", commands=[{"command": "start", "description": "Open the menu · ምናሌ"},
                                   {"command": "reminders_off", "description": "Stop daily reminders"}])
    print("Bot @%s is running. Press Ctrl+C to stop." % BOT_USERNAME, flush=True)
    offset, last_check = None, 0
    while True:
        p = {"timeout": 25, "allowed_updates": ["message", "callback_query"]}
        if offset: p["offset"] = offset
        updates = api("getUpdates", **p) or []
        for up in updates:
            offset = up["update_id"] + 1
            try:
                if "message" in up: on_message(up["message"])
                elif "callback_query" in up: on_callback(up["callback_query"])
            except Exception as e:
                print("Error:", e, flush=True)
        if time.time() - last_check > 60:
            last_check = time.time()
            try: reminders()
            except Exception as e: print("Reminder error:", e, flush=True)
        if not updates: time.sleep(1)

if __name__ == "__main__":
    main()
