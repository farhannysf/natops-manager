import logging

from utils import compute_engine, message_formatting, connecting_event
from bot_commands import session_manager

logger = logging.getLogger(__name__)


async def process_event(discord_client):
    source = "connecting-event-endpoint"
    channels = await message_formatting.authorize_discord_channels(
        discord_client=discord_client
    )

    instance = await compute_engine.get_instance(discord_client=discord_client)
    message = "Reading NATOPS console log from instance..."
    logger_info_message = await message_formatting.create_logger_info_message(
        command=source,
        message=message,
        instance_name=instance["instance_name"],
        zone=instance["zone"],
    )

    logger.info(logger_info_message)

    console_log_file = await compute_engine.read_console_log(
        discord_client=discord_client, instance=instance
    )

    server_start_datetime = await message_formatting.format_start_datetime(
        session_manager.server_start_timestamp
    )

    message = "Parsing NATOPS console log..."
    logger_info_message = await message_formatting.create_logger_info_message(
        command=source,
        message=message,
        instance_name=instance["instance_name"],
        zone=instance["zone"],
    )

    logger.info(logger_info_message)

    event_log = await connecting_event.construct_event_log(
        discord_client=discord_client,
        argument=source,
        instance=instance,
        console_log_file=console_log_file,
        server_start_date=server_start_datetime["start_date_object"],
        flag="webhook",
    )

    if isinstance(event_log, str):
        if event_log == "No player connected.":
            message = "Failed to retrieve connecting player log."
            for channel in channels:
                await channel.send(content=message)

            raise ValueError(message)

    embed = await message_formatting.create_log_event_embed(log_data=event_log[0])

    for channel in channels:
        await channel.send(embed=embed)

    message = f"Event data sent to {len(channels)} authorized channel(s)."
    logger_info_message = await message_formatting.create_logger_info_message(
        command=source,
        message=message,
        instance_name=instance["instance_name"],
        zone=instance["zone"],
    )

    logger.info(logger_info_message)

    return
