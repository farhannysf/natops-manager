import logging

from google.cloud import storage
from io import StringIO
from settings import GOOGLE_CLOUD_STORAGE

logger = logging.getLogger(__name__)
storage_client = storage.Client(credentials=GOOGLE_CLOUD_STORAGE)
bucket_name = "natops-logs"


async def read_log(discord_client, server_start_datetime):
    bucket = await discord_client.loop.run_in_executor(
        executor=None, func=lambda: storage_client.get_bucket(bucket_name)
    )

    log_filename = (
        f'logs/{server_start_datetime["date"]}/{server_start_datetime["time"]}.log'
    )

    logger.info(f"log file: {log_filename}")
    blob = await discord_client.loop.run_in_executor(
        executor=None,
        func=lambda: bucket.get_blob(log_filename),
    )

    blob_data = await discord_client.loop.run_in_executor(
        executor=None, func=lambda: StringIO(blob.download_as_string().decode("utf-8"))
    )

    return blob_data
