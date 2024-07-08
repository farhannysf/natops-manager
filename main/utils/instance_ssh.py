import logging
import asyncio
import paramiko

from settings import SSH_KEY
from bot_commands import session_manager
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


async def exponential_backoff_connect(discord_client, ssh_client, instance_ip):
    MAX_RETRIES = 10
    INITIAL_DELAY = 1
    MAX_DELAY = 16

    attempt = 0
    delay = INITIAL_DELAY
    logger.info(f"Attempting to connect to {instance_ip}")
    while attempt < MAX_RETRIES:
        try:
            await discord_client.loop.run_in_executor(
                executor=None,
                func=lambda: ssh_client.connect(hostname=instance_ip, pkey=SSH_KEY),
            )

            return

        except (
            paramiko.ssh_exception.NoValidConnectionsError,
            ConnectionResetError,
        ) as e:

            logger.warn(
                f"{e.__class__.__name__}. Retrying in {delay}s. Attempt: {attempt}"
            )
            await asyncio.sleep(delay)
            attempt += 1
            delay = min(delay * 2, MAX_DELAY)

        except Exception as e:
            logger.error(f"{e.__class__.__name__}: {e}.")
            raise

    raise Exception("Unable to establish SSH connection after maximum retries.")


async def remote_exec(discord_client, instance_ip, commands):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        await exponential_backoff_connect(
            discord_client=discord_client,
            ssh_client=ssh_client,
            instance_ip=instance_ip,
        )

    except Exception as e:
        logger.error(
            f"Unable to establish SSH connection to {instance_ip} after maximum retries: {e}"
        )

        raise e

    ssh_command_executor = ThreadPoolExecutor(max_workers=len(commands))
    for command in commands:
        stdin, stdout, stderr = await discord_client.loop.run_in_executor(
            executor=ssh_command_executor, func=lambda: ssh_client.exec_command(command)
        )

        exit_status = await discord_client.loop.run_in_executor(
            executor=ssh_command_executor,
            func=lambda: stdout.channel.recv_exit_status(),
        )

        if exit_status == 0:
            output = await discord_client.loop.run_in_executor(
                executor=ssh_command_executor,
                func=lambda: stdout.read().decode("utf-8").strip(),
            )

            logger.info(output)

            if command == "./get_start_timestamp":
                session_manager.server_start_timestamp = output.split("=")[1]

        else:
            error = await discord_client.loop.run_in_executor(
                executor=ssh_command_executor,
                func=lambda: stderr.read().decode("utf-8").strip(),
            )

            logger.error(f"Error executing '{command}': {error}")

    ssh_client.close()

    return
