import argparse
import asyncio
import math
import sys
from datetime import datetime
from pathlib import Path

from server_config import ConfigError, load_servers


def render(devices: list[dict]) -> str:
    columns = [
        ("device_id", "DEVICE-ID", 20),
        ("measurement", "MEASUREMENT-TYPE", 18),
        ("value", "VALUE", 8),
        ("unit", "UNIT", 8),
        ("updated_at", "LATEST UPDATE", 19),
        ("status", "STATUS", 12),
    ]
    status_labels = {
        "online": "Active",
        "active": "Active",
        "offline": "Offline",
        "connecting": "Connecting",
    }

    header = " | ".join(label.ljust(width) for _, label, width in columns)
    lines = [header, "-" * len(header)]

    for device in devices:
        value = device.get("value")
        timestamp = device.get("updated_at")
        status = device.get("status")

        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
            value_text = f"{value:.1f}"
        else:
            value_text = "-"

        if device.get("is_stale") and value_text != "-":
            value_text += " *"

        if isinstance(timestamp, datetime):
            time_text = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        else:
            time_text = "-"

        cells = {
            "device_id": str(device.get("device_id") or "Okand enhet"),
            "measurement": str(device.get("measurement") or "-"),
            "value": value_text,
            "unit": str(device.get("unit") or "-"),
            "updated_at": time_text,
            "status": status_labels.get(status, "unknown status"),
        }

        row = []
        for key, _, width in columns:
            text = " ".join(cells[key].split())
            if len(text) > width:
                text = text[:width - 3] + "..."
            if key == "value":
                row.append(text.rjust(width))
            else:
                row.append(text.ljust(width))

        lines.append(" | ".join(row))

    if not devices:
        lines.append("No device to show.")

    if any(device.get("is_stale") for device in devices):
        lines.append("\n* Stale reading. Status indicates the connection to the OPC UA server.")

    return "\n".join(lines)


def build_rows(entries, states, last_reads):
    """Anpassa watch() till panelen. Två rader per server."""
    rows = []
    for entry in entries:
        name = entry["name"]
        data = states.get(name)
        connected = data is not None and "error" not in data

        # watch() lägger in en ny dictionary vid varje lyckad läsning.
        # Tiden är när klienten observerade läsningen, inte sensorns mättid.
        if connected:
            previous = last_reads.get(name)
            if previous is None or previous[0] is not data:
                last_reads[name] = (data, datetime.now().astimezone())

        timestamp = last_reads[name][1] if name in last_reads else None
        status = "online" if connected else ("connecting" if data is None else "offline")

        for field, unit in (("Temperature", "C"), ("Humidity", "%")):
