"""Fidel English Telegram bot — 4-month course.

- New users share their phone (saved with their Telegram ID) and get a 3-day free trial of Month 1.
- Each payment (default 300 Birr) opens the next month. The full course (default 1000 Birr) opens all 4.
- Opened months stay open forever.
- Users pay with Telebirr and send a screenshot + transaction number; the owner approves with one tap.
- Daily practice reminders, and a "next month is ready" reminder 25 days after each payment.

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
PRICE = int(CFG.get("price_month", CFG.get("price_basic", 300)))   # one month
PRICE_FULL = int(CFG.get("price_full", 1000))                      # all 4 months at once
PRICE_PREMIUM = int(CFG.get("price_premium", 1000))                # AI tutor: shown only, can't be bought yet
TRIAL_DAYS = int(CFG.get("trial_days", 3))
MONTHS = 4
NUDGE_DAYS = 25
REMIND_HOUR = int(CFG.get("reminder_hour", 19))                    # Addis Ababa time
EAT = timezone(timedelta(hours=3))
DAY_MS = 86400000
MONTH_NAMES = {1: "Month 1 · Beginner", 2: "Month 2 · Intermediate", 3: "Month 3 · Advanced", 4: "Month 4 · Real-life words, final exam + certificate"}
MONTH_AM = {1: "ወር 1 · ጀማሪ", 2: "ወር 2 · መካከለኛ", 3: "ወር 3 · ከፍተኛ", 4: "ወር 4 · የዕለት ቃላት፣ ፈተናና ሰርተፊኬት"}

def now_ms(): return int(time.time() * 1000)
def fmt_date(ms): return datetime.fromtimestamp(ms / 1000, EAT).strftime("%d %B %Y")
def esc(t): return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

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

def api_file(method, fields, file_field, filename, content):
    """Upload a file (multipart/form-data)."""
    boundary = "----FidelEnglish%d" % int(time.time() * 1000)
    parts = []
    for k, v in fields.items():
        parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (boundary, k, v)).encode("utf-8"))
    parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"; filename="%s"\r\nContent-Type: text/html\r\n\r\n'
                  % (boundary, file_field, filename)).encode("utf-8") + content + b"\r\n")
    parts.append(("--%s--\r\n" % boundary).encode("utf-8"))
    req = urllib.request.Request(API + method, data=b"".join(parts),
                                 headers={"Content-Type": "multipart/form-data; boundary=" + boundary})
    try:
        with urllib.request.urlopen(req, timeout=120) as r: return json.load(r).get("result")
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
                            "months": 0, "last_paid": 0, "nudged_for": 0, "state": None, "reminders": True,
                            "last_daily": ""}
        save()
    us = DB["users"][uid]
    if "months" not in us:                       # users from the old monthly-plan version
        us["months"] = 1 if us.get("plan") else 0
    return us

def months_open(us): return max(0, min(MONTHS, int(us.get("months", 0))))
def in_trial(us): return us.get("trial_until", 0) > now_ms()
def has_access(us): return months_open(us) > 0 or in_trial(us)

def course_button(us):
    q = {"m": months_open(us), "t": us.get("trial_until", 0) if in_trial(us) else 0, "b": BOT_USERNAME or ""}
    url = CFG["webapp_url"].rstrip("/") + "/?" + urllib.parse.urlencode(q)
    return [{"text": "📚 Open course · ትምህርቱን ክፈት", "web_app": {"url": url}}]

DOWNLOAD_BTN = {"text": "📥 Download course · ኮርሱን አውርድ", "callback_data": "dl"}

def learn_buttons(us):
    """Learn in Telegram, and (for paid months) download the course to learn without internet."""
    rows = [course_button(us)]
    if months_open(us) > 0: rows.append([DOWNLOAD_BTN])
    return rows

def send_course_file(chat, us):
    n = months_open(us)
    if n == 0:
        send(chat, "📥 The download is for paid months. Pay to open Month 1 first.\nማውረድ የሚቻለው ለተከፈሉ ወራት ነው።",
             [[{"text": "💳 Pay · ይክፈሉ", "callback_data": "sub"}]]); return
    path = os.path.join(HERE, "offline", "month%d.html" % n)
    try:
        html = open(path, encoding="utf-8").read()
    except FileNotFoundError:
        send(chat, "Sorry, the download is not ready yet. Please learn in Telegram for now."); print("Missing", path, flush=True); return
    lic = {"name": us.get("name", ""), "phone": us.get("phone") or "", "months": n, "bot": BOT_USERNAME or ""}
    html = html.replace('"__FIDEL_LICENSE__"', json.dumps(lic, ensure_ascii=False).replace("</", "<\\/"), 1)
    api("sendChatAction", chat_id=chat, action="upload_document")
    name = "Fidel-English-Month-1.html" if n == 1 else "Fidel-English-Months-1-%d.html" % n
    caption = ("📥 <b>Your Fidel English course — %s</b>\n\n"
               "How to use it:\n1️⃣ Tap the file to download it.\n2️⃣ Open it with <b>Chrome</b>.\n"
               "3️⃣ Learn anywhere, even without internet. 🦁\n\n"
               "When you open a new month, tap 📥 Download course again.\n"
               "This copy has your name on it. Please don't share it.\n\n"
               "ፋይሉን አውርደው በ Chrome ይክፈቱ። ያለ ኢንተርኔት መማር ይችላሉ።"
               % ("Month 1" if n == 1 else "Months 1–%d" % n))
    ok = api_file("sendDocument", {"chat_id": chat, "caption": caption, "parse_mode": "HTML"}, "document", name, html.encode("utf-8"))
    if not ok: send(chat, "Sorry, the file could not be sent. Please try again later.\nይቅርታ፣ እባክዎ ቆይተው እንደገና ይሞክሩ።")

def main_menu(chat, us):
    n = months_open(us)
    if n >= MONTHS:
        status = "🎓 You have the <b>full course</b> (all 4 months).\nሙሉውን ኮርስ ከፍተዋል።"
    elif n:
        status = "✅ <b>%d of 4 months</b> open. Next: %s\n%d/4 ወራት ተከፍተዋል።" % (n, MONTH_NAMES[n + 1], n)
    elif in_trial(us):
        status = "🎁 Free trial (Month 1) until <b>%s</b>\nነፃ ሙከራ (ወር 1) እስከ %s" % (fmt_date(us["trial_until"]), fmt_date(us["trial_until"]))
    else:
        status = "🔒 Your free trial has ended. Pay to open Month 1.\nነፃ ሙከራዎ አልቋል። ወር 1ን ለመክፈት ይክፈሉ።"
    rows = learn_buttons(us) if has_access(us) else []
    if n < MONTHS:
        rows.append([{"text": "💳 Pay · ይክፈሉ", "callback_data": "sub"}, {"text": "❓ Help · እርዳታ", "callback_data": "help"}])
    else:
        rows.append([{"text": "❓ Help · እርዳታ", "callback_data": "help"}])
    send(chat, "🦁 <b>Selam %s! Welcome to Fidel English.</b>\nሰላም! እንኳን ወደ ፊደል ኢንግሊሽ በደህና መጡ።\n\n%s" % (esc(us["name"]), status), rows)

def show_plans(chat, us):
    n = months_open(us)
    if n >= MONTHS:
        send(chat, "🎓 You already have the full course! · ሙሉውን ኮርስ ከፍተዋል!", learn_buttons(us)); return
    text = ("📚 <b>Fidel English — 4-month course</b>\n"
            "Month 1 Beginner · Month 2 Intermediate · Month 3 Advanced · Month 4 Real-life words, final exam + certificate 🎓\n\n"
            "📘 <b>Open %s — %d Birr</b>\nYours forever once opened. Finished early? Open the next month any time.\n"
            "%s — %d ብር። አንዴ ከተከፈተ ለዘላለም የእርስዎ ነው።" % (MONTH_NAMES[n + 1], PRICE, MONTH_AM[n + 1], PRICE))
    rows = [[{"text": "📘 %s · %d Birr" % (MONTH_NAMES[n + 1].split(" · ")[0], PRICE), "callback_data": "plan:month"}]]
    if n == 0:
        text += ("\n\n🎓 <b>Full course, all 4 months — %d Birr</b> (save %d Birr)\nሙሉ ኮርስ፣ 4 ወራት — %d ብር"
                 % (PRICE_FULL, PRICE * MONTHS - PRICE_FULL, PRICE_FULL))
        rows.append([{"text": "🎓 Full course · %d Birr" % PRICE_FULL, "callback_data": "plan:full"}])
    text += "\n\n🤖 AI tutor (%d Birr / month) — coming soon · በቅርቡ ይመጣል" % PRICE_PREMIUM
    send(chat, text, rows)

def plan_info(us, plan):
    """(amount, label) for a plan the user is buying now."""
    if plan == "full": return PRICE_FULL, "Full course (all 4 months)"
    return PRICE, MONTH_NAMES[min(MONTHS, months_open(us) + 1)]

def pay_instructions(chat, us, plan):
    if months_open(us) >= MONTHS:
        send(chat, "🎓 You already have the full course! · ሙሉውን ኮርስ ከፍተዋል!"); return
    if plan == "full" and months_open(us) > 0: plan = "month"
    amount, label = plan_info(us, plan)
    us["state"], us["pay_plan"] = "proof", plan; save()
    send(chat, "🧾 <b>%s — %d Birr</b>\n\n"
               "1️⃣ Send <b>%d Birr</b> with Telebirr to:\n📱 <b>%s</b> (%s)\n\n"
               "2️⃣ Then send the <b>screenshot</b> here, and write the <b>transaction number</b> under the photo.\n\n"
               "1️⃣ %d ብር በቴሌብር ወደ %s (%s) ይላኩ።\n2️⃣ ከዚያ ስክሪንሾቱን እዚህ ይላኩ፣ የግብይት ቁጥሩንም ይጻፉ።"
         % (esc(label), amount, amount, esc(CFG["telebirr_number"]), esc(CFG["telebirr_name"]),
            amount, esc(CFG["telebirr_number"]), esc(CFG["telebirr_name"])))

# ---------- payments ----------
def new_payment(uid, us, photo, txn):
    plan = us.get("pay_plan") or "month"
    amount, label = plan_info(us, plan)
    pid = str(DB["next_pay"]); DB["next_pay"] += 1
    DB["payments"][pid] = {"uid": uid, "photo": photo, "txn": txn, "plan": plan, "amount": amount,
                           "label": label, "status": "waiting", "at": now_ms()}
    us["state"] = None; save()
    send(int(uid), "🙏 Thank you! We are checking your payment. This usually takes less than 1 hour.\nእናመሰግናለን! ክፍያዎን እያረጋገጥን ነው።")
    cap = ("💰 <b>New payment #%s</b>\nName: %s%s\nPhone: %s\nTelegram ID: %s\nBuying: <b>%s · %d Birr</b>\nMonths open now: %d of 4\nTransaction: <b>%s</b>\n\n"
           "⚠️ Check your Telebirr SMS for this transaction number and amount before approving."
           % (pid, esc(us["name"]), (" (@%s)" % esc(us["username"])) if us.get("username") else "",
              esc(us.get("phone") or "-"), uid, esc(label), amount, months_open(us), esc(txn)))
    kb = {"inline_keyboard": [[{"text": "✅ Approve", "callback_data": "ok:" + pid}, {"text": "❌ Reject", "callback_data": "no:" + pid}]]}
    api("sendPhoto", chat_id=ADMIN, photo=photo, caption=cap, parse_mode="HTML", reply_markup=kb)

def decide(pid, ok, cb):
    p = DB["payments"].get(pid)
    if not p or p["status"] != "waiting":
        api("answerCallbackQuery", callback_query_id=cb["id"], text="Already handled"); return
    us = DB["users"][p["uid"]]
    if ok:
        before = months_open(us)
        us["months"] = MONTHS if p.get("plan") == "full" else min(MONTHS, before + 1)
        us["last_paid"] = now_ms()
        p["status"] = "approved"; save()
        n = months_open(us)
        opened = "all 4 months are open" if n >= MONTHS and before == 0 else "%s is open" % MONTH_NAMES[n]
        opened_am = "ሁሉም 4 ወራት ተከፍተዋል" if n >= MONTHS and before == 0 else "%s ተከፍቷል" % MONTH_AM[n]
        send(int(p["uid"]), "🎉 <b>Payment confirmed!</b> %s. Enjoy learning!\nክፍያዎ ተረጋግጧል! %s።" % (opened[0].upper() + opened[1:], opened_am),
             learn_buttons(us))
        result = "✅ Approved — %s now has %d of 4 months" % (esc(us["name"]), n)
    else:
        p["status"] = "rejected"; save()
        send(int(p["uid"]), "😕 We could not confirm your payment. Please check the transaction number and send again.\nክፍያዎን ማረጋገጥ አልቻልንም። እባክዎ እንደገና ይላኩ።",
             [[{"text": "💳 Try again · እንደገና", "callback_data": "plan:" + (p.get("plan") or "month")}]])
        result = "❌ Rejected"
    api("answerCallbackQuery", callback_query_id=cb["id"], text=result[:190])
    msg = cb["message"]
    api("editMessageCaption", chat_id=msg["chat"]["id"], message_id=msg["message_id"],
        caption=(msg.get("caption") or "") + "\n\n" + result, parse_mode="HTML")

# ---------- sign-up ----------
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
        if arg in ("month", "full"): pay_instructions(chat, us, arg)
        elif arg in ("basic", "premium", "pay"): show_plans(chat, us)
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
    if data == "sub": show_plans(chat, us)
    elif data in ("plan:month", "plan:basic"): pay_instructions(chat, us, "month")
    elif data == "plan:full": pay_instructions(chat, us, "full")
    elif data == "dl": send_course_file(chat, us)
    elif data == "help":
        send(chat, "❓ <b>Help</b>\n• Tap 📚 Open course to learn here in Telegram.\n• Paid months: tap 📥 Download course to learn without internet.\n• The course has 4 months. Each payment opens the next month.\n"
                   "• To pay: 💳 Pay → choose → pay with Telebirr → send the screenshot.\n• /reminders_off — stop daily reminders\n\n"
                   "Questions? Write to %s" % esc(CFG.get("support_contact", "the owner")))

def stats(chat):
    t = now_ms(); us = [u for k, u in DB["users"].items() if int(k) != ADMIN]
    by_month = [sum(1 for u in us if months_open(u) == n) for n in range(1, MONTHS + 1)]
    trial = sum(1 for u in us if months_open(u) == 0 and in_trial(u))
    waiting = sum(1 for p in DB["payments"].values() if p["status"] == "waiting")
    recent = sum(p.get("amount", PRICE) for p in DB["payments"].values() if p["status"] == "approved" and t - p["at"] < 30 * DAY_MS)
    total = sum(p.get("amount", PRICE) for p in DB["payments"].values() if p["status"] == "approved")
    send(chat, "📊 <b>Stats</b>\nStudents: %d\nIn free trial: %d\nMonths open — 1: %d · 2: %d · 3: %d · 4: %d\n"
               "Waiting for approval: %d\nLast 30 days: %d Birr\nAll time: %d Birr"
         % (len(us), trial, by_month[0], by_month[1], by_month[2], by_month[3], waiting, recent, total))

# ---------- reminders ----------
def reminders():
    now = datetime.now(EAT); today = now.strftime("%Y-%m-%d"); t = now_ms(); changed = False
    for uid, us in DB["users"].items():
        if not us.get("phone") or int(uid) == ADMIN: continue
        n = months_open(us)
        if n == 0 and us.get("trial_until", 0) and not in_trial(us) and not us.get("trial_end_sent"):
            us["trial_end_sent"] = True; changed = True
            send(int(uid), "🔒 Your 3-day free trial has ended. Open Month 1 for %d Birr to keep learning.\nየ3 ቀን ነፃ ሙከራዎ አልቋል። ወር 1ን በ%d ብር ይክፈቱ።" % (PRICE, PRICE),
                 [[{"text": "💳 Open Month 1 · %d Birr" % PRICE, "callback_data": "plan:month"}],
                  [{"text": "🎓 Full course · %d Birr" % PRICE_FULL, "callback_data": "plan:full"}]])
        if 0 < n < MONTHS and us.get("last_paid") and t - us["last_paid"] > NUDGE_DAYS * DAY_MS and us.get("nudged_for") != us["last_paid"]:
            us["nudged_for"] = us["last_paid"]; changed = True
            send(int(us["telegram_id"]) if us.get("telegram_id") else int(uid),
                 "🦁 Ready for <b>%s</b>? Keep going — you're doing great!\n%s ለመጀመር ዝግጁ ነዎት?" % (MONTH_NAMES[n + 1], MONTH_AM[n + 1]),
                 [[{"text": "💳 Open %s · %d Birr" % (MONTH_NAMES[n + 1].split(" · ")[0], PRICE), "callback_data": "plan:month"}]])
        if has_access(us) and us.get("reminders", True) and now.hour >= REMIND_HOUR and us.get("last_daily") != today:
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
