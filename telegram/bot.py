"""Fidel English Telegram bot — 4-month course.

- Plans: Basic (one month), Premium (one month + AI tutor for 30 days), Full course (all 4 months).

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
PRICE_PREMIUM = int(CFG.get("price_premium", 1000))                # Premium: next month + AI tutor for 30 days
PREMIUM_DAYS = 30
TRIAL_DAYS = int(CFG.get("trial_days", 3))
CLUB_LINK = (CFG.get("speaking_club_link") or "").strip()            # Telegram group invite link
TUTOR_MODEL = CFG.get("tutor_model", "claude-haiku-5-5")
TUTOR_ON = bool(CFG.get("tutor_enabled", False))                    # false = AI tutor and Premium show "coming soon"
TUTOR_DAILY_LIMIT = int(CFG.get("tutor_daily_limit", 30))           # messages per student per day
TUTOR_HISTORY = 20                                                   # messages the tutor remembers
# Haiku 5.5 price per million tokens (prompts up to 100K tokens), for the /stats cost estimate
TUTOR_PRICE_IN, TUTOR_PRICE_OUT = 0.10, 0.50
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

def api_file(method, fields, file_field, filename, content, ctype="text/html"):
    """Upload a file (multipart/form-data)."""
    boundary = "----FidelEnglish%d" % int(time.time() * 1000)
    parts = []
    for k, v in fields.items():
        parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (boundary, k, v)).encode("utf-8"))
    parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"; filename="%s"\r\nContent-Type: %s\r\n\r\n'
                  % (boundary, file_field, filename, ctype)).encode("utf-8") + content + b"\r\n")
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
def has_tutor(us): return us.get("premium_until", 0) > now_ms()

def course_button(us):
    q = {"m": months_open(us), "t": us.get("trial_until", 0) if in_trial(us) else 0, "b": BOT_USERNAME or ""}
    url = CFG["webapp_url"].rstrip("/") + "/?" + urllib.parse.urlencode(q)
    return [{"text": "📚 Open course · ትምህርቱን ክፈት", "web_app": {"url": url}}]

DOWNLOAD_BTN = {"text": "📥 Download course · ኮርሱን አውርድ", "callback_data": "dl"}
TUTOR_BTN = {"text": "🦁 Chat with Anbessa, your AI tutor · ከ AI አስተማሪ ጋር ይወያዩ", "callback_data": "tutor"}
UPGRADE_BTN = {"text": "⭐ Get Anbessa, the AI tutor (Premium) · ፕሪሚየም", "callback_data": "plan:premium"}
SOON_BTN = {"text": "🦁 Anbessa AI tutor · በቅርቡ (coming soon)", "callback_data": "tutor"}
def tutor_soon(chat, us=None):
    send(chat, "🦁 <b>Anbessa, your AI tutor, is coming soon!</b>\nYou will chat in English like with a friend, and Anbessa will correct your mistakes. We will tell you when it is ready.\n\n"
               "🦁 <b>AI አስተማሪው አንበሳ በቅርቡ ይመጣል!</b>\nሲዘጋጅ እናሳውቅዎታለን።", learn_buttons(us) if us and has_access(us) else None)
END_TUTOR_BTN = [[{"text": "⏹ End chat · ውይይቱን ጨርስ", "callback_data": "end_tutor"}]]

# ---------- AI tutor (Claude) ----------
_tutor_client = None
def tutor_client():
    """The Claude client, or None when the tutor isn't set up (no SDK or no API key)."""
    global _tutor_client
    if _tutor_client is None:
        key = (CFG.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY") or "").strip()
        if not key or key.startswith("PASTE"): return None
        try:
            import anthropic
        except ImportError:
            print("The AI tutor needs the Claude SDK: run  pip install anthropic", flush=True); return None
        _tutor_client = anthropic.Anthropic(api_key=key, timeout=60.0, max_retries=2)
    return _tutor_client

LEVEL_STYLE = {
    1: "The student is a BEGINNER. Use very simple words and short sentences (5-10 words). "
       "After your English reply, add the Amharic translation of your reply on a new line in brackets.",
    2: "The student is INTERMEDIATE. Use everyday English with common phrasal verbs and different tenses. "
       "Add Amharic only for a hard word, in brackets.",
    3: "The student is ADVANCED. Speak naturally like a friendly native speaker, with idioms. "
       "Point out English that is correct but sounds unnatural. No Amharic unless asked.",
}

def tutor_system(us):
    level = LEVEL_STYLE[min(3, max(1, months_open(us)))]
    return ("You are Anbessa, a warm, funny English tutor and friend inside the Fidel English Telegram bot. "
            "Your students are Ethiopians whose first language is Amharic, learning to speak English with confidence. "
            "Chat like a kind friend: be curious about their life, family, work, food, faith, football, music and dreams. "
            "Keep every reply short: 2-4 sentences, then ask ONE question to keep the conversation going. "
            "If the student made a mistake, first answer naturally, then add one line that starts with '✏️ Better:' "
            "and shows the corrected sentence. Fix only the most important mistake, and praise good English often. "
            "If they write in Amharic, answer in simple English and gently ask them to try in English. "
            "Use the student's name sometimes. Stay friendly and respectful; keep topics suitable for all ages. "
            "Write plain text only: no markdown, no lists, no headings. "
            + level + " The student's name is " + (us.get("name") or "friend") + ".")

def start_tutor(chat, us):
    if not TUTOR_ON:
        tutor_soon(chat, us); return
    if not has_tutor(us):
        send(chat, "🦁 Anbessa, the AI tutor, is part of <b>Premium</b> (%d Birr): your next month of lessons + chat with Anbessa for %d days.\n"
                   "AI አስተማሪው በፕሪሚየም ውስጥ ነው።" % (PRICE_PREMIUM, PREMIUM_DAYS),
             [[{"text": "⭐ Get Premium · %d Birr" % PRICE_PREMIUM, "callback_data": "plan:premium"}]]); return
    if not tutor_client():
        send(chat, "🦁 The AI tutor is coming very soon! · AI አስተማሪው በቅርቡ ይመጣል!"); return
    us["state"] = "tutor"; us["tutor_hist"] = []; save()
    send(chat, "🦁 <b>Hi %s! I'm Anbessa, your English friend.</b>\n"
               "Let's chat in English. Write to me about anything: your day, your family, your work...\n"
               "I will help you when you make a mistake. ✏️\n\n"
               "ሰላም! በእንግሊዝኛ እንወያይ። ስህተት ሲሰሩ እረዳዎታለሁ።\n\n"
               "👉 So, how are you today? What did you do this morning?" % esc(us["name"]), END_TUTOR_BTN)

def end_tutor(chat, us):
    us["state"] = None; save()
    send(chat, "👋 Great chat! See you next time. · ጥሩ ውይይት ነበር! በሚቀጥለው እንገናኝ።", learn_buttons(us))

def tutor_reply(chat, uid, us, text):
    today = datetime.now(EAT).strftime("%Y-%m-%d")
    if us.get("tutor_day") != today: us["tutor_day"], us["tutor_count"] = today, 0
    if not TUTOR_ON or not has_tutor(us):
        us["state"] = None; save(); start_tutor(chat, us); return
    if us["tutor_count"] >= TUTOR_DAILY_LIMIT:
        send(chat, "🦁 You've sent %d messages today, great work! Let's talk again tomorrow.\nለዛሬ በቂ ነው፣ ነገ እንገናኝ!" % TUTOR_DAILY_LIMIT, END_TUTOR_BTN); return
    client = tutor_client()
    if not client:
        end_tutor(chat, us); return
    hist = (us.get("tutor_hist") or []) + [{"role": "user", "content": text[:1500]}]
    api("sendChatAction", chat_id=chat, action="typing")
    import anthropic
    try:
        resp = client.messages.create(
            model=TUTOR_MODEL, max_tokens=1024,
            system=tutor_system(us),
            thinking={"type": "disabled"},          # a short friendly chat doesn't need thinking; keeps cost low
            output_config={"effort": "low"},
            messages=hist)
    except anthropic.RateLimitError:
        send(chat, "🦁 I'm a little busy right now. Please send that again in a minute.\nእባክዎ ትንሽ ቆይተው ይላኩ።"); return
    except anthropic.AuthenticationError:
        print("Tutor: the Anthropic API key is wrong or has no credit.", flush=True)
        send(chat, "🦁 Sorry, the tutor is resting now. Please try again later.\nይቅርታ፣ እባክዎ ቆይተው ይሞክሩ።"); return
    except anthropic.APIStatusError as e:
        print("Tutor API error:", e.status_code, str(e)[:200], flush=True)
        send(chat, "🦁 Sorry, something went wrong. Please try again.\nይቅርታ፣ እንደገና ይሞክሩ።"); return
    except anthropic.APIConnectionError:
        send(chat, "🦁 I can't connect right now. Please try again soon.\nአሁን መገናኘት አልቻልኩም።"); return
    u = DB.setdefault("tutor_usage", {"input": 0, "output": 0, "messages": 0})
    u["input"] += resp.usage.input_tokens; u["output"] += resp.usage.output_tokens; u["messages"] += 1
    if resp.stop_reason == "refusal":
        reply = "Let's talk about something else! What do you like to do on weekends?"
    else:
        reply = "".join(b.text for b in resp.content if b.type == "text").strip() or "Sorry, can you say that again?"
    hist.append({"role": "assistant", "content": reply})
    us["tutor_hist"] = hist[-TUTOR_HISTORY:]
    while us["tutor_hist"] and us["tutor_hist"][0]["role"] != "user": us["tutor_hist"].pop(0)
    us["tutor_count"] += 1; save()
    send(chat, esc(reply), END_TUTOR_BTN)

def learn_buttons(us):
    """Learn in Telegram, and (for paid months) download the course to learn without internet."""
    rows = [course_button(us)]
    if months_open(us) > 0:
        rows.append([DOWNLOAD_BTN])
        if CLUB_LINK: rows.append([{"text": "🎤 Join our speaking club · የንግግር ክበብ", "url": CLUB_LINK}])
        rows.append([SOON_BTN] if not TUTOR_ON else [TUTOR_BTN] if has_tutor(us) else [UPGRADE_BTN])
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
    lic = {"name": us.get("name", ""), "phone": us.get("phone") or "", "months": n, "bot": BOT_USERNAME or "",
           "web": CFG.get("webapp_url", "")}
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
    if has_tutor(us):
        status += "\n⭐ Premium (AI tutor) until <b>%s</b>" % fmt_date(us["premium_until"])
    rows = learn_buttons(us) if has_access(us) else []
    rows.append([{"text": "💳 Pay · ይክፈሉ", "callback_data": "sub"}, {"text": "❓ Help · እርዳታ", "callback_data": "help"}])
    send(chat, "🦁 <b>Selam %s! Welcome to Fidel English.</b>\nሰላም! እንኳን ወደ ፊደል ኢንግሊሽ በደህና መጡ።\n\n%s" % (esc(us["name"]), status), rows)

def show_plans(chat, us):
    n = months_open(us)
    if not TUTOR_ON:
        if n >= MONTHS:
            send(chat, "🎓 You have the full course (all 4 months)! · ሙሉውን ኮርስ ከፍተዋል!\n\n🦁 AI tutor (Premium) — coming soon · በቅርቡ ይመጣል", learn_buttons(us)); return
        nxt = MONTH_NAMES[n + 1].split(" · ")[0]
        text = ("📚 <b>Fidel English — 4-month course</b>\n"
                "Month 1 Beginner · Month 2 Intermediate · Month 3 Advanced · Month 4 Real-life words, final exam + certificate 🎓\n\n"
                "📘 <b>Open %s — %d Birr</b>\nLessons in Telegram, 📥 download, and 🎤 our speaking club. Yours forever once opened.\n"
                "%s — %d ብር። አንዴ ከተከፈተ ለዘላለም የእርስዎ ነው።" % (MONTH_NAMES[n + 1], PRICE, MONTH_AM[n + 1], PRICE))
        rows = [[{"text": "📘 %s · %d Birr" % (nxt, PRICE), "callback_data": "plan:month"}]]
        if n == 0:
            text += ("\n\n🎓 <b>Full course, all 4 months — %d Birr</b> (save %d Birr)\nሙሉ ኮርስ፣ 4 ወራት — %d ብር"
                     % (PRICE_FULL, PRICE * MONTHS - PRICE_FULL, PRICE_FULL))
            rows.append([{"text": "🎓 Full course · %d Birr" % PRICE_FULL, "callback_data": "plan:full"}])
        text += "\n\n🦁 AI tutor (Premium) — coming soon · በቅርቡ ይመጣል"
        send(chat, text, rows); return
    if n >= MONTHS:
        text = ("🎓 You have the full course (all 4 months)!\n\n"
                "⭐ <b>Premium — %d Birr</b>: chat with Anbessa, your AI tutor, for %d days. "
                "Practise speaking English like with a friend, and get your mistakes corrected.\n"
                "ፕሪሚየም፦ ከ AI አስተማሪው ጋር ለ%d ቀናት ይወያዩ።" % (PRICE_PREMIUM, PREMIUM_DAYS, PREMIUM_DAYS))
        send(chat, text, [[{"text": "⭐ Premium · AI tutor · %d Birr" % PRICE_PREMIUM, "callback_data": "plan:premium"}]]); return
    nxt = MONTH_NAMES[n + 1].split(" · ")[0]
    text = ("📚 <b>Fidel English — 4-month course</b>\n"
            "Month 1 Beginner · Month 2 Intermediate · Month 3 Advanced · Month 4 Real-life words, final exam + certificate 🎓\n\n"
            "📘 <b>Basic — %d Birr</b>\nOpens %s: lessons in Telegram, 📥 download, and 🎤 our speaking club.\n"
            "%s ይከፈታል፤ ትምህርቶች፣ ማውረድና የንግግር ክበብ።\n\n"
            "⭐ <b>Premium — %d Birr</b>\nEverything in Basic + 🦁 <b>Anbessa, your AI tutor</b> for %d days: chat in English like with a friend and get your mistakes corrected.\n"
            "ሁሉም በመሰረታዊ ያለው + ከ AI አስተማሪ ጋር መወያየት።"
            % (PRICE, MONTH_NAMES[n + 1], MONTH_AM[n + 1], PRICE_PREMIUM, PREMIUM_DAYS))
    rows = [[{"text": "📘 Basic · %s · %d Birr" % (nxt, PRICE), "callback_data": "plan:month"}],
            [{"text": "⭐ Premium · %s + AI tutor · %d Birr" % (nxt, PRICE_PREMIUM), "callback_data": "plan:premium"}]]
    if n == 0:
        text += ("\n\n🎓 <b>Full course, all 4 months — %d Birr</b> (save %d Birr, no AI tutor)\nሙሉ ኮርስ፣ 4 ወራት — %d ብር"
                 % (PRICE_FULL, PRICE * MONTHS - PRICE_FULL, PRICE_FULL))
        rows.append([{"text": "🎓 Full course · %d Birr" % PRICE_FULL, "callback_data": "plan:full"}])
    send(chat, text, rows)

def plan_info(us, plan):
    """(amount, label) for a plan the user is buying now."""
    if plan == "full": return PRICE_FULL, "Full course (all 4 months)"
    if plan == "premium":
        if months_open(us) >= MONTHS: return PRICE_PREMIUM, "Premium: AI tutor for %d days" % PREMIUM_DAYS
        return PRICE_PREMIUM, "Premium: %s + AI tutor for %d days" % (MONTH_NAMES[months_open(us) + 1].split(" · ")[0], PREMIUM_DAYS)
    return PRICE, MONTH_NAMES[min(MONTHS, months_open(us) + 1)]

def pay_instructions(chat, us, plan):
    if plan == "premium" and not TUTOR_ON:
        tutor_soon(chat, us); return
    if months_open(us) >= MONTHS and plan != "premium":
        show_plans(chat, us); return
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
        if p.get("plan") == "premium":
            us["premium_until"] = max(now_ms(), us.get("premium_until", 0)) + PREMIUM_DAYS * DAY_MS
        us["last_paid"] = now_ms()
        p["status"] = "approved"; save()
        n = months_open(us)
        if n == before:
            opened, opened_am = "your course stays open", "ኮርስዎ ክፍት ነው"
        elif n >= MONTHS and before == 0:
            opened, opened_am = "all 4 months are open", "ሁሉም 4 ወራት ተከፍተዋል"
        else:
            opened, opened_am = "%s is open" % MONTH_NAMES[n], "%s ተከፍቷል" % MONTH_AM[n]
        if p.get("plan") == "premium":
            opened += ", and Anbessa, your AI tutor, is ready until %s 🦁" % fmt_date(us["premium_until"])
            opened_am += "፤ AI አስተማሪው ዝግጁ ነው"
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
        if us.get("state") == "tutor": us["state"] = None; save()
        arg = text[6:].strip()
        if arg in ("month", "full", "premium"): pay_instructions(chat, us, arg)
        elif arg in ("basic", "pay"): show_plans(chat, us)
        else: main_menu(chat, us)
        return
    if text == "/stats" and int(uid) == ADMIN: stats(chat); return
    if text == "/backup" and int(uid) == ADMIN: daily_backup(force=True); return
    if text in ("/stop", "/reminders_off"):
        us["reminders"] = False; save(); send(chat, "🔕 Reminders are off. Send /reminders_on to turn them on."); return
    if text == "/reminders_on":
        us["reminders"] = True; save(); send(chat, "🔔 Reminders are on."); return
    if text == "/tutor": start_tutor(chat, us); return
    if text in ("/end", "/end_chat"): end_tutor(chat, us); return
    if us.get("state") == "tutor":
        if text and not text.startswith("/"): tutor_reply(chat, uid, us, text)
        elif m.get("voice") or m.get("audio") or m.get("video_note"):
            send(chat, "🎤 I can only read typed messages for now. Please type in English!\nለአሁን የተጻፈ መልዕክት ብቻ አነባለሁ።", END_TUTOR_BTN)
        else:
            send(chat, "🦁 Please type a message in English, or tap ⏹ End chat.\nእባክዎ በእንግሊዝኛ ይጻፉ።", END_TUTOR_BTN)
        return
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
    elif data == "plan:premium": pay_instructions(chat, us, "premium")
    elif data == "dl": send_course_file(chat, us)
    elif data == "tutor": start_tutor(chat, us)
    elif data == "end_tutor": end_tutor(chat, us)
    elif data == "help":
        send(chat, "❓ <b>Help</b>\n• Tap 📚 Open course to learn here in Telegram.\n• Paid months: tap 📥 Download course to learn without internet.\n"
                   "• Premium: tap 🦁 Chat with Anbessa to practise English with your AI tutor (/tutor). Up to %d messages a day.\n" % TUTOR_DAILY_LIMIT +
                   "• The course has 4 months. Each payment opens the next month.\n"
                   "• To pay: 💳 Pay → choose → pay with Telebirr → send the screenshot.\n• /reminders_off — stop daily reminders\n\n"
                   "Questions? Write to %s" % esc(CFG.get("support_contact", "the owner")))

def stats(chat):
    t = now_ms(); us = [u for k, u in DB["users"].items() if int(k) != ADMIN]
    by_month = [sum(1 for u in us if months_open(u) == n) for n in range(1, MONTHS + 1)]
    trial = sum(1 for u in us if months_open(u) == 0 and in_trial(u))
    waiting = sum(1 for p in DB["payments"].values() if p["status"] == "waiting")
    recent = sum(p.get("amount", PRICE) for p in DB["payments"].values() if p["status"] == "approved" and t - p["at"] < 30 * DAY_MS)
    total = sum(p.get("amount", PRICE) for p in DB["payments"].values() if p["status"] == "approved")
    premium = sum(1 for u in us if has_tutor(u))
    tu = DB.get("tutor_usage", {"input": 0, "output": 0, "messages": 0})
    cost = tu["input"] / 1e6 * TUTOR_PRICE_IN + tu["output"] / 1e6 * TUTOR_PRICE_OUT
    send(chat, "📊 <b>Stats</b>\nStudents: %d\nIn free trial: %d\nMonths open — 1: %d · 2: %d · 3: %d · 4: %d\n"
               "Waiting for approval: %d\nLast 30 days: %d Birr\nAll time: %d Birr\n\n"
               "⭐ Premium students now: %d\n🦁 AI tutor: %d replies, about $%.2f so far (check the real bill at console.anthropic.com)"
         % (len(us), trial, by_month[0], by_month[1], by_month[2], by_month[3], waiting, recent, total, premium, tu["messages"], cost))

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
        pu = us.get("premium_until", 0)
        if pu and 0 < pu - t < 3 * DAY_MS and us.get("premium_warned") != pu:
            us["premium_warned"] = pu; changed = True
            send(int(uid), "🦁 Your Premium (AI tutor) ends on <b>%s</b>. Renew to keep chatting with Anbessa!\nፕሪሚየምዎ %s ያልቃል።" % (fmt_date(pu), fmt_date(pu)),
                 [[{"text": "⭐ Renew Premium · %d Birr" % PRICE_PREMIUM, "callback_data": "plan:premium"}]])
        elif pu and pu <= t and us.get("premium_ended") != pu:
            us["premium_ended"] = pu; changed = True
            if us.get("state") == "tutor": us["state"] = None
            send(int(uid), "🦁 Your Premium has ended. Your lessons stay open! Renew Premium any time to chat with Anbessa again.\nፕሪሚየምዎ አልቋል፤ ትምህርቶችዎ ግን ክፍት ናቸው።",
                 [[{"text": "⭐ Renew Premium · %d Birr" % PRICE_PREMIUM, "callback_data": "plan:premium"}]])
        if has_access(us) and us.get("reminders", True) and now.hour >= REMIND_HOUR and us.get("last_daily") != today:
            us["last_daily"] = today; changed = True
            send(int(uid), "🦁 It's English time, %s! Your lesson is waiting.\nየእንግሊዝኛ ሰዓት ደርሷል!" % esc(us["name"]), [course_button(us)])
    if changed: save()
    daily_backup(now)

BACKUP_HOUR = int(CFG.get("backup_hour", 3))    # Addis Ababa time
def daily_backup(now=None, force=False):
    """Send data.json (students and payments) to the owner on Telegram once a day, so it is never lost."""
    now = now or datetime.now(EAT); today = now.strftime("%Y-%m-%d")
    if not force and (now.hour < BACKUP_HOUR or DB.get("last_backup") == today): return
    DB["last_backup"] = today; save()
    content = open(DATA_FILE, "rb").read()
    users = sum(1 for k in DB["users"] if int(k) != ADMIN)
    ok = api_file("sendDocument", {"chat_id": ADMIN, "caption": "💾 Daily backup %s · %d students. Keep this file safe." % (today, users)},
                  "document", "fidel-data-%s.json" % today, content, "application/json")
    if not ok: DB["last_backup"] = ""; save()       # try again at the next check

# ---------- main loop ----------
def main():
    global BOT_USERNAME
    me = api("getMe")
    if not me: print("Could not connect. Check bot_token in config.json."); sys.exit(1)
    BOT_USERNAME = me["username"]
    api("setMyCommands", commands=[{"command": "start", "description": "Open the menu · ምናሌ"},
                                   {"command": "tutor", "description": "Chat with Anbessa, your AI tutor"},
                                   {"command": "end", "description": "End the tutor chat"},
                                   {"command": "reminders_off", "description": "Stop daily reminders"}])
    print("AI tutor: %s" % ("ON (%s, %d messages/day)" % (TUTOR_MODEL, TUTOR_DAILY_LIMIT) if tutor_client() else
                            "OFF (add anthropic_api_key to config.json and run: pip install anthropic)"), flush=True)
    print("Speaking club button: %s" % ("ON" if CLUB_LINK else "OFF (add speaking_club_link to config.json)"), flush=True)
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
