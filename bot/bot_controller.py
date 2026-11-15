"""
Telegram Bot Controller Module.
Event-driven microservice using python-telegram-bot (v20+ async).
Coordinates RBAC protection, inline keyboard menus, telemetry, background pipeline triggering,
concurrency mutex lock, and error handling.
"""

import asyncio
import logging
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.error import NetworkError, TimedOut
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .auth import admin_only
from .config import SECURITY_AUDIT_LOG, TELEGRAM_BOT_TOKEN
from .pipeline import PIPELINE_LOCK, execute_automation_pipeline, is_pipeline_active
from .telemetry import get_system_telemetry

logger = logging.getLogger(__name__)


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Generates the interactive inline keyboard for authorized admins."""
    keyboard = [
        [
            InlineKeyboardButton("🖥️ Host Telemetry (/sysinfo)", callback_data="btn_sysinfo"),
            InlineKeyboardButton("🚀 Trigger Pipeline", callback_data="btn_run_pipeline"),
        ],
        [
            InlineKeyboardButton("📜 Security Audit Logs", callback_data="btn_logs"),
            InlineKeyboardButton("ℹ️ Help & Commands", callback_data="btn_help"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# ==============================================================================
# COMMAND HANDLERS (RBAC PROTECTED)
# ==============================================================================

@admin_only
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /start: Verifies authorization and presents interactive operations dashboard.
    """
    user = update.effective_user
    welcome_text = (
        f"👋 <b>Welcome, Administrator {user.first_name}!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🛡️ <b>Secure Infrastructure Ops Microservice</b>\n"
        "Your access is verified via <b>Role-Based Access Control (RBAC)</b>.\n\n"
        "Select an operation below or use slash commands:"
    )
    await update.message.reply_html(welcome_text, reply_markup=get_main_menu_keyboard())


@admin_only
async def sysinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /sysinfo: Immediately returns real-time telemetry, even during pipeline runs.
    """
    active = is_pipeline_active()
    telemetry_report = get_system_telemetry(is_pipeline_running=active)
    await update.message.reply_html(telemetry_report)


@admin_only
async def run_pipeline_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /run_pipeline: Asynchronously triggers the pipeline workflow in the background.
    Enforces the asyncio.Lock mutex to prevent overlapping runs.
    """
    # Requirement 7: Concurrency Mutex Lock check
    if PIPELINE_LOCK.locked():
        conflict_msg = (
            "⚠️ <b>409 Conflict: Pipeline Already Running</b>\n\n"
            "An automation workflow is currently executing in the background.\n"
            "Simultaneous runs are prevented to preserve data integrity."
        )
        await update.message.reply_html(conflict_msg)
        return

    # Acquire lock and dispatch background task
    await PIPELINE_LOCK.acquire()

    status_msg = await update.message.reply_html(
        "🚀 <b>Initializing Background Pipeline...</b>\n"
        "Acquired concurrency lock. Starting asynchronous worker..."
    )

    async def pipeline_worker():
        try:
            await execute_automation_pipeline(
                chat_id=update.effective_chat.id,
                status_message=status_msg,
                context=context,
            )
        finally:
            if PIPELINE_LOCK.locked():
                PIPELINE_LOCK.release()
                logger.info("Pipeline mutex lock released.")

    # Requirement 6 & 8: Dispatch background task so the bot never blocks
    asyncio.create_task(pipeline_worker())


@admin_only
async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /logs: Reads recent security audit log entries.
    """
    if not SECURITY_AUDIT_LOG.exists():
        await update.message.reply_html("📜 <b>Security Audit Log:</b> Log file is empty or not yet created.")
        return

    try:
        with open(SECURITY_AUDIT_LOG, "r", encoding="utf-8") as f:
            lines = f.readlines()
        recent = lines[-10:] if len(lines) > 10 else lines
        if not recent:
            await update.message.reply_html("📜 <b>Security Audit Log:</b> No security incidents recorded.")
            return

        formatted_logs = "".join(recent)
        await update.message.reply_html(
            f"📜 <b>Recent Security Audit Log (Last {len(recent)} entries):</b>\n\n"
            f"<pre>{formatted_logs}</pre>"
        )
    except Exception as e:
        await update.message.reply_html(f"❌ Error reading audit log: {e}")


@admin_only
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /help: Displays command usage instructions.
    """
    help_text = (
        "📖 <b>AVAILABLE BOT COMMANDS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "• /start — Open interactive administrator control menu\n"
        "• /sysinfo — Instant non-blocking host telemetry & health\n"
        "• /run_pipeline — Asynchronously trigger data & vault pipeline\n"
        "• /logs — View recent security audit entries\n"
        "• /help — Show this help manual"
    )
    await update.message.reply_html(help_text)


# ==============================================================================
# INLINE KEYBOARD CALLBACK DISPATCHER
# ==============================================================================

@admin_only
async def callback_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles interactive clicks from inline keyboard buttons.
    """
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "btn_sysinfo":
        active = is_pipeline_active()
        telemetry = get_system_telemetry(is_pipeline_running=active)
        await query.message.reply_html(telemetry)

    elif data == "btn_run_pipeline":
        if PIPELINE_LOCK.locked():
            await query.message.reply_html(
                "⚠️ <b>409 Conflict: Pipeline Already Running</b>\n\n"
                "A background pipeline is already active. Please wait for completion."
            )
            return

        await PIPELINE_LOCK.acquire()
        status_msg = await query.message.reply_html(
            "🚀 <b>Initializing Background Pipeline...</b>\n"
            "Acquired concurrency lock. Starting asynchronous worker..."
        )

        async def worker():
            try:
                await execute_automation_pipeline(
                    chat_id=update.effective_chat.id,
                    status_message=status_msg,
                    context=context,
                )
            finally:
                if PIPELINE_LOCK.locked():
                    PIPELINE_LOCK.release()

        asyncio.create_task(worker())

    elif data == "btn_logs":
        await logs_command(update, context)

    elif data == "btn_help":
        await help_command(update, context)


# ==============================================================================
# ERROR & UNKNOWN COMMAND HANDLERS
# ==============================================================================

async def unknown_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gracefully handles invalid/unknown slash commands."""
    if update.message:
        await update.message.reply_html(
            "❓ <b>Unknown Command</b>\n"
            "Please use /help to see the list of valid operations."
        )


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Gracefully catches timeouts, network dropouts, and unexpected exceptions
    without allowing the bot process to crash.
    """
    error = context.error
    if isinstance(error, (TimedOut, NetworkError)):
        logger.warning(f"Telegram network transient error: {error}")
    else:
        logger.error(f"Unhandled bot exception: {error}", exc_info=error)


def create_bot_application() -> Application:
    """
    Constructs and configures the python-telegram-bot Application instance.
    """
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("sysinfo", sysinfo_command))
    app.add_handler(CommandHandler("run_pipeline", run_pipeline_command))
    app.add_handler(CommandHandler("logs", logs_command))
    app.add_handler(CommandHandler("help", help_command))

    # Register callback query handler for inline menu buttons
    app.add_handler(CallbackQueryHandler(callback_button_handler))

    # Fallback for unrecognized messages
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command_handler))

    # Global error handler
    app.add_error_handler(global_error_handler)

    return app
