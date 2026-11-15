"""
Host Telemetry & System Health Diagnostics Module.
Gathers real-time host metrics: OS, architecture, Python version, CPU, RAM, Disk,
and current automation pipeline state.
"""

import os
import platform
import sys
import psutil
from datetime import datetime


def format_bytes(bytes_num: int) -> str:
    """Formats raw bytes into human-readable GiB / MiB."""
    for unit in ["B", "KiB", "MiB", "GiB", "TiB"]:
        if bytes_num < 1024.0:
            return f"{bytes_num:.1f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.1f} PiB"


def get_system_telemetry(is_pipeline_running: bool) -> str:
    """
    Collects real-time host telemetry and formats it into a clean,
    professional Telegram HTML report.
    """
    # Host & OS Info
    os_name = f"{platform.system()} {platform.release()}"
    architecture = platform.machine()
    python_ver = platform.python_version()
    hostname = platform.node()

    # CPU & RAM Metrics
    cpu_usage = psutil.cpu_percent(interval=None)
    cpu_count = psutil.cpu_count(logical=True)

    ram = psutil.virtual_memory()
    ram_total = format_bytes(ram.total)
    ram_used = format_bytes(ram.used)
    ram_pct = ram.percent

    # Disk Metrics (current workspace drive)
    current_drive = os.path.splitdrive(os.path.abspath(__file__))[0] or "/"
    disk = psutil.disk_usage(current_drive)
    disk_total = format_bytes(disk.total)
    disk_used = format_bytes(disk.used)
    disk_pct = disk.percent

    # Pipeline State
    if is_pipeline_running:
        pipeline_status = "🟡 <b>RUNNING</b> (Background Task Active)"
    else:
        pipeline_status = "🟢 <b>IDLE</b> (Available)"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = (
        "🖥️ <b>HOST TELEMETRY & SYSTEM HEALTH</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>• Pipeline State   :</b> {pipeline_status}\n"
        f"<b>• Host / Node       :</b> <code>{hostname}</code>\n"
        f"<b>• OS Identifier    :</b> {os_name}\n"
        f"<b>• Architecture     :</b> {architecture}\n"
        f"<b>• Python Runtime   :</b> v{python_ver}\n"
        "──────────────────────────\n"
        f"<b>• CPU Utilization  :</b> {cpu_usage}% ({cpu_count} logical cores)\n"
        f"<b>• Memory (RAM)      :</b> {ram_used} / {ram_total} (<b>{ram_pct}%</b>)\n"
        f"<b>• Disk ({current_drive})      :</b> {disk_used} / {disk_total} (<b>{disk_pct}%</b>)\n"
        "──────────────────────────\n"
        f"🕒 <i>Timestamp: {timestamp}</i>"
    )
    return report
