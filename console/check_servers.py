"""Person 3: kontrollera serverlistan och gruppens tre OPC UA-noder."""
import argparse
import asyncio
import logging
import math

from server_config import ConfigError, load_servers
from schema import FIELDS, NAMESPACE


async def probe(entry, timeout=5):
    # Importeras bara för nätverkskontrollen. --config-only kräver inga bibliotek.
    from asyncua import Client, ua
    expected_types = (ua.VariantType.String, ua.VariantType.Double, ua.VariantType.String)
    try:
        # En övre gräns för hela kontrollen, utöver timeout per UA-anrop.
        async with asyncio.timeout(timeout):
            async with Client(entry["endpoint"], timeout=timeout) as client:
                ns = await client.get_namespace_index(NAMESPACE)
                nodes = [client.get_node(ua.NodeId("Device." + field, ns)) for field in FIELDS]
                for field, node, expected in zip(FIELDS, nodes, expected_types):
                    actual = await node.read_data_type_as_variant_type()
                    if actual != expected:
                        raise ValueError(f"Device.{field}: förväntade {expected.name}, fick {actual.name}")
                data = dict(zip(FIELDS, await client.read_values(nodes)))
                if data["DeviceId"] != entry["device_id"]:
                    raise ValueError(f"Fel DeviceId: väntade {entry['device_id']}, fick {data['DeviceId']}")
                if not isinstance(data["Unit"], str) or not data["Unit"].strip():
                    raise ValueError("Unit är tom: servern har ännu inget komplett mätvärde")
                value = data["Value"]
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError("Value är inte ett ändligt tal")
                return {"name": entry["name"], "ok": True, "data": data}
    except Exception as exc:
        return {"name": entry["name"], "ok": False,
                "error": type(exc).__name__ + ": " + str(exc)}


async def check_all(entries, timeout=5):
    return await asyncio.gather(*(probe(entry, timeout) for entry in entries))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--servers", default="servers.json")
    parser.add_argument("--config-only", action="store_true", help="Kontrollera filen utan nätverksanslutning")
    parser.add_argument("--timeout", type=float, default=5)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("timeout måste vara ett positivt, ändligt tal")
    try:
        entries = load_servers(args.servers)
    except ConfigError as exc:
        print(f"KONFIGURATIONSFEL: {exc}")
        return 1
    print(f"KONFIGURATION OK: {len(entries)} unika servrar och enhets-ID.")
    if args.config_only:
        print("Endast filen kontrollerad; inga servrar har kontaktats.")
        return 0
    try:
        results = asyncio.run(check_all(entries, args.timeout))
    except ImportError:
        print("Installera projektets bibliotek: python -m pip install -r requirements.txt")
        return 2
    for result in results:
        if result["ok"]:
            data = result["data"]
            print(f"OK {result['name']}: {data['DeviceId']} | {data['Value']:.2f} {data['Unit']}")
        else:
            print(f"FEL {result['name']}: {result['error']}")
    print(f"Godkända servrar: {sum(result['ok'] for result in results)}/{len(results)}")
    print("Kontrollen avser läsning, ID och datatyper; mätvärdets ålder kan inte avgöras med tre noder.")
    return 0 if all(result["ok"] for result in results) else 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nKontroll stoppad.")
        raise SystemExit(130)
