"""OPC UA-kommunikation f?r gruppens konsolklient."""

import asyncio

from asyncua import Client, ua
from schema import FIELDS, NAMESPACE


async def watch(entry, states, interval):
    name = entry["name"]
    while True:
        try:
            async with Client(entry["endpoint"], timeout=3) as client:
                # Slå upp namespace genom URI; anta inte att index alltid är 2.
                ns = await client.get_namespace_index(NAMESPACE)
                nodes = [client.get_node(ua.NodeId("Device." + field, ns)) for field in FIELDS]
                while True:
                    values = await client.read_values(nodes)
                    data = dict(zip(FIELDS, values))
                    if data["DeviceId"] != entry["device_id"]:
                        raise ValueError("Servern har ett annat DeviceId än servers.json")
                    states[name] = data
                    await asyncio.sleep(interval)
        except Exception as exc:
            # En server som är nere får inte stoppa läsning från övriga servrar.
            states[name] = {"error": type(exc).__name__ + ": " + str(exc)}
            await asyncio.sleep(3)

