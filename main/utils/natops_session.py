import logging
import asyncio

from a2s import ainfo, aplayers
from utils import message_formatting

logger = logging.getLogger(__name__)

NATOPS_QUERY_PORT = 2303


async def exponential_backoff_query(natops_socket, flag):
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
            if flag == "no-retry":
                return

            logger.warn(
                f"{e.__class__.__name__}. Retrying in {delay}s. Attempt: {attempt}"
            )
            await asyncio.sleep(delay)
            attempt += 1
            delay = min(delay * 2, MAX_DELAY)

        except Exception as e:
            logger.error(f"{e.__class__.__name__}: {e}.")
            raise


async def query_natops_session(instance_ip, flag=None):
    natops_socket = (instance_ip, NATOPS_QUERY_PORT)
    natops_session = await exponential_backoff_query(
        natops_socket=natops_socket, flag=flag
    )

    if not natops_session:
        return

    natops_embeds = {}

    session_embed_header = await message_formatting.embify(
        title=natops_session.server_name,
        description=f"Version: {natops_session.version}",
    )

    session_fields = [
        ("__IP Address__", f"{instance_ip}:{natops_session.port}"),
        ("__Players__", f"{natops_session.player_count}/{natops_session.max_players}"),
        ("__Map__", natops_session.map_name),
        ("__Mission__", natops_session.game),
        (
            "__Steam Run__",
            f"steam://run/{natops_session.game_id}//+connect {instance_ip}:{NATOPS_QUERY_PORT}",
        ),
    ]

    session_embed = await message_formatting.populate_embed_fields(
        discord_embed=session_embed_header, fields=session_fields
    )

    natops_embeds["session_embed"] = session_embed

    if natops_session.player_count > 0:
        natops_players = await aplayers(natops_socket)
        players_embed = [
            await message_formatting.populate_embed_fields(
                discord_embed=await message_formatting.embify(
                    title="Player Score", description=None
                ),
                fields=[
                    ("__Name__", player.name),
                    ("__Kill Score__", player.score),
                    ("__Uptime__", f"{player.duration // 60} minute(s)"),
                ],
            )
            for player in natops_players
        ]

        natops_embeds["players_embed"] = players_embed

    return natops_embeds
