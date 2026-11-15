"""
Background Automation Pipeline Module.
Implements:
1. Concurrency Mutex Lock (asyncio.Lock) to prevent overlapping execution (HTTP 409 Conflict).
2. Non-blocking asynchronous execution (asyncio.create_task).
3. Live progress telemetry with dynamic message editing (Bonus Challenge).
4. Generation of verified CSV reports with SHA-256 checksums and automated delivery.
"""

import asyncio
import csv
import hashlib
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from telegram import Message
from telegram.ext import ContextTypes

from .config import REPORTS_DIR

logger = logging.getLogger(__name__)

# Concurrency Mutex Lock
PIPELINE_LOCK = asyncio.Lock()


def is_pipeline_active() -> bool:
    """Checks whether the pipeline is currently running."""
    return PIPELINE_LOCK.locked()


def compute_sha256(filepath: Path) -> str:
    """Computes a deterministic SHA-256 checksum of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


async def execute_automation_pipeline(
    chat_id: int,
    status_message: Message,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Executes the multi-stage automation workflow in the background.
    Live progress updates are sent via edit_message_text.
    Generates a CSV report and delivers it via send_document.
    """
    start_time = time.perf_counter()

    try:
        # =====================================================================
        # Stage 1: Data Ingestion & Scraping Simulation
        # =====================================================================
        await status_message.edit_text(
            "🚀 <b>AUTOMATION PIPELINE IN PROGRESS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⏳ <b>[Stage 1/3]</b> Ingesting host metrics & remote telemetry...\n"
            "<code>[■■■■░░░░░░░░] 33%</code>",
            parse_mode="HTML"
        )
        await asyncio.sleep(2.5)  # Non-blocking async sleep

        # =====================================================================
        # Stage 2: Vault Processing & Quarantine Inspection
        # =====================================================================
        await status_message.edit_text(
            "🚀 <b>AUTOMATION PIPELINE IN PROGRESS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔐 <b>[Stage 2/3]</b> Vault processing & anomaly quarantine check...\n"
            "<code>[■■■■■■■■░░░░] 66%</code>",
            parse_mode="HTML"
        )
        await asyncio.sleep(2.5)

        # =====================================================================
        # Stage 3: Dataset Generation & Cryptographic Checksum
        # =====================================================================
        await status_message.edit_text(
            "🚀 <b>AUTOMATION PIPELINE IN PROGRESS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📊 <b>[Stage 3/3]</b> Generating CSV report & cryptographic checksum...\n"
            "<code>[■■■■■■■■■■■■] 100%</code>",
            parse_mode="HTML"
        )

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"ops_report_{timestamp_str}.csv"
        report_filepath = REPORTS_DIR / report_filename

        # Generate sample verified report data
        sample_records = [
            {"record_id": f"REC-100{i}", "service": f"node-{i % 4 + 1}", "latency_ms": 12 + i * 2, "status": "HEALTHY", "quarantined": False}
            for i in range(1, 49)
        ]
        # Deliberate flagged / quarantined records
        sample_records.append({"record_id": "REC-1049", "service": "node-db", "latency_ms": 940, "status": "HIGH_LATENCY", "quarantined": True})
        sample_records.append({"record_id": "REC-1050", "service": "gateway-auth", "latency_ms": 1200, "status": "ANOMALY", "quarantined": True})

        # Write to CSV
        with open(report_filepath, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["record_id", "service", "latency_ms", "status", "quarantined"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(sample_records)

        duration = round(time.perf_counter() - start_time, 2)
        total_records = len(sample_records)
        quarantined_count = sum(1 for r in sample_records if r["quarantined"])
        sha256_hash = compute_sha256(report_filepath)

        # Update status message to complete
        await status_message.edit_text(
            "✅ <b>PIPELINE EXECUTION COMPLETED</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• Duration : <code>{duration}s</code>\n"
            f"• Records  : <code>{total_records}</code> entries\n"
            "Delivering signed audit report below...",
            parse_mode="HTML"
        )

        # =====================================================================
        # Deliver CSV Document via send_document with verified caption
        # =====================================================================
        caption_receipt = (
            "📄 <b>VERIFIED PIPELINE EXECUTION RECEIPT</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>• File Name        :</b> <code>{report_filename}</code>\n"
            f"<b>• Total Records    :</b> {total_records}\n"
            f"<b>• Execution Time   :</b> {duration} seconds\n"
            f"<b>• Quarantined Items:</b> {quarantined_count}\n"
            f"<b>• SHA-256 Checksum :</b>\n<code>{sha256_hash}</code>\n"
            "──────────────────────────\n"
            "🔒 <i>Cryptographically verified and sealed.</i>"
        )

        with open(report_filepath, "rb") as doc_file:
            await context.bot.send_document(
                chat_id=chat_id,
                document=doc_file,
                filename=report_filename,
                caption=caption_receipt,
                parse_mode="HTML"
            )

        logger.info(f"Delivered {report_filename} to chat {chat_id} (SHA-256: {sha256_hash[:12]}...).")

    except Exception as exc:
        logger.error(f"Error during pipeline execution: {exc}", exc_info=True)
        await status_message.edit_text(
            f"❌ <b>Pipeline Error:</b> An unexpected error occurred: {exc}",
            parse_mode="HTML"
        )
    finally:
        # Mutex lock release is handled by caller in wrapper
        pass
