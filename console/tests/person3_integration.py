"""Person 3:s automatiska kontroll av riktiga lokala OPC UA-testservrar."""
import asyncio
import logging
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from asyncua import Server, ua
from check_servers import probe, check_all
from console_client import watch
from schema import NAMESPACE


async def start_server(port, device_id, *, value_type=ua.VariantType.Double, omit_unit=False, namespace=NAMESPACE):
    server=Server()
    await server.init()
    endpoint=f"opc.tcp://127.0.0.1:{port}/telemetry/"
    server.set_endpoint(endpoint)
    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
    ns=await server.register_namespace(namespace)
    obj=await server.nodes.objects.add_object(ua.NodeId("Device",ns),"Device")
    await obj.add_variable(ua.NodeId("Device.DeviceId",ns),"DeviceId",device_id)
    node=await obj.add_variable(ua.NodeId("Device.Value",ns),"Value",
                              ua.Variant(22.5,value_type))
    if not omit_unit:
        await obj.add_variable(ua.NodeId("Device.Unit",ns),"Unit","C")
    await server.start()
    return server,node,{"name":device_id,"device_id":device_id,"endpoint":endpoint}


async def until(predicate, seconds=20):
    for _ in range(int(seconds*10)):
        if predicate():
            return
        await asyncio.sleep(.1)
    raise AssertionError("Väntat tillstånd uppnåddes inte")


async def main():
    logging.basicConfig(level=logging.ERROR)
    servers=[]
    jobs=[]
    try:
        first,node1,entry1=await start_server(4855,"test-one")
        servers.append(first)
        second,node2,entry2=await start_server(4856,"test-two")
        servers.append(second)
        results=await check_all([entry1,entry2])
        assert all(result["ok"] for result in results),results
        assert results[0]["data"]["Unit"]=="C"
        print("PASS: två servrar med exakt tre noder och rätt datatyper/ID")

        wrong=await probe(dict(entry1,device_id="wrong-id"))
        assert not wrong["ok"] and "Fel DeviceId" in wrong["error"],wrong
        print("PASS: fel enhets-ID upptäcks")

        bad,_,bad_entry=await start_server(4857,"bad-type",value_type=ua.VariantType.Float)
        servers.append(bad)
        result=await probe(bad_entry)
        assert not result["ok"] and "förväntade Double" in result["error"],result
        await bad.stop()
        servers.remove(bad)

        missing,_,missing_entry=await start_server(4857,"missing-unit",omit_unit=True)
        servers.append(missing)
        assert not (await probe(missing_entry))["ok"]
        await missing.stop()
        servers.remove(missing)

        foreign,_,foreign_entry=await start_server(4857,"wrong-namespace",namespace="urn:other:test")
        servers.append(foreign)
        assert not (await probe(foreign_entry))["ok"]
        await foreign.stop()
        servers.remove(foreign)
        print("PASS: fel datatyp, saknad nod och fel namespace upptäcks")

        offline={"name":"offline","device_id":"offline","endpoint":"opc.tcp://127.0.0.1:4898/telemetry/"}
        results=await check_all([entry1,offline,entry2],timeout=2)
        assert [item["ok"] for item in results]==[True,False,True],results
        print("PASS: otillgänglig server hindrar inte kontroll av övriga")

        states={}
        jobs=[asyncio.create_task(watch(entry,states,.1)) for entry in (entry1,entry2)]
        await until(lambda: states.get("test-one",{}).get("Value")==22.5
                    and states.get("test-two",{}).get("Value")==22.5)
        await node1.write_value(24.5)
        await until(lambda: states["test-one"].get("Value")==24.5)
        print("PASS: konsolklienten läser ändrade värden automatiskt")

        await first.stop()
        servers.remove(first)
        await until(lambda: "error" in states["test-one"])
        await node2.write_value(25.5)
        await until(lambda: states["test-two"].get("Value")==25.5)
        restarted,newnode,_=await start_server(4855,"test-one")
        servers.append(restarted)
        await newnode.write_value(26.5)
        await until(lambda: states["test-one"].get("Value")==26.5)
        print("PASS: serveravbrott isoleras och klienten återansluter efter omstart")
        print("PERSON 3: ALLA INTEGRATIONSKONTROLLER GODKÄNDA")
    finally:
        for task in jobs:
            task.cancel()
        await asyncio.gather(*jobs,return_exceptions=True)
        for server in reversed(servers):
            await server.stop()


if __name__=="__main__":
    asyncio.run(main())
