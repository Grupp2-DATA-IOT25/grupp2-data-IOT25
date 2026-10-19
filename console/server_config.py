"""Person 3: läs och kontrollera gruppens serverlista utan nätverksanslutning."""
import ipaddress
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


class ConfigError(ValueError):
    """Fel som användaren kan rätta i servers.json."""


def validate_servers(entries):
    if not isinstance(entries, list) or not entries:
        raise ConfigError("Serverlistan måste vara en lista med minst en server.")
    names, ids, endpoints = set(), set(), set()
    for index, entry in enumerate(entries, start=1):
        label = f"Server {index}"
        if not isinstance(entry, dict):
            raise ConfigError(f"{label}: posten måste vara ett JSON-objekt.")
        for key in ("name", "device_id", "endpoint"):
            value = entry.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ConfigError(f"{label}: {key} måste vara en icke-tom text.")
            if value != value.strip() or any(not char.isprintable() for char in value):
                raise ConfigError(f"{label}: {key} får inte ha inledande/avslutande blanksteg eller kontrolltecken.")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", entry["device_id"]):
            raise ConfigError(f"{label}: device_id ska använda små bokstäver, siffror och bindestreck.")
        endpoint = entry["endpoint"]
        if any(char.isspace() for char in endpoint) or "BYT_TILL" in endpoint.upper():
            raise ConfigError(f"{label}: fyll i en riktig serveradress utan blanksteg eller IP-platshållare.")
        try:
            url = urlsplit(endpoint)
            host, port = url.hostname, url.port
        except ValueError as exc:
            raise ConfigError(f"{label}: ogiltig serveradress eller port.") from exc
        if url.scheme != "opc.tcp" or not host or port is None or not 1 <= port <= 65535:
            raise ConfigError(f"{label}: använd opc.tcp://PI-ADRESS:PORT/telemetry/ med giltig port.")
        if url.username is not None or url.password is not None or url.query or url.fragment:
            raise ConfigError(f"{label}: adressen får inte innehålla inloggning, query eller fragment.")
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            # Tillåt även verkliga värdnamn som alexander-pi.local.
            if re.fullmatch(r"[0-9.]+", host):
                raise ConfigError(f"{label}: ogiltig IP-adress.")
            if len(host) > 253 or any(not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", part)
                                     for part in host.rstrip(".").split(".")):
                raise ConfigError(f"{label}: ogiltigt värdnamn.")
        else:
            if ip.is_unspecified or ip.is_multicast:
                raise ConfigError(f"{label}: använd Pi:ns nåbara adress, inte en lyssnings- eller multicastadress.")
        canonical = (host.lower().rstrip("."), port, url.path or "/")
        if entry["name"].casefold() in names:
            raise ConfigError(f"{label}: name måste vara unikt.")
        if entry["device_id"] in ids:
            raise ConfigError(f"{label}: device_id måste vara unikt.")
        if canonical in endpoints:
            raise ConfigError(f"{label}: samma serveradress förekommer flera gånger.")
        names.add(entry["name"].casefold())
        ids.add(entry["device_id"])
        endpoints.add(canonical)
    return entries


def load_servers(path="servers.json"):
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ConfigError(f"Kunde inte läsa {path}. Kontrollera filnamnet och att du står i projektmappen.") from exc
    except UnicodeError as exc:
        raise ConfigError(f"{path} måste sparas som UTF-8.") from exc
    try:
        entries = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Ogiltig JSON i {path}, rad {exc.lineno}, kolumn {exc.colno}.") from exc
    return validate_servers(entries)
