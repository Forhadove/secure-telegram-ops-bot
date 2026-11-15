# 🛡️ Secure Telegram Operations Microservice Bot

> An asynchronous, event-driven Telegram Bot microservice built for infrastructure operations teams. Enables authorized administrators to monitor server health, trigger background automation pipelines concurrently without freezing the bot, and receive cryptographically verified CSV reports.

---

## 🎯 Project Features & Compliance

| # | Requirement | Implementation |
| :--- | :--- | :--- |
| **1** | **Event-Driven Async Architecture** | Built with `python-telegram-bot` (v20+ async) and environment-based configuration (`.env`). |
| **2** | **Reusable RBAC Gatekeeper** | `@admin_only` decorator in `bot/auth.py` validating against `WHITELISTED_ADMINS`. Returns **403 Forbidden: Access Denied** to unauthorized users. |
| **3** | **Security Audit Logging** | Unwhitelisted access attempts (User ID, username, attempted command, and UTC timestamp) are logged to `logs/security_audit.log`. |
| **4** | **Interactive Start Menu** | `/start` verifies RBAC authorization and renders an interactive `InlineKeyboardMarkup` operations dashboard. |
| **5** | **Real-Time Host Telemetry** | `/sysinfo` gathers live OS info, CPU, RAM, Disk utilization, and pipeline state (`🟢 IDLE` or `🟡 RUNNING`). |
| **6** | **Asynchronous Background Execution** | `/run_pipeline` dispatches background tasks via `asyncio.create_task()`, keeping the bot 100% responsive. |
| **7** | **Concurrency Mutex Lock** | Protected by `asyncio.Lock()`. Simultaneous triggers receive **409 Conflict: Pipeline Already Running**. |
| **8** | **Non-Blocking Verification** | Running `/sysinfo` while `/run_pipeline` is actively running returns telemetry instantly without latency or waiting. |
| **9** | **Verified Document Delivery** | Generated CSV dataset is streamed via `send_document` with record count, duration, quarantine count, and SHA-256 checksum. |
| **10**| **Fault Tolerance & Error Handling** | Catches `TimedOut`, `NetworkError`, and unknown commands gracefully without crashing the bot service. |
| **Bonus**| **Live Progress Telemetry** | Dynamically updates a single message via `edit_message_text` across all execution stages (`33%` -> `66%` -> `100%`). |

---

## 📁 Repository Structure

```
telegram_ops_bot/
│
├── bot/
│   ├── __init__.py           # Package exports
│   ├── auth.py               # Reusable RBAC decorator & security audit logging
│   ├── bot_controller.py     # Main async Telegram Bot controller & handlers
│   ├── config.py             # Environment variable loader & strict pre-flight validator
│   ├── pipeline.py           # Multi-stage automation pipeline with mutex lock & progress telemetry
│   └── telemetry.py          # Real-time host telemetry collector (OS, CPU, RAM, Disk)
│
├── logs/
│   ├── .gitkeep              # Directory tracker
│   └── security_audit.log    # Persistent audit log of unauthorized access attempts
│
├── reports/
│   └── .gitkeep              # Generated verified CSV datasets
│
├── .env.example              # Safe environment variable template (NO SECRETS)
├── .gitignore                # Strict exclusion rules (.env, *.log, reports/*.csv)
├── main.py                   # Microservice launcher with startup checks
├── requirements.txt          # Python dependencies (python-telegram-bot, psutil, python-dotenv)
└── README.md                 # Complete documentation & video demonstration script
```

---

## ⚙️ Prerequisites & Setup Guide

### Step 1: Obtain a Telegram Bot Token
1. Open Telegram and search for **[@BotFather](https://t.me/BotFather)**.
2. Send `/newbot` and follow instructions to name your bot.
3. Copy the HTTP API token provided by BotFather.

### Step 2: Find Your Telegram User ID
1. Search for **[@userinfobot](https://t.me/userinfobot)** on Telegram.
2. Send `/start`. The bot will reply with your numeric `Id` (e.g. `123456789`).

### Step 3: Clone & Configure Environment Variables
Navigate to the project directory:
```bash
cd telegram_ops_bot
```

Copy `.env.example` to create your local `.env`:
```bash
cp .env.example .env
```
*(On Windows PowerShell: `Copy-Item .env.example .env`)*

Open `.env` and fill in your values:
```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
WHITELISTED_ADMINS=123456789
```
> ⚠️ **CRITICAL SECURITY NOTE:** Never commit `.env` or your real bot token to Git. `.gitignore` is pre-configured to keep your secrets safe.

### Step 4: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 5: Start the Bot Microservice
```bash
python main.py
```

---

## 🤖 Available Bot Commands

| Command | Description | Access Level |
| :--- | :--- | :--- |
| `/start` | Verifies RBAC authorization and renders the interactive dashboard | Administrator Only |
| `/sysinfo` | Returns real-time host telemetry (CPU, RAM, Disk, OS, Pipeline state) | Administrator Only |
| `/run_pipeline` | Asynchronously triggers background data collection and vault workflow | Administrator Only |
| `/logs` | Displays recent security audit log entries | Administrator Only |
| `/help` | Shows usage instructions and manual | Administrator Only |

---

## 🔍 Deep-Dive: Core Technical Concepts

### 1. Reusable RBAC Gatekeeper (`bot/auth.py`)
Access control is implemented as a reusable asynchronous Python decorator (`@admin_only`). It intercepts incoming updates before any handler logic executes:
```python
def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in WHITELISTED_ADMINS:
            record_unauthorized_attempt(user_id, username, command)
            await update.message.reply_html("⛔ <b>403 Forbidden: Access Denied</b>")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper
```
Any unauthorized user attempting a command or callback button is immediately rebuffed with a 403 Forbidden message, and the incident is appended to `logs/security_audit.log` with a UTC timestamp.

### 2. Concurrency Mutex Lock (`bot/pipeline.py`)
To prevent overlapping workflows that could corrupt output datasets, an `asyncio.Lock()` mutex guard is enforced:
```python
if PIPELINE_LOCK.locked():
    await update.message.reply_html("⚠️ <b>409 Conflict: Pipeline Already Running</b>")
    return

await PIPELINE_LOCK.acquire()
asyncio.create_task(pipeline_worker())  # Background execution
```
If a user triggers `/run_pipeline` while an existing run is in progress, the bot replies instantly with **409 Conflict** and rejects the redundant execution.

### 3. Non-Blocking Event-Driven Concurrency
Because the pipeline is dispatched via `asyncio.create_task()`, Python's asyncio event loop is never blocked. While the pipeline performs stages in the background, administrators can query `/sysinfo` at any millisecond and receive an immediate response showing:
```text
• Pipeline State : 🟡 RUNNING (Background Task Active)
```

### 4. Verified Document Streaming & SHA-256 Sealing
Upon pipeline completion:
1. A timestamped CSV dataset is written to `reports/`.
2. A cryptographic SHA-256 checksum is computed over the raw file bytes:
   ```python
   hasher = hashlib.sha256()
   while chunk := f.read(65536):
       hasher.update(chunk)
   ```
3. The report is delivered using `context.bot.send_document()` with a tamper-evident audit receipt.

---

## 🎥 Demonstration Video Script (60–90 Seconds)

Follow this structured script when recording your Loom or Google Drive demonstration:

| Time | Scene / Action | What to Say / Demonstrate |
| :--- | :--- | :--- |
| **0:00 - 0:15** | **(a) Unauthorized User Rejection** | Send `/start` from an account NOT in `WHITELISTED_ADMINS`. Show the bot instantly reply: `⛔ 403 Forbidden: Access Denied`. Briefly show `logs/security_audit.log` capturing the event. |
| **0:15 - 0:35** | **(b) Authorized Admin Menu & Pipeline Start** | Switch to the whitelisted admin account. Send `/start` to show the interactive inline keyboard menu. Click **"🚀 Trigger Pipeline"** (or type `/run_pipeline`). Show live stage telemetry: `[Stage 1/3] 33%` -> `[Stage 2/3] 66%`. |
| **0:35 - 0:50** | **(c) Non-Blocking Telemetry & Concurrency Lock** | **While the pipeline is actively running**, immediately send `/sysinfo`. Show that the bot replies instantly without waiting, displaying `Pipeline State: 🟡 RUNNING`. Then trigger `/run_pipeline` again to show the **409 Conflict: Pipeline Already Running** rejection. |
| **0:50 - 1:15** | **(d) Verified CSV Delivery** | Watch the pipeline complete. Show Telegram receiving the generated CSV file with the signed receipt (Record count, execution time, quarantine count, and SHA-256 checksum). |

---

## 📄 License
This project is open-source and intended for academic evaluation and enterprise DevOps operations.
