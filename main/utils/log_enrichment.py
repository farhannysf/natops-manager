import logging
import aiohttp
import asyncio

from yarl import URL
from settings import IPINFO_TOKEN, VPNIO_TOKEN

logger = logging.getLogger(__name__)


async def fetch_url(session, url, params=None):
    try:
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.json()

    except aiohttp.ClientResponseError as e:
        logger.error(f"ClientResponseError: {e}")

    except aiohttp.ClientConnectionError as e:
        logger.error(f"ClientConnectionError: {e}")

    except aiohttp.ClientError as e:
        logger.error(f"ClientError: {e}")

    except asyncio.TimeoutError as e:
        logger.error(f"TimeoutError: {e}")

    return None


async def get_ip_attributes(ip_address):
    url = URL("http://ipinfo.io/").with_path(ip_address)
    params = {"token": IPINFO_TOKEN}
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=10)
    ) as session:
        ip_data = await fetch_url(session, url, params)
        if ip_data:
            latlong = ip_data.get("loc").split(",")
            ip_attributes = {
                "City": ip_data.get("city"),
                "Region": ip_data.get("region"),
                "Postal Code": ip_data.get("postal"),
                "Latitude": latlong[0],
                "Longitude": latlong[1],
                "ISP": ip_data.get("org"),
                "Country": ip_data.get("country"),
            }

            return ip_attributes

        return None


async def get_obfuscation_flags(ip_address):
    url = URL("https://vpnapi.io/api/") / ip_address
    params = {"key": VPNIO_TOKEN}
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=10)
    ) as session:
        obfuscation_flag = await fetch_url(session, url, params)
        if obfuscation_flag:
            obfuscation_attributes = {
                key.upper() if key == "vpn" else key.title(): value
                for key, value in obfuscation_flag["security"].items()
            }

            return obfuscation_attributes

        return None


async def enrich_event(event):
    ip_address = event.get("IP Address")
    if ip_address:
        attributes_data = await asyncio.gather(
            get_ip_attributes(ip_address), get_obfuscation_flags(ip_address)
        )

        ip_attributes = attributes_data[0]
        event.update(ip_attributes)

        obfuscation_attributes = attributes_data[1]
        event.update(obfuscation_attributes)


async def enrich_data(ip_log_data):
    tasks = [enrich_event(event) for event in ip_log_data]
    await asyncio.gather(*tasks)

    enriched_log_data = ip_log_data
    return enriched_log_data
