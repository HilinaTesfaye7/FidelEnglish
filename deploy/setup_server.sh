#!/usr/bin/env bash
# Fidel English bot: install on a fresh Debian/Ubuntu server and keep it running 24/7.
# Usage (on the server, in the folder where you uploaded both files):
#     bash setup_server.sh
# Running it again later updates the bot and keeps your student data.
set -euo pipefail

BUNDLE="${1:-$HOME/fidel-bot.zip}"
APP=/opt/fidel
[ -f "$BUNDLE" ] || { echo "Can't find $BUNDLE. Upload fidel-bot.zip first."; exit 1; }

echo "== 1/5 Installing Python =="
sudo apt-get update -y -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3 unzip >/dev/null

echo "== 2/5 Stopping the old bot (if any) =="
sudo systemctl stop fidel-bot 2>/dev/null || true

echo "== 3/5 Copying files =="
sudo id -u fidel >/dev/null 2>&1 || sudo useradd --system --home "$APP" --shell /usr/sbin/nologin fidel
sudo mkdir -p "$APP" "$APP/backups"
# keep the student list already on the server, if there is one
if [ -f "$APP/telegram/data.json" ]; then
  sudo cp "$APP/telegram/data.json" "$APP/backups/data-before-update-$(date +%F-%H%M).json"
  KEEP_DATA=1
else
  KEEP_DATA=0
fi
TMP=$(mktemp -d); unzip -q -o "$BUNDLE" -d "$TMP"
if [ "$KEEP_DATA" = 1 ]; then rm -f "$TMP/telegram/data.json"; fi
sudo cp -r "$TMP/." "$APP/"; rm -rf "$TMP"
sudo chown -R fidel:fidel "$APP"; sudo chmod 600 "$APP/telegram/config.json"

echo "== 4/5 Making it run 24/7 (restarts by itself) =="
sudo tee /etc/systemd/system/fidel-bot.service >/dev/null <<EOF
[Unit]
Description=Fidel English Telegram bot
After=network-online.target
Wants=network-online.target

[Service]
User=fidel
WorkingDirectory=$APP/telegram
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8

[Install]
WantedBy=multi-user.target
EOF

echo "== 5/5 Daily copy of the student list on the server (kept 30 days) =="
sudo tee /etc/cron.d/fidel-backup >/dev/null <<EOF
30 0 * * * fidel cp $APP/telegram/data.json $APP/backups/data-\$(date +\%F).json && find $APP/backups -name 'data-*.json' -mtime +30 -delete
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now fidel-bot
sleep 4
echo
sudo journalctl -u fidel-bot -n 6 --no-pager
echo
if systemctl is-active --quiet fidel-bot; then
  echo "DONE: the bot is running 24/7. Send /start to it in Telegram."
else
  echo "The bot did not start. Copy the lines above and send them to Claude."
fi
