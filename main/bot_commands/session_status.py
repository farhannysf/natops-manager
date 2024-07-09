import logging

from utils import compute_engine, connecting_event, message_formatting

from bot_commands import session_manager
from settings import GOOGLE_CLOUD_PROJECT

logger = logging.getLogger(__name__)


async def logic(discord_client, ctx, argument: str):
    instance = await compute_engine.get_instance(discord_client=discord_client)

    if argument == "player":
        if instance["instance_name"] in session_manager.session_running:
            async with ctx.typing():
                message = "Reading NATOPS console log from instance..."
                logger_info_message = (
                    await message_formatting.create_logger_info_message(
                        command=argument,
                        message=message,
                        instance_name=instance["instance_name"],
                        zone=instance["zone"],
                    )
                )

                logger.info(logger_info_message)

                console_log_file = await compute_engine.read_console_log(
                    discord_client=discord_client, instance=instance
                )

                server_start_datetime = await message_formatting.format_start_datetime(
                    session_manager.server_start_timestamp
                )

                message = "Parsing NATOPS console log..."
                logger_info_message = (
                    await message_formatting.create_logger_info_message(
                        command=argument,
                        message=message,
                        instance_name=instance["instance_name"],
                        zone=instance["zone"],
                    )
                )

                logger.info(logger_info_message)
                await ctx.send(message)

                event_log = await connecting_event.construct_event_log(
                    discord_client=discord_client,
                    argument=argument,
                    instance=instance,
                    console_log_file=console_log_file,
                    server_start_date=server_start_datetime["start_date_object"],
                )

                if isinstance(event_log, str):
                    if event_log == "No player connected.":
                        message = event_log
                        logger_info_message = (
                            await message_formatting.create_logger_info_message(
                                command=argument,
                                message=message,
                                instance_name=instance["instance_name"],
                                zone=instance["zone"],
                            )
                        )

                        logger.info(logger_info_message)

                        return await ctx.send(message)

                for event in event_log:
                    embed = await message_formatting.create_log_event_embed(
                        log_data=event
                    )

                    await ctx.send(embed=embed)

                message = f"{len(event_log)} events data sent."
                logger_info_message = (
                    await message_formatting.create_logger_info_message(
                        command=argument,
                        message=message,
                        instance_name=instance["instance_name"],
                        zone=instance["zone"],
                    )
                )

                logger.info(logger_info_message)

            return

        else:
            async with ctx.typing():
                message = "NATOPS session is not running."
                logger_info_message = (
                    await message_formatting.create_logger_info_message(
                        command=argument,
                        message=message,
                        instance_name=instance["instance_name"],
                        zone=instance["zone"],
                    )
                )

                logger.info(logger_info_message)
                await ctx.send(message)

            return

    return