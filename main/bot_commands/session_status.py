import logging

from utils import compute_engine, connecting_event, message_formatting

from bot_commands import session_manager
from settings import GOOGLE_CLOUD_PROJECT

logger = logging.getLogger(__name__)


async def inactive_session_message(argument, instance):
    text = "NATOPS session is not running."
    logger_info_message = await message_formatting.create_logger_info_message(
        command=argument,
        message=text,
        instance_name=instance["instance_name"],
        zone=instance["zone"],
    )

    message = {"message": text, "logger_info_message": logger_info_message}
    return message


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
                        await ctx.send(message)

                        return

                for event in event_log:
                    embed = await message_formatting.create_log_event_embed(
                        log_data=event
                    )

                    await ctx.send(embed=embed)

                message = f"{len(event_log)} event(s) data sent."
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
                message = await inactive_session_message(
                    argument=argument, instance=instance
                )

                logger.info(message["logger_info_message"])
                await ctx.send(message["message"])

                return

    elif argument == "server":
        async with ctx.typing():
            message = "Health check..."
            logger_info_message = await message_formatting.create_logger_info_message(
                command=argument,
                message=message,
                instance_name=instance["instance_name"],
                zone=instance["zone"],
            )

            logger.info(logger_info_message)

            instance_attributes = await compute_engine.health_check(
                discord_client=discord_client, instance=instance, flag="query-natops"
            )

            if not instance_attributes.get("natops_session"):
                message = await inactive_session_message(
                    argument=argument, instance=instance
                )

                logger.info(message["logger_info_message"])
                await ctx.send(message["message"])

                return

            await ctx.send(embed=instance_attributes["natops_session"]["session_embed"])

            if instance_attributes["natops_session"].get("players_embed"):
                players_embed = instance_attributes["natops_session"]["players_embed"]
                for embed in players_embed:
                    await ctx.send(embed=embed)

                message = f"{len(players_embed)} player score embed(s) sent."
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

    return
