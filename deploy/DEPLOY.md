# Going live: Fidel English

Website on **Cloudflare Pages** (free), bot on a **free Google Cloud server** (24/7). AI tutor stays off.

## A. Website → Cloudflare Pages (about 10 minutes, no card needed)
1. Go to **dash.cloudflare.com** and sign up (free).
2. Left menu: **Workers & Pages** → **Create** → **Pages** → **Connect to Git**.
3. Connect **GitHub** and choose the **FidelEnglish** repository.
4. Build settings:
   - Framework preset: **None**
   - Build command: *(leave empty)*
   - Build output directory: **telegram/webapp**
5. **Save and Deploy**. You get a link like `https://fidelenglish.pages.dev`. Open it: the lion should appear.
6. In `telegram/config.json`, set `"webapp_url": "https://fidelenglish.pages.dev"` (your link) and save.

From now on, every push to GitHub updates the site by itself.

## B. Bot → free Google Cloud server
1. Go to **console.cloud.google.com** and sign up. Add a card (it is checked, the free server is not charged).
2. Menu → **Compute Engine** → **VM instances** → **Create instance**:
   - Name: `fidel-bot`
   - Region: **us-central1** (or us-west1 / us-east1). Only these are free.
   - Machine: **e2-micro**
   - Boot disk: **Debian 12**, **Standard persistent disk**, **30 GB**
   - Click **Create**.
3. On your computer: stop the bot here (**Ctrl + C**), then in the FidelEnglish folder run:
   `python deploy/make_bundle.py`
   It makes `deploy/fidel-bot.zip`. Keep it private.
4. In Google Cloud, click **SSH** next to `fidel-bot`. A black window opens.
5. In that window: **⚙ (or ↑) → Upload file**. Upload **deploy/fidel-bot.zip**, then **deploy/setup_server.sh**.
6. Type: `bash setup_server.sh` and press Enter. At the end it should say **DONE**.
7. In Telegram, send `/start` to the bot. Then send `/backup`: you should receive the student list file.

**Never run the bot on your computer again** while the server runs it (two copies → "Conflict" error).

## Useful server commands (in the SSH window)
- See what the bot is doing: `sudo journalctl -u fidel-bot -f` (Ctrl + C to stop watching)
- Restart the bot: `sudo systemctl restart fidel-bot`
- Update the bot later: make a new zip (step 3), upload it, run `bash setup_server.sh` again. Your student list on the server is kept.

## Backups
- Every day at 3:00 (Addis Ababa time) the bot sends **fidel-data-DATE.json** to you on Telegram. Keep those messages.
- The server also keeps a daily copy for 30 days in `/opt/fidel/backups`.
