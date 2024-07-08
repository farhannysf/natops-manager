import logging

from utils import (
    compute_engine,
    cloud_storage,
    cloud_logging,
    instance_info,
    console_log_parser,
    log_enrichment,
    message_formatting,
)

logger = logging.getLogger(__name__)
server_start_timestamp = None
session_startup_in_progress = set()


async def logic(discord_client, ctx, argument: str):
    instance = await compute_engine.get_instance(discord_client=discord_client)

    if argument == "start":
        async with ctx.typing():
            start_result = await compute_engine.start(
                discord_client=discord_client, instance=instance
            )

            if start_result.get("log_message"):
                message = start_result["log_message"]
                logger_info_message = (
                    await message_formatting.create_logger_info_message(
                        command=argument,
                        message=message,
                        instance_name=instance["instance_name"],
                        zone=instance["zone"],
                    )
                )

                logger.info(logger_info_message)

            message = start_result["message"]
            await ctx.send(message)

            if start_result.get("status") == "success" and start_result.get(
                "instance_ip"
            ):

                session_startup_in_progress.add(instance["instance_name"])

                message = "Querying NATOPS session..."
                logger_info_message = (
                    await message_formatting.create_logger_info_message(
                        command=argument,
                        message=message,
                        instance_name=instance["instance_name"],
                        zone=instance["zone"],
                    )
                )

                logger.info(logger_info_message)

                discord_embed = await instance_info.query_natops_session(
                    instance_ip=start_result["instance_ip"]
                )

                await ctx.send(embed=discord_embed)
                session_startup_in_progress.discard(instance["instance_name"])

                message = "NATOPS session started."
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

    elif argument == "stop":
        async with ctx.typing():
            if instance["instance_name"] in session_startup_in_progress:
                message = "locked: session startup in progress"
                logger_info_message = (
                    await message_formatting.create_logger_info_message(
                        command=argument,
                        message=message,
                        instance_name=instance["instance_name"],
                        zone=instance["zone"],
                    )
                )

                logger.info(logger_info_message)

                message = f'`{instance["instance_name"]}` in `{instance["zone"]}` is still starting up NATOPS session.'
                return await ctx.send(message)

            stop_result = await compute_engine.stop(
                discord_client=discord_client, instance=instance
            )

            if stop_result.get("log_message"):
                message = stop_result["log_message"]
                logger_info_message = (
                    await message_formatting.create_logger_info_message(
                        command=argument,
                        message=message,
                        instance_name=instance["instance_name"],
                        zone=instance["zone"],
                    )
                )

                logger.info(logger_info_message)

            message = stop_result["message"]
            await ctx.send(message)

            if stop_result.get("status") == "success":
                message = "NATOPS instance stopped."
                logger_info_message = (
                    await message_formatting.create_logger_info_message(
                        command=argument,
                        message=message,
                        instance_name=instance["instance_name"],
                        zone=instance["zone"],
                    )
                )

                logger.info(logger_info_message)

                server_start_datetime = await message_formatting.format_start_datetime(
                    server_start_timestamp
                )

                message = "Reading NATOPS console log from cloud storage..."
                logger_info_message = (
                    await message_formatting.create_logger_info_message(
                        command=argument,
                        message=message,
                        instance_name=instance["instance_name"],
                        zone=instance["zone"],
                    )
                )

                logger.info(logger_info_message)

                console_log_file = await cloud_storage.read_log(
                    discord_client=discord_client,
                    server_start_datetime=server_start_datetime,
                )

                message = "Parsing NATOPS console log..."
                logger.info(logger_info_message)
                await ctx.send(message)

                console_log_data = await console_log_parser.parse_log(
                    log_file=console_log_file,
                    start_date=server_start_datetime["start_date_object"],
                )

                if len(console_log_data) == 0:
                    message = "No player connected."
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

                message = "Fetching IP address from cloud logging..."
                logger_info_message = (
                    await message_formatting.create_logger_info_message(
                        command=argument,
                        message=message,
                        instance_name=instance["instance_name"],
                        zone=instance["zone"],
                    )
                )

                logger.info(logger_info_message)

                ip_log_data = await cloud_logging.create_ip_log_data(
                    discord_client=discord_client, console_log_data=console_log_data
                )

                message = "Enriching log data..."
                logger_info_message = (
                    await message_formatting.create_logger_info_message(
                        command=argument,
                        message=message,
                        instance_name=instance["instance_name"],
                        zone=instance["zone"],
                    )
                )

                logger.info(logger_info_message)

                enriched_log_data = await log_enrichment.enrich_data(ip_log_data)
                for event in enriched_log_data:
                    embed = await message_formatting.create_log_event_embed(
                        log_data=event
                    )

                    await ctx.send(embed=embed)

                message = f"{len(enriched_log_data)} events data sent."
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
