"""Gruppens gemensamma datakontrakt."""
import json
import math

NAMESPACE = "urn:nackademin:group2:telemetry"
FIELDS = ("DeviceId", "Temperature", "Humidity")


def parse_telemetry(payload: bytes, expected_device: str) -> dict:
    """Kontrollera enhets-ID och båda mätvärdena."""
    data = json.loads(payload.decode("utf-8"))

    if not isinstance(data, dict):
        raise ValueError("Meddelandet måste vara ett JSON-objekt")

    if data.get("deviceId") != expected_device:
        raise ValueError("Fel deviceId")

    result = {"deviceId": expected_device}

    for field in ("temperature", "humidity"):
        value = data.get(field)

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{field} måste vara ett tal")

        value = float(value)

        if not math.isfinite(value):
            raise ValueError(f"{field} måste vara ett ändligt tal")

        result[field] = value

    return result
