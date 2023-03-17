import asyncio
import os
import time
from aioprometheus.service import Service
from aioprometheus import Gauge, Counter
from datetime import datetime, date
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager

EMAIL = os.environ.get('MEROSS_EMAIL') or "YOUR_MEROSS_CLOUD_EMAIL"
PASSWORD = os.environ.get('MEROSS_PASSWORD') or "YOUR_MEROSS_CLOUD_PASSWORD"

def _get_today_consumption(daily_consumption_history):
    today_time = datetime.now()
    today_time = today_time.replace(hour=0, minute=0, second=0, microsecond=0)
    today_consumption = 0
    for daily_history in daily_consumption_history:
        if daily_history['date'] == today_time:
            today_consumption = daily_history['total_consumption_kwh']
    return today_consumption


def _get_monthly_consumption(daily_consumption_history):
    current_month = datetime.today().month

    month_daily_history = [h for h in daily_consumption_history if h['date'].month == current_month]
    monthly_consumption = 0

    for daily_history in month_daily_history:
        monthly_consumption += daily_history['total_consumption_kwh']

    return monthly_consumption


async def main():
    service = Service()
        
    power = Gauge('meross_power', 'Electricity watt reading (w)')
    voltage = Gauge('meross_voltage', 'Electricity voltage reading (v)')
    current = Gauge('meross_current', 'Electricity ampere reading (a)')
    daily_consumption = Gauge('meross_daily_consumption', 'Electricity daily consumption (w)')
    monthly_consumption = Gauge('meross_monthly_consumption', 'Electricity monthly consumption (w)')
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
        async def updater(p: Gauge, v: Gauge, c: Gauge, dc: Gauge, mc: Gauge):
            while True:
                for dev in plugs:
                    try:
                        instant_consumption = await dev.async_get_instant_metrics()
                        p.set({'device': dev.name},instant_consumption.power)
                        v.set({'device': dev.name},instant_consumption.voltage)
                        c.set({'device': dev.name},instant_consumption.current)

                        daily_consumption_history = await dev.async_get_daily_power_consumption()
                        dc.set({'device': dev.name}, _get_today_consumption(daily_consumption_history))
                        mc.set({'device': dev.name}, _get_monthly_consumption(daily_consumption_history))
                        
                    except Exception as e:
                        print(f"Exception caught: {e}")
                await asyncio.sleep(30.0)

        await updater(power,voltage,current, daily_consumption, monthly_consumption)


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
