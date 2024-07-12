import logging
import discord
import error_handling
from bot_commands import session_manager, session_status, natops_help
from discord.ext import commands
from settings import BOT_NAME, BOT_TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix="!natops-", help_command=None, intents=intents)


@client.event
async def on_ready():
    logger.info(f"{BOT_NAME} running as {client.user.name} ({client.user.id}).\n------")
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
