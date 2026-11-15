"""
Role-Based Access Control (RBAC) Gatekeeper & Security Audit Logger.
Validates incoming Telegram user IDs against WHITELISTED_ADMINS,
rejects unauthorized users with HTTP 403 Forbidden, and maintains an audit log.
"""

import logging
from datetime import datetime, timezone
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

from .config import SECURITY_AUDIT_LOG, WHITELISTED_ADMINS

logger = logging.getLogger(__name__)


def record_unauthorized_attempt(user_id: int, username: str, command: str, full_name: str = "") -> None:
    """
    Appends unauthorized access attempts to the security audit log.
    Includes User ID, username, attempted command, and UTC timestamp.
    """
    timestamp_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    clean_username = f"@{username}" if username else "NO_USERNAME"
    clean_name = full_name.strip() if full_name else "Unknown"

    log_entry = (
        f"[{timestamp_utc}] [SECURITY ALERT 403] "
        f"Unauthorized Access Attempt | UserID: {user_id} | "
        f"Username: {clean_username} ({clean_name}) | "
        f"Attempted Action: {command}\n"
    )

    try:
        with open(SECURITY_AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(log_entry)
        logger.warning(f"🚨 Logged unauthorized attempt by UserID {user_id} ({clean_username}) for '{command}'.")
    except Exception as exc:
        logger.error(f"Failed to write to security audit log: {exc}")


def admin_only(func):
    """
    Reusable async decorator enforcing Role-Based Access Control (RBAC).
    Intercepts calls to commands and callbacks.
    Unauthorized users receive a 403 Forbidden response and are recorded in the audit log.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return

        user_id = user.id
        username = user.username or ""
        full_name = user.full_name or ""

        # Determine the action/command attempted
        command = "Unknown"
        if update.message and update.message.text:
            command = update.message.text.split()[0]
        elif update.callback_query and update.callback_query.data:
            command = f"callback:{update.callback_query.data}"

        # RBAC Check
        if user_id not in WHITELISTED_ADMINS:
            record_unauthorized_attempt(user_id, username, command, full_name)

            denial_message = (
                "⛔ <b>403 Forbidden: Access Denied</b>\n\n"
                f"Your User ID (<code>{user_id}</code>) is not on the administrator whitelist.\n"
                "⚠️ <i>This incident has been permanently logged in the security audit journal.</i>"
            )

            if update.callback_query:
                await update.callback_query.answer("⛔ 403 Forbidden: Access Denied", show_alert=True)
                await update.callback_query.message.reply_html(denial_message)
            elif update.message:
                await update.message.reply_html(denial_message)

            return  # Stop execution for unauthorized users

        # Authorized admin -> proceed to handler
        return await func(update, context, *args, **kwargs)

    return wrapper
