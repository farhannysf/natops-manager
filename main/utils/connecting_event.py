import logging
from utils import message_formatting, console_log_parser, cloud_logging, log_enrichment

logger = logging.getLogger(__name__)


async def construct_event_log(
    discord_client, argument, instance, console_log_file, server_start_date, flag=None
):

    console_log_data = await console_log_parser.parse_log(
        log_file=console_log_file,
        start_date=server_start_date,
    )

    if len(console_log_data) == 0:
        message = "No player connected."
        logger_info_message = await message_formatting.create_logger_info_message(
            command=argument,
            message=message,
            instance_name=instance["instance_name"],
            zone=instance["zone"],
        )

        logger.info(logger_info_message)
        return message

    if flag == "webhook":
        console_log_data = [console_log_data[-1]]

    message = "Fetching IP address from cloud logging..."
    logger_info_message = await message_formatting.create_logger_info_message(
        command=argument,
        message=message,
        instance_name=instance["instance_name"],
        zone=instance["zone"],
    )

    logger.info(logger_info_message)

    ip_log_data = await cloud_logging.create_ip_log_data(
        discord_client=discord_client, console_log_data=console_log_data
    )

    message = "Enriching log data..."
    logger_info_message = await message_formatting.create_logger_info_message(
        command=argument,
        message=message,
        instance_name=instance["instance_name"],
        zone=instance["zone"],
    )

    logger.info(logger_info_message)

    enriched_log_data = await log_enrichment.enrich_data(ip_log_data)

    return enriched_log_data
