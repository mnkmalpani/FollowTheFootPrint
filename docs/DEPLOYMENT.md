# Deployment & Scheduling Guide

Run the FTF scanner on a server so it produces a fresh demand-zone report every
morning before the market opens (e.g. 08:45 IST for NSE).

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Linux server | Ubuntu 18.04+ or any systemd-based distro |
| [UV](https://docs.astral.sh/uv/) | Installs itself **and** manages Python — no system Python 3.11 required |
| git | For cloning and pulling updates |

> **Note on Python:** FTF requires Python 3.11+. Ubuntu 18.04 ships with
> Python 3.6, but **UV handles this automatically** — `uv sync` downloads
> and manages its own Python 3.11+ toolchain. You do not need to install
> Python from a PPA or build from source.
>
> **Tip:** A 4 GB / 4-core VPS is more than enough.
> The scanner is CPU-light; the bottleneck is yfinance network I/O.

---

## 1. Deployment

### One-time setup (first deploy)

```bash
# 0. SSH into the server
ssh user@YOUR_SERVER_IP

# 1. Install UV (one-liner; also manages Python 3.11+ for you)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc        # or re-login so `uv` is on PATH

# 2. Install git if missing
sudo apt-get update && sudo apt-get install -y git

# 3. Set timezone to IST (so cron 08:45 = 08:45 IST)
sudo timedatectl set-timezone Asia/Kolkata

# 4. Clone the repo
git clone <repo-url> ~/followthefootprints
cd ~/followthefootprints

# 5. Run setup (uv sync downloads Python 3.11 + deps, creates .env)
./setup.sh

# 6. Configure Telegram alerts
nano .env   # add TELEGRAM_TOKEN and TELEGRAM_CHAT_ID

# 7. Verify it runs
uv run ftf --mode weekly --index nifty100
```

After step 7 you should see a `nifty100_weekly.csv` in the project root
and (if Telegram is configured) a message in your chat.

### Incremental updates (subsequent deploys)

```bash
cd ~/followthefootprints
git pull origin main
uv sync          # re-resolve deps if pyproject.toml changed
```

Or use the Makefile shortcut:

```bash
make update      # git pull && uv sync
```

No restart is needed — cron/systemd picks up changes on the next scheduled run.

---

## 2. Scheduling

### Option A: cron — simple and fast

Best for: single server, quick setup, "I just need it to run."

```bash
crontab -e
```

Add the following (assumes timezone was set to IST during one-time setup):

```cron
# Ensure cron can find uv (installed to ~/.local/bin by default)
PATH=/usr/local/bin:/usr/bin:/bin:/home/YOUR_USERNAME/.local/bin

# Run FTF at 08:45 IST, Mon–Fri
45 8 * * 1-5  cd ~/followthefootprints && uv run ftf --log-file ~/ftf.log 2>&1
```

> If your server timezone is UTC instead of IST, use `15 3` (03:15 UTC = 08:45 IST).

Replace `YOUR_USERNAME` with your Linux username, or use the full path to `uv`
(`which uv` to find it).

**What this does:**

- `PATH=...` — cron runs with a minimal PATH; this line ensures it finds `uv`.
- `45 8 * * 1-5` — minute 45, hour 8, every weekday (Mon–Fri).
- `--log-file ~/ftf.log` — appends timestamped logs to `~/ftf.log`
  (in addition to stderr, which cron captures in mail).
- If the run crashes, FTF sends a Telegram failure alert automatically
  (when `TELEGRAM_TOKEN` / `TELEGRAM_CHAT_ID` are set in `.env`).

**Verify cron is running:**

```bash
# List your crontab
crontab -l

# Check last few lines of the log after the scheduled time
tail -30 ~/ftf.log
```

### Option B: systemd timer — scalable and observable

Best for: production servers, multiple schedules, centralised logging via
`journalctl`, automatic retries, dependency ordering.

#### Step 1 — Create the service unit

```bash
sudo tee /etc/systemd/system/ftf.service > /dev/null << 'EOF'
[Unit]
Description=FollowTheFootPrints demand-zone scanner
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/followthefootprints
EnvironmentFile=/home/YOUR_USERNAME/followthefootprints/.env
ExecStart=/home/YOUR_USERNAME/.local/bin/uv run ftf --mode weekly --index nifty100
TimeoutStartSec=600

# Restart on failure (oneshot retries via systemd)
Restart=on-failure
RestartSec=120
StartLimitIntervalSec=900
StartLimitBurst=3
EOF
```

Replace `YOUR_USERNAME` with your actual Linux username.

#### Step 2 — Create the timer unit

```bash
sudo tee /etc/systemd/system/ftf.timer > /dev/null << 'EOF'
[Unit]
Description=Run FTF scanner before market open

[Timer]
OnCalendar=Mon..Fri 08:45
Persistent=true

[Install]
WantedBy=timers.target
EOF
```

> `Persistent=true` means if the server was off at 08:45, the timer fires
> immediately on next boot — you never miss a run.

#### Step 3 — Enable and start

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ftf.timer

# Verify the timer is active
systemctl list-timers ftf.timer
```

#### Step 4 — Check logs

```bash
# Live follow
journalctl -u ftf.service -f

# Last run
journalctl -u ftf.service -n 50 --no-pager

# Since yesterday
journalctl -u ftf.service --since yesterday
```

#### Manually trigger a run (outside schedule)

```bash
sudo systemctl start ftf.service
journalctl -u ftf.service -n 30 --no-pager
```

### Comparison

| | cron | systemd timer |
|---|---|---|
| Setup time | 2 min | 10 min |
| Logging | Manual (`--log-file`) | Built-in (`journalctl`) |
| Missed-run catch-up | No | Yes (`Persistent=true`) |
| Retry on failure | No | Yes (`Restart=on-failure`) |
| Dependency ordering | No | Yes (`After=network-online.target`) |
| Multiple schedules | Duplicate crontab lines | One timer, multiple `OnCalendar=` |

**Recommendation:** Start with cron. Move to systemd when you need retries,
journal logging, or multiple indices/modes on different schedules.

---

## 3. Monitoring & Failure Alerts

### Built-in Telegram alerts

FTF already sends results to Telegram on **success**. As of the latest
update, it also sends a failure alert on **crash** — no extra setup needed
beyond having `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`.

| Event | Telegram message |
|-------|------------------|
| Success | CSV + summary (stocks found, index, interval) |
| Failure | Alert with index/mode + "check server logs" |

### Checking the last run

```bash
# cron: check the log file
tail -50 ~/ftf.log

# systemd: check the journal
journalctl -u ftf.service -n 50 --no-pager

# Quick health check: was the CSV updated today?
ls -la ~/followthefootprints/nifty100_weekly.csv
stat --format='%y' ~/followthefootprints/nifty100_weekly.csv
```

### Log rotation (cron)

Prevent `~/ftf.log` from growing forever:

```bash
sudo tee /etc/logrotate.d/ftf > /dev/null << 'EOF'
/home/YOUR_USERNAME/ftf.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
}
EOF
```

systemd journal rotation is handled automatically by `journald.conf`.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Fatal error (exception during analysis) |
| 130 | Interrupted (Ctrl+C / SIGINT) |

---

## 4. Running Multiple Scans

You can schedule multiple index/mode combinations. For cron, add more lines:

```cron
45 8 * * 1-5  cd ~/followthefootprints && uv run ftf --mode weekly --index nifty100 --log-file ~/ftf.log 2>&1
50 8 * * 1-5  cd ~/followthefootprints && uv run ftf --mode daily  --index nifty50  --log-file ~/ftf.log 2>&1
```

For systemd, create additional service/timer pairs (e.g. `ftf-daily-nifty50.service`),
or parameterise with a template unit:

```bash
# ftf@.service — template unit (note the @ in the filename)
# Usage: systemctl start ftf@"weekly-nifty100"

[Service]
ExecStart=/home/YOUR_USERNAME/.local/bin/uv run ftf --mode %i
```

---

## 5. Quick Reference

```bash
# SSH into the server
ssh user@YOUR_SERVER_IP

# First-time deploy
curl -LsSf https://astral.sh/uv/install.sh | sh && source ~/.bashrc
git clone <repo-url> ~/followthefootprints && cd ~/followthefootprints && ./setup.sh

# Update
cd ~/followthefootprints && make update

# Manual run
uv run ftf

# Manual run with log file
uv run ftf --log-file ~/ftf.log

# Check cron schedule
crontab -l

# Check systemd timer
systemctl list-timers ftf.timer

# Last systemd run logs
journalctl -u ftf.service -n 50 --no-pager

# Tail cron log
tail -f ~/ftf.log
```
