"""Build the Telegram course files from the main app (fidel-english.html).

Run from the FidelEnglish folder:   python tools/build_telegram.py
(Needs Node.js, used once to read the lesson data.)

Makes:
  telegram/webapp/index.html          the course inside Telegram (upload to Vercel through GitHub)
  telegram/offline/month1..4.html     downloadable courses with ONLY the paid months' lessons.
                                      The bot fills in the student's name and phone before sending.

The bot opens the Telegram course with these link values:
  m = months open (0-4), t = free-trial end time (ms, 0 = no trial), b = bot username.
"""
import json, os, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = open(os.path.join(ROOT, "fidel-english.html"), encoding="utf-8").read()
DATA_START, DATA_END = "const LEVELS = [", "const WORDMAP = {};"

def patcher(s):
    def rep(a, b):
        nonlocal s
        assert s.count(a) == 1, (a[:70], s.count(a))
        s = s.replace(a, b)
    return rep, lambda: s

def head(telegram):
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
            + ('<script src="https://telegram.org/js/telegram-web-app.js"></script>\n' if telegram else '')
            + '<style>*,*::before,*::after{box-sizing:border-box}body{margin:0}</style>\n')

def common(rep):
    rep('Open this page in the Claude app or in Chrome while signed in to use the AI tutor.', 'Coming soon · በቅርቡ ይመጣል')
    rep('const contact = P.method === "phone" ? normPhone(raw)', 'const contact = P.method !== "phone" && P.method !== "gmail" ? P.contact : P.method === "phone" ? normPhone(raw)')
    rep('  show("profile");\n', '  show("profile");\n  if (P.method !== "phone" && P.method !== "gmail") $("#pfContact").closest(".field").hidden = true;\n')

# ---------- 1. Telegram Mini App ----------
def build_webapp():
    rep, get = patcher(head(True) + SRC)
    rep('let isOwner = false;', '''let isOwner = false;
const TG = (window.Telegram && Telegram.WebApp && Telegram.WebApp.initData) ? Telegram.WebApp : null;
const QS = new URLSearchParams(location.search);
const FROM_BOT = QS.has("m");
if (TG){ try { TG.ready(); TG.expand(); } catch(e){} }
if (FROM_BOT){
  store.months = Math.max(0, Math.min(4, +QS.get("m") || 0));
  const t = +QS.get("t") || 0;
  store.trialStart = t ? t - TRIAL_DAYS * 86400000 : 1;
  saveStore();
}''')
    rep('if (b) toast("Payment is coming soon · ክፍያ በቅርቡ ይጀምራል");',
        'if (b){ const bot = QS.get("b"); if (TG && bot){ TG.openTelegramLink("https://t.me/" + bot + "?start=" + b.dataset.plan); try { TG.close(); } catch(e){} } else toast("Open the course from our Telegram bot to pay · ከቴሌግራም ቦቱ ይክፈሉ"); }')
    rep('store.trialStart = Date.now(); store.nudged', 'if (!FROM_BOT) store.trialStart = Date.now(); store.nudged')
    rep('  show("signup");\n  $("#v-signup .seg")', '''  show("signup");
  if (TG && TG.initDataUnsafe && TG.initDataUnsafe.user && !$("#suName").value) $("#suName").value = TG.initDataUnsafe.user.first_name || "";
  $("#v-signup .seg")''')
    rep('if (store.profile){ renderHome(); checkMissed();', '''if (TG && TG.initDataUnsafe && TG.initDataUnsafe.user && (!store.profile || store.profile.tgId !== TG.initDataUnsafe.user.id)){
  const tu = TG.initDataUnsafe.user;
  store.profile = Object.assign({ avatar:"🦁", goal:10, remind:"19:00", created:Date.now() }, store.profile || {},
    { name: (store.profile && store.profile.tgId === tu.id && store.profile.name) || tu.first_name || "Friend", method:"telegram", contact:"Telegram", tgId: tu.id });
  saveStore();
}
if (store.profile){ renderHome(); checkMissed();''')
    rep('''fn:() => { delete store.profile; saveStore(); renderSignup(); } }''',
        '''fn:() => { delete store.profile; saveStore(); if (TG) { try { TG.close(); } catch(e){} } else renderSignup(); } }''')
    common(rep)
    return get() + '\n</body>\n</html>\n'

# ---------- 2. Offline downloadable courses ----------
def lesson_data():
    i, j = SRC.index(DATA_START), SRC.index(DATA_END)
    js = SRC[i:j] + "\nprocess.stdout.write(JSON.stringify({LEVELS, LESSONS, SCENARIOS}));\n"
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(js); path = f.name
    try:
        out = subprocess.run(["node", path], capture_output=True, check=True).stdout
    finally:
        os.remove(path)
    d = json.loads(out.decode("utf-8"))
    pron = [l["id"] for l in d["LESSONS"] if l["level"] == "pron"]
    for l in d["LESSONS"]:
        l["month"] = l.get("month") or {"beg": 1, "int": 2, "adv": 3}.get(l["level"]) or (1 if pron.index(l["id"]) < 5 else 2)
    return d

def js_json(v): return json.dumps(v, ensure_ascii=False).replace("</", "<\\/")

def build_offline(months, data):
    lessons = [l for l in data["LESSONS"] if l["month"] <= months]
    i, j = SRC.index(DATA_START), SRC.index(DATA_END)
    src = (SRC[:i] + "const LEVELS = " + js_json(data["LEVELS"]) + ";\nconst LESSONS = " + js_json(lessons)
           + ";\nconst SCENARIOS = " + js_json(data["SCENARIOS"]) + ";\n" + SRC[j:])
    rep, get = patcher(head(False) + src)
    rep('const KEY = "fidel-english-v1";', 'const KEY = "fidel-english-offline";')
    rep('let isOwner = false;', '''let isOwner = false;
const LICENSE = "__FIDEL_LICENSE__";
store.months = %d; store.trialStart = 1;
if (LICENSE && typeof LICENSE === "object" && (!store.profile || store.profile.method !== "license")){
  store.profile = Object.assign({ avatar:"🦁", goal:10, remind:"19:00", created:Date.now() }, store.profile || {}, { name: LICENSE.name || "Student", method:"license", contact: LICENSE.phone || "" });
}
saveStore();''' % months)
    rep('if (b) toast("Payment is coming soon · ክፍያ በቅርቡ ይጀምራል");',
        'if (b){ const bot = LICENSE && LICENSE.bot; if (bot) location.href = "https://t.me/" + bot + "?start=" + b.dataset.plan; else toast("Pay in our Telegram bot · በቴሌግራም ቦታችን ይክፈሉ"); }')
    rep('<p class="paynote">Pay with Telebirr in our Telegram bot · <span class="am">በቴሌግራም ቦታችን በቴሌብር ይክፈሉ</span></p>',
        '<p class="paynote">Pay with Telebirr in our Telegram bot, then tap 📥 Download course again to get the new month.<br><span class="am">በቴሌግራም ቦታችን ይክፈሉ፣ ከዚያ አዲሱን ወር ለማግኘት ኮርሱን እንደገና ያውርዱ።</span></p>')
    rep('''fn:() => { delete store.profile; saveStore(); renderSignup(); } }''', '''fn:() => {} }''')
    label = "Month 1" if months == 1 else "Months 1–%d" % months
    rep('<p class="foot">Every lesson:', '<p class="foot" style="margin:0">📥 Offline course · ' + label + ' · Licensed to ${esc((LICENSE && LICENSE.name) || "")} ${esc((LICENSE && LICENSE.phone) || "")}<br>Personal copy, please do not share · <span class="am">የግል ቅጂ ነው፣ አያጋሩ</span></p><p class="foot">Every lesson:')
    common(rep)
    out = get() + '\n</body>\n</html>\n'
    assert out.count('"__FIDEL_LICENSE__"') == 1
    return out

if __name__ == "__main__":
    web = os.path.join(ROOT, "telegram", "webapp", "index.html")
    open(web, "w", encoding="utf-8").write(build_webapp()); print("Built telegram/webapp/index.html")
    data = lesson_data()
    os.makedirs(os.path.join(ROOT, "telegram", "offline"), exist_ok=True)
    for k in range(1, 5):
        html = build_offline(k, data)
        open(os.path.join(ROOT, "telegram", "offline", "month%d.html" % k), "w", encoding="utf-8").write(html)
        n = sum(1 for l in data["LESSONS"] if l["month"] <= k)
        print("Built telegram/offline/month%d.html  (%d lessons, %d KB)" % (k, n, len(html.encode("utf-8")) // 1024))
