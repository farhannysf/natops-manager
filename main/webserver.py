import logging
import ssl
import base64

from aiohttp import web
from utils import ssl_generator, webhook_handler
from settings import (
    WEBHOOK_PORT,
    WEBHOOK_AUTH_USERNAME,
    WEBHOOK_AUTH_PASSWORD,
    GOOGLE_CLOUD_PROJECT,
)

logger = logging.getLogger(__name__)


async def start_webhook(discord_client):
    ssl_pair = await ssl_generator.generate_ssl_pair()
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(
        certfile=ssl_pair["certfile"], keyfile=ssl_pair["keyfile"]
    )

    webhook = web.Application()
    endpoint_path = "/connecting-event"
    webhook.router.add_post(
        path=endpoint_path,
        handler=lambda request: connecting_event_endpoint(request, discord_client),
    )

    runner = web.AppRunner(webhook)
    await runner.setup()
    webhook_socket = ("0.0.0.0", WEBHOOK_PORT)

    # Google Cloud Platform notification channel webhook does not support self-signed certificate for TLS connection.
    webhook_server = await discord_client.loop.create_server(
        protocol_factory=runner.server,
        host=webhook_socket[0],
        port=webhook_socket[1],
        ssl=None,
    )

    logger.info(
        f"Webhook server started at {webhook_socket[0]}:{webhook_socket[1]}{endpoint_path}"
    )

    return webhook_server


async def check_basic_auth(auth_header):
    if not auth_header:
        return False

    try:
        auth_type, encoded_credentials = auth_header.split(" ", 1)
        if auth_type.lower() != "basic":
            return False

        decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
        username, password = decoded_credentials.split(":", 1)

        return username == WEBHOOK_AUTH_USERNAME and password == WEBHOOK_AUTH_PASSWORD

    except Exception:
        return False


async def connecting_event_endpoint(request, discord_client):
    auth_header = request.headers.get("Authorization")
    if not await check_basic_auth(auth_header):
        error_message = "401 Could not verify your access level for that URL. You have to login with proper credentials"
        return web.Response(
            text=error_message,
            status=401,
            headers={"WWW-Authenticate": 'Basic realm="Login Required"'},
        )

    try:
        payload_data = await request.json()
        payload_policy_name = payload_data["incident"]["policy_name"]
        payload_project_id = payload_data["incident"]["resource"]["labels"][
            "project_id"
        ]

        if (
            payload_policy_name == "NATOPS Session Connecting Event"
            and payload_project_id == GOOGLE_CLOUD_PROJECT
        ):
            logger.info(f"Received connecting-event payload.")
            discord_client.loop.create_task(
                webhook_handler.process_event(discord_client=discord_client)
            )

        else:
            raise ValueError("The provided data does not match the expected schema.")

        return web.Response(text="OK", status=200)

    except Exception as e:
        logger.error(f"Error while processing webhook data: {e}")
        return web.Response(status=400)


async def webhook_health_check(task_memory, discord_client):
    webhook_server = task_memory.get("webhook_server")
    if not webhook_server:
        webhook_server = await start_webhook(discord_client=discord_client)
        task_memory["webhook_server"] = webhook_server

    else:
        if webhook_server.is_serving():
            logger.info("Webhook server is currently running.")

        else:
            del task_memory["webhook_server"]
            await webhook_health_check(discord_client, task_memory)
