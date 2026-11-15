"""
Main Launcher for Secure Telegram Operations Microservice Bot.
Validates environment configuration and starts the non-blocking event loop.
"""

import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from bot.config import (
    TELEGRAM_BOT_TOKEN,
    WHITELISTED_ADMINS,
    validate_config,
)
from bot.bot_controller import create_bot_application


def setup_logging():
    """Sets up clean console logging."""
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )
    # Silence noisy HTTP connection logs from httpx/httpcore
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def main():
    setup_logging()
    logger = logging.getLogger("main")

    print("=" * 70)
    print("      🛡️ SECURE TELEGRAM OPS MICROSERVICE BOT CONTROLLER")
    print("=" * 70)

    # Pre-flight environment check
    validate_config()

    admin_count = len(WHITELISTED_ADMINS)
    logger.info(f"Loaded {admin_count} whitelisted administrator ID(s): {WHITELISTED_ADMINS}")
    logger.info("Initializing event-driven ApplicationBuilder...")

    try:
        app = create_bot_application()
        logger.info("✅ Bot initialized successfully. Starting non-blocking polling...")
        print("-" * 70)
        print("🤖 Bot is LIVE and listening for commands! (Press Ctrl+C to stop)")
        print("-" * 70)
        app.run_polling(drop_pending_updates=True)
    except KeyboardInterrupt:
        logger.info("Bot service stopped by user.")
    except Exception as exc:
        logger.critical(f"Fatal error starting bot service: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
