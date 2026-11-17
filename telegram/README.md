# Fidel English on Telegram

## Files
- `webapp/index.html` – the course (Telegram Mini App). Upload the `webapp` folder to Netlify.
- `bot.py` – the bot: free trial, Telebirr payments, approve/reject, reminders.
- `config.json` – your settings. Keep this file private (it has your bot token).
- `data.json` – created by the bot: your users and payments. Do not delete it.

## Setup
1. Telegram → @BotFather → `/newbot` → copy the token into `config.json` → `bot_token`.
2. Telegram → @userinfobot → copy your Id into `config.json` → `admin_id`.
3. Write your Telebirr number and name in `config.json`.
4. Go to https://app.netlify.com/drop → sign up free → drag the `webapp` folder → copy the link into `config.json` → `webapp_url`.
5. Run the bot:  `python bot.py`  (it works while this computer is on).
6. Open your bot in Telegram and press Start.

## How sign-up works
New users press Start → tap "Share my phone" → the bot saves their phone number and Telegram ID
and starts the 3-day trial. The course opens with their Telegram name (no second sign-up).

## 4-month course and downloads
- Month 1 Beginner · Month 2 Intermediate · Month 3 Advanced · Month 4 real-life words + final exam.
- Each payment opens the next month; the full course price opens all 4. Opened months stay open.
- Students learn in Telegram (📚 Open course) or tap 📥 Download course to get an HTML file
  with ONLY their paid months (their name and phone are written inside). It works without internet.
- After changing `fidel-english.html`, run `python tools/build_telegram.py` to rebuild
  `webapp/index.html` and `offline/month1-4.html`, then push to GitHub and restart the bot.

## Plans
- Basic (`price_month`, 300): opens the next month + 📚 course, 📥 download.
- Premium (`price_premium`, 1000): everything in Basic + 🦁 AI tutor for 30 days. Students with all 4 months
  can buy Premium just for the tutor. Renewing adds 30 more days. Lessons stay open when Premium ends.
- Full course (`price_full`, 1000): all 4 months at once, no AI tutor (only offered before the first payment).

## AI tutor switch
- `"tutor_enabled": false` in config.json (the default): the AI tutor and Premium show "coming soon",
  and plans offer only Basic and Full course. Set it to `true` (plus the API key) to sell Premium.

## AI tutor
- AI tutor "Anbessa" (Premium only): students tap 🦁 Chat with Anbessa (or send /tutor) and chat in English;
  it corrects their mistakes like a friend. Uses Claude Haiku 5.5, 30 messages per student per day (`tutor_daily_limit`).
  Setup: `pip install anthropic`, then put your key from console.anthropic.com in `anthropic_api_key`.
  `/stats` shows an estimate of what the tutor has cost; check the real bill in the Anthropic Console.

## Owner commands
- `/stats` – users, paying users, money in the last 30 days.
- Payments arrive with ✅ Approve / ❌ Reject buttons. Check your Telebirr SMS first.

## Users' commands
- `/start` – menu · `/reminders_off` – stop daily reminders

## Later
- Move the bot to a small server so it runs 24/7.
- Premium (AI tutor) needs a server with your own Claude API key.
- Access links can be copied by a clever user; a server check will fix that later.
