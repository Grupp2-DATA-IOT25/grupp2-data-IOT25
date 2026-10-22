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
            rows.append({
                "device_id": data.get("DeviceId", entry["device_id"]) if connected else entry["device_id"],
                "measurement": field,
                "value": data.get(field) if connected else None,
                "unit": unit,
                "updated_at": timestamp,
                "status": status,
                "is_stale": False,
            })
    return rows


def screen_text(entries, states, last_reads):
    rows = build_rows(entries, states, last_reads)
    connected = sum(
        entry["name"] in states and "error" not in states[entry["name"]]
        for entry in entries
    )
    parts = [
        "GRUPPENS OPC UA-TELEMETRI",
        f"Servrar: {len(entries)} | Anslutna: {connected}",
        "",
        render(rows),
        "",
        "LATEST UPDATE = senaste lyckade läsning observerad av klienten.",
        "STATUS visar OPC UA-anslutningen, inte sensorvärdets ålder.",
        "Avsluta med Ctrl + C.",
    ]
    for entry in entries:
        data = states.get(entry["name"], {})
        if "error" in data:
            error = " ".join(str(data["error"]).split())
            parts.append(f"{entry['name']}: {error}")
    return "\n".join(parts)


async def run(entries, interval=2.0):
    from opcua_watch import watch

    states = {}
    last_reads = {}
    tasks = [
        asyncio.create_task(watch(entry, states, interval))
        for entry in entries
    ]
    try:
        while True:
            text = screen_text(entries, states, last_reads)
            if sys.stdout.isatty():
                print("\033[2J\033[H", end="")
            print(text, flush=True)
            await asyncio.sleep(interval)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def main():
    parser = argparse.ArgumentParser(description="Gruppens OPC UA-konsolklient")
    parser.add_argument(
        "--servers", default=str(Path(__file__).with_name("servers.json"))
    )
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()
    if not math.isfinite(args.interval) or args.interval <= 0:
        parser.error("--interval måste vara ett positivt, ändligt tal")
    try:
        entries = load_servers(args.servers)
    except ConfigError as error:
        parser.error(str(error))
    try:
        asyncio.run(run(entries, args.interval))
    except ModuleNotFoundError as error:
        print(f"Paket eller fil saknas: {error.name}", file=sys.stderr)
        print(
            "Installera requirements.txt och kontrollera att opcua_watch.py "
            "och schema.py finns i samma mapp som main.py.", file=sys.stderr
        )
        return 1
    except KeyboardInterrupt:
        print("\nKonsolklienten stoppad.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
