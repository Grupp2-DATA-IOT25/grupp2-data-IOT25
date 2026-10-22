"""Kontrollera konfiguration och gruppens tre OPC UA-variabelnoder."""
import argparse
import asyncio
import math

from server_config import ConfigError, load_servers

NAMESPACE = "urn:nackademin:group2:telemetry"
FIELDS = {
    "DeviceId": "String",
    "Temperature": "Double",
    "Humidity": "Double",
}


async def probe(entry, timeout=5.0):
    from asyncua import Client, ua

    try:
        async with asyncio.timeout(timeout):
            async with Client(entry["endpoint"], timeout=timeout) as client:
                namespace = await client.get_namespace_index(NAMESPACE)
                nodes = [
                    client.get_node(ua.NodeId(f"Device.{field}", namespace))
                    for field in FIELDS
                ]
                for (field, expected_type), node in zip(FIELDS.items(), nodes):
                    actual_type = await node.read_data_type_as_variant_type()
                    if actual_type != getattr(ua.VariantType, expected_type):
                        raise ValueError(
                            f"Device.{field} ska vara {expected_type}, "
                            f"men är {actual_type.name}"
                        )
                data = dict(zip(FIELDS, await client.read_values(nodes)))
                if data["DeviceId"] != entry["device_id"]:
                    raise ValueError(
                        f"Fel enhets-ID: {data['DeviceId']!r}. "
                        f"Förväntat: {entry['device_id']!r}"
                    )
                for field in ("Temperature", "Humidity"):
                    value = data[field]
                    if (
                        isinstance(value, bool)
                        or not isinstance(value, (int, float))
                        or not math.isfinite(value)
                    ):
                        raise ValueError(f"Device.{field} saknar ett giltigt tal")
                return {"name": entry["name"], "ok": True, "data": data}
    except Exception as error:
        return {
            "name": entry["name"],
            "ok": False,
            "error": f"{type(error).__name__}: {error}",
        }


async def check_all(entries, timeout=5.0):
    return await asyncio.gather(*(probe(entry, timeout) for entry in entries))


def main():
    parser = argparse.ArgumentParser(description="Kontrollera gruppens OPC UA-servrar.")
    parser.add_argument("--servers", default="servers.json")
    parser.add_argument("--config-only", action="store_true")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout måste vara ett positivt, ändligt tal")
    try:
        entries = load_servers(args.servers)
    except ConfigError as error:
        parser.error(str(error))
    print(f"KONFIGURATION OK: {len(entries)} unika servrar och enhets-ID.")
    if args.config_only:
        print("Endast filen kontrollerad; inga servrar har kontaktats.")
        return 0
    try:
        results = asyncio.run(check_all(entries, args.timeout))
    except ModuleNotFoundError as error:
        print(f"Paket saknas: {error.name}. Installera requirements.txt.")
        return 2
    for result in results:
        if result["ok"]:
            data = result["data"]
            print(
                f"OK: {result['name']} | {data['DeviceId']} | "
                f"{data['Temperature']:.1f} C | {data['Humidity']:.1f} %"
            )
        else:
            print(f"FEL: {result['name']} | {result['error']}")
    passed = sum(result["ok"] for result in results)
    print(f"\nGodkända kontroller: {passed}/{len(results)}")
    print("Kontrollen visar läsbara värden, inte när sensorn senast skickade data.")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
