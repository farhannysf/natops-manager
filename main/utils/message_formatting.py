import logging

from datetime import datetime
from discord import Embed

logger = logging.getLogger(__name__)


async def create_logger_info_message(command, message, instance_name, zone):
    return f"[{command}] {message} instance: {instance_name} zone: {zone}"


async def embify(title, description):
    discord_embed = Embed(title=title, description=description, color=0xE74C3C)

    return discord_embed


async def populate_embed_fields(discord_embed, fields):
    for field in fields:
        discord_embed.add_field(name=field[0], value=field[1], inline=False)

    return discord_embed


async def create_log_event_embed(log_data):
    discord_embed = await embify(
        title="Player Connected Event", description="Timezone: UTC"
    )

    for header, data in log_data.items():
        discord_embed.add_field(name=f"__{header}__", value=data, inline=False)

    return discord_embed


async def format_start_datetime(date_string):
    try:
        timestamp = datetime.strptime(date_string, "%Y-%m-%d-%H-%M-%S")

        server_start_datetime = {
            "date": timestamp.strftime("%Y-%m-%d"),
            "time": timestamp.strftime("%H-%M-%S"),
            "start_date_object": timestamp.date(),
        }

        return server_start_datetime

    except ValueError as e:
        logger.error(f"Invalid server start date format: {date_string}. Error: {e}")
        raise
