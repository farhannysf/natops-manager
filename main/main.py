import logging
import discord
import error_handling

from bot_commands import session_manager, session_status, natops_help
from utils import compute_engine, message_formatting
from discord.ext import commands, tasks
from settings import BOT_NAME, BOT_TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix="!natops-", help_command=None, intents=intents)


@tasks.loop(seconds=300)
async def health_check_worker(discord_client):
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

    instance_attributes["instance"] = instance["instance_name"]
    instance_attributes["zone"] = instance["zone"]

    return instance_attributes


@client.event
async def on_ready():
    instance_attributes = await health_check_worker(discord_client=client)
    instance_status = " ".join(
        f"{key}: {value}" for key, value in instance_attributes.items()
    )

    if not health_check_worker.is_running():
        health_check_worker.start(discord_client=client)

    logger.info(
        f"{BOT_NAME} running as {client.user.name} ({client.user.id})\n{instance_status}\n------"
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
