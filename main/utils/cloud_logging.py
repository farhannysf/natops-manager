import logging
from google.cloud import logging_v2
from settings import GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOGGING, FIREWALL_NAME
from datetime import timedelta

logger = logging.getLogger(__name__)
cloud_logging = logging_v2.Client(credentials=GOOGLE_CLOUD_LOGGING)


async def create_filter_time_range(console_log_data):
    filter_timestamp_format = "%Y-%m-%dT%H:%M:%S.%fZ"
    filter_time_range = {
        "min_time": (console_log_data[0]["Timestamp"] - timedelta(seconds=1)).strftime(
            filter_timestamp_format
        ),
        "max_time": (
            console_log_data[-1]["Timestamp"] + timedelta(microseconds=999999)
        ).strftime(filter_timestamp_format),
    }

    return filter_time_range


async def get_firewall_log(discord_client, min_time, max_time):
    filter_ = (
        f"logName:(projects/{GOOGLE_CLOUD_PROJECT}/logs/compute.googleapis.com%2Ffirewall) "
        f'AND jsonPayload.rule_details.reference:("network:default/firewall:{FIREWALL_NAME}") '
        'AND jsonPayload.connection.dest_port="2302" '
        f'AND timestamp>="{min_time}" '
        f'AND timestamp<="{max_time}"'
    )

    project_name = f"projects/{GOOGLE_CLOUD_PROJECT}"

    firewall_log_entries = await discord_client.loop.run_in_executor(
        executor=None,
        func=lambda: cloud_logging.list_entries(
            resource_names=[project_name], filter_=filter_
        ),
    )

    connection_attributes = []

    for log_entry in firewall_log_entries:
        connection_data = log_entry.payload.get("connection", {})
        src_ip = connection_data.get("src_ip")
        src_port = connection_data.get("src_port")

        data_dict = {
            "timestamp": log_entry.timestamp.replace(microsecond=0),
            "src_ip": src_ip,
            "src_port": src_port,
        }

        connection_attributes.append(data_dict)

    return connection_attributes


async def adaptive_timedelta_sync(console_log_data, connection_attributes):
    threshold = timedelta(seconds=1)

    for connection in connection_attributes:
        connection_timestamp = connection.get("timestamp")

        for i, console_log_event in enumerate(console_log_data):
            console_event_timestamp = console_log_event.get("Timestamp")
            next_adjacent_difference = timedelta(seconds=2)

            if i + 1 < len(console_log_data):
                next_console_event_timestamp = console_log_data[i + 1].get("Timestamp")
                next_adjacent_difference = abs(
                    next_console_event_timestamp - console_event_timestamp
                )

            if next_adjacent_difference > timedelta(seconds=1):
                if abs(connection_timestamp - console_event_timestamp) <= threshold:
                    console_log_event["IP Address"] = connection["src_ip"]
                    console_log_event["Source Port"] = int(connection["src_port"])

                    break

            elif (
                next_adjacent_difference == timedelta(seconds=1)
                and connection_timestamp == console_event_timestamp
            ):
                console_log_event["IP Address"] = connection["src_ip"]
                console_log_event["Source Port"] = int(connection["src_port"])

                break

    ip_log_data = console_log_data
    return ip_log_data


async def create_ip_log_data(discord_client, console_log_data):
    filter_time_range = await create_filter_time_range(console_log_data)

    connection_attributes = await get_firewall_log(
        discord_client=discord_client,
        min_time=filter_time_range["min_time"],
        max_time=filter_time_range["max_time"],
    )

    ip_log_data = await adaptive_timedelta_sync(
        console_log_data=console_log_data, connection_attributes=connection_attributes
    )

    return ip_log_data
