import logging
import asyncio

from a2s import ainfo
from utils import message_formatting

logger = logging.getLogger(__name__)

NATOPS_QUERY_PORT = 2303


async def exponential_backoff_query(natops_socket):
    MAX_RETRIES = 10
    INITIAL_DELAY = 1
    MAX_DELAY = 16

    attempt = 0
    delay = INITIAL_DELAY
    logger.info(
        f"Attempting to query to NATOPS session at {natops_socket[0]}:{natops_socket[1]}"
    )

    while attempt < MAX_RETRIES:
        try:
            natops_session = await ainfo(natops_socket)
            return natops_session

        except (ConnectionRefusedError, asyncio.TimeoutError) as e:

            logger.warn(
                f"{e.__class__.__name__}. Retrying in {delay}s. Attempt: {attempt}"
            )
            await asyncio.sleep(delay)
            attempt += 1
            delay = min(delay * 2, MAX_DELAY)

        except Exception as e:
            logger.error(f"{e.__class__.__name__}: {e}.")
            raise


async def query_natops_session(instance_ip):
    natops_socket = (instance_ip, NATOPS_QUERY_PORT)
    natops_session = await exponential_backoff_query(natops_socket)
    discord_embed = await message_formatting.embify(
        title=natops_session.server_name, description="Online"
    )

    embed_fields = [
        ("__IP Address__", f"{instance_ip}:{natops_session.port}"),
        ("__Players__", f"{natops_session.player_count}/{natops_session.max_players}"),
        ("__Map__", natops_session.map_name),
        ("__Mission__", natops_session.game),
        (
            "__Steam Run__",
            f"steam://run/107410//+connect {instance_ip}:{NATOPS_QUERY_PORT}",
        ),
    ]

    await message_formatting.populate_embed_fields(
        discord_embed=discord_embed, fields=embed_fields
    )

    return discord_embed
