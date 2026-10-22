import asyncio
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from asyncua import Server, ua
from check_servers import NAMESPACE, check_all, probe


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def available_port():
    with socket.socket() as connection:
        connection.bind(("127.0.0.1", 0))
        return connection.getsockname()[1]


async def main():
    endpoint = f"opc.tcp://127.0.0.1:{available_port()}/telemetry/"
    entry = {
        "name": "Testenhet",
        "device_id": "alexander-esp32",
        "endpoint": endpoint,
    }
    server = Server()
    await server.init()
    server.set_endpoint(endpoint)
    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
    namespace = await server.register_namespace(NAMESPACE)
    device = await server.nodes.objects.add_object(
        ua.NodeId("Device", namespace), "Device"
    )
    device_id = await device.add_variable(
        ua.NodeId("Device.DeviceId", namespace),
        "DeviceId", "alexander-esp32",
        varianttype=ua.VariantType.String,
    )
    temperature = await device.add_variable(
        ua.NodeId("Device.Temperature", namespace),
        "Temperature", 22.5,
        varianttype=ua.VariantType.Double,
    )
    humidity = await device.add_variable(
        ua.NodeId("Device.Humidity", namespace),
        "Humidity", 48.0,
        varianttype=ua.VariantType.Double,
    )

    async with server:
        result = await probe(entry)
        require(result["ok"], str(result))
        require(result["data"]["Temperature"] == 22.5, "Fel temperatur")
        require(result["data"]["Humidity"] == 48.0, "Fel luftfuktighet")
        print("PASS: nya noder, datatyper och enhets-ID", flush=True)

        await temperature.write_value(25.0, ua.VariantType.Double)
        await humidity.write_value(55.0, ua.VariantType.Double)
        result = await probe(entry)
        require(result["ok"], str(result))
        require(
            result["data"]["Temperature"] == 25.0
            and result["data"]["Humidity"] == 55.0,
            "Ändrade värden kunde inte läsas",
        )
        print("PASS: båda ändrade mätvärdena kan läsas", flush=True)

        await device_id.write_value("fel-esp32", ua.VariantType.String)
        result = await probe(entry)
        require(not result["ok"], "Fel enhets-ID accepterades")
        print("PASS: fel enhets-ID upptäcks", flush=True)
        await device_id.write_value("alexander-esp32", ua.VariantType.String)

        # Behåll en port bunden utan att lyssna: ingen annan testserver
        # kan råka ta den under kontrollen av en otillgänglig server.
        with socket.socket() as unavailable:
            unavailable.bind(("127.0.0.1", 0))
            offline = {
                "name": "Avstängd",
                "device_id": "offline-esp32",
                "endpoint": (
                    f"opc.tcp://127.0.0.1:"
                    f"{unavailable.getsockname()[1]}/telemetry/"
                ),
            }
            results = await check_all([entry, offline], timeout=2.0)
        require(results[0]["ok"], "Den fungerande servern misslyckades")
        require(not results[1]["ok"], "Den otillgängliga servern upptäcktes inte")
        print("PASS: otillgänglig server hindrar inte övriga", flush=True)

    result = await probe(entry, timeout=2.0)
    require(not result["ok"], "Serveravbrott upptäcktes inte")
    print("PASS: serveravbrott upptäcks", flush=True)
    print("\nALLA DESSA KONTROLLER GODKÄNDA", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
