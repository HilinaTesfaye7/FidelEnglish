"""Build the Telegram Mini App (telegram/webapp/index.html) from the main app (fidel-english.html).

Run from the FidelEnglish folder:   python tools/build_telegram.py
The bot opens the course with these link values:
  m = months open (0-4), t = free-trial end time (ms, 0 = no trial), b = bot username.
"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = os.path.join(ROOT, "fidel-english.html")
out = os.path.join(ROOT, "telegram", "webapp", "index.html")
s = open(src, encoding="utf-8").read()

def rep(a, b):
    global s
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)

s = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
     '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
     '<script src="https://telegram.org/js/telegram-web-app.js"></script>\n'
     '<style>*,*::before,*::after{box-sizing:border-box}body{margin:0}</style>\n') + s

# Telegram setup + access from the bot's link
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

# Pay buttons go to the bot
rep('if (b) toast("Payment is coming soon · ክፍያ በቅርቡ ይጀምራል");',
    'if (b){ const bot = QS.get("b"); if (TG && bot){ TG.openTelegramLink("https://t.me/" + bot + "?start=" + b.dataset.plan); try { TG.close(); } catch(e){} } else toast("Open the course from our Telegram bot to pay · ከቴሌግራም ቦቱ ይክፈሉ"); }')

rep('Open this page in the Claude app or in Chrome while signed in to use the AI tutor.', 'Coming soon · በቅርቡ ይመጣል')

# The bot decides the trial; signing up must not restart it
rep('store.trialStart = Date.now(); store.nudged', 'if (!FROM_BOT) store.trialStart = Date.now(); store.nudged')

# Name from Telegram on the sign-up form
rep('  show("signup");\n  $("#v-signup .seg")', '''  show("signup");
  if (TG && TG.initDataUnsafe && TG.initDataUnsafe.user && !$("#suName").value) $("#suName").value = TG.initDataUnsafe.user.first_name || "";
  $("#v-signup .seg")''')

# Sign-up happens in the bot (phone + Telegram ID); the course makes the profile from the Telegram user
rep('if (store.profile){ renderHome(); checkMissed();', '''if (TG && TG.initDataUnsafe && TG.initDataUnsafe.user && (!store.profile || store.profile.tgId !== TG.initDataUnsafe.user.id)){
  const tu = TG.initDataUnsafe.user;
  store.profile = Object.assign({ avatar:"🦁", goal:10, remind:"19:00", created:Date.now() }, store.profile || {},
    { name: (store.profile && store.profile.tgId === tu.id && store.profile.name) || tu.first_name || "Friend", method:"telegram", contact:"Telegram", tgId: tu.id });
  saveStore();
}
if (store.profile){ renderHome(); checkMissed();''')
rep('const contact = P.method === "phone" ? normPhone(raw)', 'const contact = P.method === "telegram" ? P.contact : P.method === "phone" ? normPhone(raw)')
rep('  show("profile");\n', '  show("profile");\n  if (P.method === "telegram") $("#pfContact").closest(".field").hidden = true;\n')
rep('''fn:() => { delete store.profile; saveStore(); renderSignup(); } }''',
    '''fn:() => { delete store.profile; saveStore(); if (TG) { try { TG.close(); } catch(e){} } else renderSignup(); } }''')

s += '\n</body>\n</html>\n'
open(out, "w", encoding="utf-8").write(s)
print("Built", os.path.relpath(out, ROOT))
