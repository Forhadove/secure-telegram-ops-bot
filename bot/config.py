"""
Configuration and Environment Management Module.
Loads environment variables from .env and provides strict validation.
"""

import os
import sys
from pathlib import Path
from typing import Set
from dotenv import load_dotenv

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"
SECURITY_AUDIT_LOG = LOGS_DIR / "security_audit.log"

LOGS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Load environment variables (override=True ensures latest values are always reloaded)
ENV_FILE = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_FILE, override=True)

# Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ADMIN_IDS_RAW = os.getenv("WHITELISTED_ADMINS", "").strip()


def parse_whitelisted_admins(raw_ids: str) -> Set[int]:
    """Parses a comma-separated string of user IDs into a set of integers."""
    admins: Set[int] = set()
    if not raw_ids:
        return admins

    for part in raw_ids.split(","):
        cleaned = part.strip()
        if cleaned.isdigit():
            admins.add(int(cleaned))
    return admins


WHITELISTED_ADMINS: Set[int] = parse_whitelisted_admins(ADMIN_IDS_RAW)


def validate_config() -> None:
    """
    Validates essential environment variables.
    Exits with an informative message if required secrets are missing.
    """
    errors = []

    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        errors.append(
            "Missing TELEGRAM_BOT_TOKEN in .env! "
            "Please create a bot via @BotFather on Telegram and set the token in your .env file."
        )

    if not WHITELISTED_ADMINS:
        errors.append(
            "Missing or invalid WHITELISTED_ADMINS in .env! "
            "Add your Telegram user ID (comma-separated if multiple, e.g. WHITELISTED_ADMINS=123456789)."
        )

    if errors:
        print("\n" + "=" * 70)
        print("❌ CONFIGURATION ERROR - MISSING ENVIRONMENT VARIABLES")
        print("=" * 70)
        for err in errors:
            print(f" • {err}")
        print("\n💡 Please copy .env.example to .env and configure your credentials.")
        print("=" * 70 + "\n")
        sys.exit(1)
