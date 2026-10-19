"""Gruppens konsolklient: läser samtliga listade OPC UA-servrar samtidigt."""
import argparse
import asyncio
import json
import logging
import sys

from asyncua import Client, ua

from schema import FIELDS, NAMESPACE
from terminal_panel import render


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


async def run(entries, interval):
    states = {}
    tasks = [asyncio.create_task(watch(entry, states, interval)) for entry in entries]
    try:
        while True:
            # Uppdatera samma panel i en interaktiv terminal. Loggar till fil
            # får vanliga textblock utan terminalkommandon.
            if sys.stdout.isatty():
                print("\033[2J\033[H", end="")
            print(render(entries, states), flush=True)
            await asyncio.sleep(interval)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--servers", default="servers.json")
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()
    logging.basicConfig(level=logging.ERROR)
    with open(args.servers, encoding="utf-8") as file:
        entries = json.load(file)
    if not isinstance(entries, list) or not entries:
        raise ValueError("servers.json måste innehålla minst en server")
    if len({item["name"] for item in entries}) != len(entries):
        raise ValueError("Varje name måste vara unikt")
    if args.interval <= 0:
        raise ValueError("interval måste vara större än 0")
    try:
        asyncio.run(run(entries, args.interval))
    except KeyboardInterrupt:
        print("\nKlient stoppad.")
