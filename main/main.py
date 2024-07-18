import logging
import discord
import error_handling
import webserver

from bot_commands import session_manager, session_status, natops_help
from utils import compute_engine, message_formatting
from discord.ext import commands, tasks
from settings import BOT_TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix="!natops-", help_command=None, intents=intents)
task_memory = {}


@tasks.loop(seconds=300)
async def instance_health_check_worker(discord_client):
    instance = await compute_engine.get_instance(discord_client=discord_client)
    message = "Health check..."
    logger_info_message = await message_formatting.create_logger_info_message(
        command="service-worker",
        message=message,
        instance_name=instance["instance_name"],
        zone=instance["zone"],
    )

    logger.info(logger_info_message)
    instance_attributes = await compute_engine.health_check(
        discord_client=discord_client, instance=instance, flag="query-natops"
    )

    return instance_attributes


@tasks.loop(seconds=82800)
async def webhook_rotation_worker(task_memory, discord_client):
    webhook_server = task_memory.get("webhook_server")
    if webhook_server:
        message = "[service-worker] Rotating webhook server..."
        logger.info(message)

        webhook_server.close()
        await webhook_server.wait_closed()
        del task_memory["webhook_server"]

    await webserver.webhook_health_check(
        task_memory=task_memory, discord_client=discord_client
    )


@client.event
async def on_ready():
    if not instance_health_check_worker.is_running():
        instance_health_check_worker.start(discord_client=client)

    if not webhook_rotation_worker.is_running():
        webhook_rotation_worker.start(task_memory=task_memory, discord_client=client)

    logger.info(
        f"natops-manager running as {client.user.name} ({client.user.id})\n------"
    )

    activity = discord.Game("!natops-session")
    await client.change_presence(status=discord.Status.online, activity=activity)


@client.command(pass_context=True)
async def session(ctx, argument: str):
    if argument in ["start", "stop"]:
        await session_manager.logic(discord_client=client, ctx=ctx, argument=argument)

    else:
        raise discord.ext.commands.BadArgument


@client.command(pass_context=True)
async def status(ctx, argument: str):
    if argument in ["player", "server"]:
        await session_status.logic(discord_client=client, ctx=ctx, argument=argument)

    else:
        raise discord.ext.commands.BadArgument


@client.command(pass_context=True)
async def help(ctx):
    await natops_help.logic(ctx)


@help.error
async def help_error(ctx, error):
    logger.error({"command": "help", "error": error})
    return await error_handling.internal_error(ctx)


if __name__ == "__main__":
    client.run(BOT_TOKEN)
    logger.critical("Client Event Loop Exit")
