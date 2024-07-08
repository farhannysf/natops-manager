import re
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

time_pattern = re.compile(r"(\s*\d{1,2}:\d{2}:\d{2}),?")
player_connecting_pattern = re.compile(r"Player\s+(.*?)\s+connecting")
player_connected_pattern = re.compile(r"Player\s+.*?\s+connected\s+\(id=(.*?)\)\.")


async def convert_to_datetime(time_str, start_date, microseconds=0):
    time_obj = datetime.strptime(time_str, "%H:%M:%S").time()

    return datetime.combine(start_date, time_obj).replace(
        microsecond=microseconds, tzinfo=timezone.utc
    )


async def parse_log(log_file, start_date):
    connecting_players = {}
    console_log_data = []

    first_line = log_file.readline()
    first_time_match = time_pattern.match(first_line)
    if first_time_match:
        first_time_str = first_time_match.group(1).strip()
        content_start_pos = first_time_match.end()
        content = first_line[content_start_pos:].strip()
        previous_time = datetime.strptime(first_time_str, "%H:%M:%S").time()

    else:
        previous_time = datetime.min.time()
        content = first_line.strip()

    log_file.seek(0)

    for line in log_file:
        time_match = time_pattern.match(line)
        if time_match:
            time_str = time_match.group(1).strip()
            content_start_pos = time_match.end()
            content = line[content_start_pos:].strip()
            current_time = datetime.strptime(time_str, "%H:%M:%S").time()
            if current_time < previous_time:
                start_date += timedelta(days=1)

            previous_time = current_time
        else:
            time_str = ""
            content = line.strip()

        player_connecting_match = player_connecting_pattern.search(content)
        if player_connecting_match:
            player_name = player_connecting_match.group(1)
            connecting_players[player_name] = time_str
            continue

        player_connected_match = player_connected_pattern.search(content)
        if player_connected_match:
            steam_id = player_connected_match.group(1)
            for player_name, connect_time_str in connecting_players.items():
                steam_link = f"https://steamcommunity.com/profiles/{steam_id}"
                connect_datetime_obj = await convert_to_datetime(
                    connect_time_str, start_date
                )

                console_log_data.append(
                    {
                        "Timestamp": connect_datetime_obj,
                        "Time": connect_time_str,
                        "Content": content,
                        "Player": player_name,
                        "Steam ID": steam_id,
                        "Steam Link": steam_link,
                    }
                )
                break

            connecting_players.pop(player_name, None)

    return console_log_data
