import asyncio
import os
import time
from aioprometheus.service import Service
from aioprometheus import Gauge

from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager

EMAIL = os.environ.get('MEROSS_EMAIL') or "YOUR_MEROSS_CLOUD_EMAIL"
PASSWORD = os.environ.get('MEROSS_PASSWORD') or "YOUR_MEROSS_CLOUD_PASSWORD"


async def main():
    service = Service()
        
    power = Gauge('meross_power', 'Electricity watt reading (w)')
    voltage = Gauge('meross_voltage', 'Electricity voltage reading (v)')
    current = Gauge('meross_current', 'Electricity ampere reading (a)')
    await service.start(addr="0.0.0.0", port=8000)
    print(f"Serving prometheus metrics on: {service.metrics_url}")

    # Setup the HTTP client API from user-password
    http_api_client = await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD)

    # Setup and start the device manager
    manager = MerossManager(http_client=http_api_client)
    await manager.async_init()

    # Retrieve all the MSS310 devices that are registered on this account
    await manager.async_device_discovery()
    plugs = manager.find_devices(device_type="mss310")

    if len(plugs) < 1:
        print("No MSS310 plugs found...")
    else:
        async def updater(p: Gauge, v: Gauge, c: Gauge):
            while True:
                for dev in plugs:
                    try:
                        instant_consumption = await dev.async_get_instant_metrics()
                        p.set({'device': dev.name},instant_consumption.power)
                        v.set({'device': dev.name},instant_consumption.voltage)
                        c.set({'device': dev.name},instant_consumption.current)
                    except Exception as e:
                        print(f"Exception caught: {e}")
                await asyncio.sleep(30.0)

        await updater(power,voltage,current)


    # Close the manager and logout from http_api
    manager.close()
    await http_api_client.async_logout()
    await service.stop()


if __name__ == '__main__':
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
