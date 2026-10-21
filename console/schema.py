"""Förslag till gruppens gemensamma kontrakt. Samma NodeId på varje server."""
import json
import math

NAMESPACE = "urn:nackademin:group2:telemetry"
# Gruppens tre överenskomna noder. Extra statusnoder får finnas på en server,
# men klienten kräver dem inte.
FIELDS = ("DeviceId", "Temperature", "Humidity")


def parse_telemetry(payload: bytes, expected_device: str) -> dict:
    """Avvisa fel enhet, trasig JSON och värden som inte är ändliga tal."""
    data = json.loads(payload.decode("utf-8"))
    if not isinstance(data, dict) or data.get("deviceId") != expected_device:
        raise ValueError("Fel deviceId eller fel JSON-struktur")
    value = data.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("value måste vara ett tal")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("value måste vara ett ändligt tal")
    unit = data.get("unit")
    if not isinstance(unit, str) or not unit.strip() or len(unit) > 32:
        raise ValueError("unit måste vara en kort, icke-tom sträng")
    return {"deviceId": expected_device, "value": value, "unit": unit}
