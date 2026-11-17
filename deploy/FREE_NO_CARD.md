# Bot 24/7 for free, no card: PythonAnywhere + cron-job.org

The website is already on Cloudflare. This puts the bot online too.

## 1. Make the bundle (on your computer)
1. Stop the bot here (Ctrl + C). From now on, don't run `python bot.py` on your computer.
2. In `telegram/config.json`, `webapp_url` must be your Cloudflare link:
   `"webapp_url": "https://fidelenglish.fetitesfa.workers.dev",`
3. In the FidelEnglish folder run: `python deploy/make_bundle.py` → makes `deploy/fidel-bot.zip` (private!).

## 2. PythonAnywhere (free "Beginner" account, no card)
1. Go to **pythonanywhere.com** → **Pricing & signup** → **Create a Beginner account**.
   Your username becomes your address: `https://USERNAME.pythonanywhere.com`.
2. **Files** tab → **Upload a file** → choose `deploy/fidel-bot.zip`.
3. **Consoles** tab → **Bash**. Type:
   `unzip -o fidel-bot.zip -d ~/fidel`
4. **Web** tab → **Add a new web app** → Next → **Manual configuration** → **Python 3.12** (or newest) → Next.
5. On the Web page, click the **WSGI configuration file** link. Delete everything in it and paste these 2 lines
   (change USERNAME):
   ```
   import sys; sys.path.insert(0, "/home/USERNAME/fidel/telegram")
   from wsgi_app import application
   ```
   **Save**, go back to the **Web** tab, click the green **Reload** button.
6. Back in the **Bash** console:
   ```
   cd ~/fidel/telegram
   python3 setup_webhook.py https://USERNAME.pythonanywhere.com
   ```
   It prints a **tick link**. Copy it (keep it private).
7. **Web** tab → **Reload** again.
8. In Telegram, send `/start` to your bot. It should answer.

## 3. cron-job.org (free, no card): reminders and daily backup
1. Go to **cron-job.org** → sign up (free).
2. **Create cronjob**: Title `Fidel tick`, URL = the tick link from step 2.6, schedule **every 15 minutes** → Create.

## Every month
PythonAnywhere emails you: open the **Web** tab and click **"Run until 1 month from today"**. Otherwise the bot pauses.

## Updating the bot later
Make a new zip, upload it (Files), then in Bash: `cp ~/fidel/telegram/data.json ~/data-backup.json && unzip -o fidel-bot.zip -d ~/fidel && cp ~/data-backup.json ~/fidel/telegram/data.json`, then **Reload** on the Web tab.

## Back to running on a computer (if ever needed)
In the PythonAnywhere Bash: `python3 setup_webhook.py off`, then run `python bot.py` on the computer.
