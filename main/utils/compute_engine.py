import logging

from google.cloud import compute_v1
from settings import GOOGLE_COMPUTE_ENGINE, GOOGLE_CLOUD_PROJECT
from utils import instance_ssh, natops_session
from bot_commands import session_manager
from io import StringIO

logger = logging.getLogger(__name__)

compute_client = compute_v1.InstancesClient(credentials=GOOGLE_COMPUTE_ENGINE)
operation_client = compute_v1.ZoneOperationsClient(credentials=GOOGLE_COMPUTE_ENGINE)
server_startup_in_progress = set()
server_shutdown_in_progress = set()

label_key = "classification"
label_value = "natops"

async def health_check(discord_client, instance, flag=None):
    instance_attributes = {}
    instance_info = await discord_client.loop.run_in_executor(
        executor=None,
        func=lambda: compute_client.get(
            project=GOOGLE_CLOUD_PROJECT,
            zone=instance["zone"],
            instance=instance["instance_name"],
        ),
    )

    instance_attributes["instance_status"] = instance_info.status

    if instance_info.status == compute_v1.Instance.Status.RUNNING.name:
        instance_ip = instance_info.network_interfaces[0].access_configs[0].nat_i_p
        instance_attributes["instance_ip"] = instance_ip

        if flag == "query-natops":
            natops_embed = await natops_session.query_natops_session(
                instance_ip=instance_ip, flag="no-retry"
            )

            if not natops_embed:
                session_manager.session_running.discard(instance["instance_name"])

                return instance_attributes
            
            instance_attributes["natops_session"] = natops_embed

            if not session_manager.server_start_timestamp:
                await instance_ssh.remote_exec(discord_client=discord_client, instance_ip=instance_ip, commands=["./get_start_timestamp"])

            if instance["instance_name"] not in server_shutdown_in_progress:
                session_manager.session_running.add(instance["instance_name"])

    elif instance_info.status  in [
        compute_v1.Instance.Status.STOPPED.name,
        compute_v1.Instance.Status.TERMINATED.name,
    ]:
        
        session_manager.session_running.discard(instance["instance_name"])

    return instance_attributes

async def operation_result(discord_client, operation_name, instance):
    operation_result = await discord_client.loop.run_in_executor(
        executor=None,
        func=lambda: operation_client.wait(
            project=GOOGLE_CLOUD_PROJECT, zone=instance["zone"], operation=operation_name
        ),
    )

    if operation_result.error:
        logger.error(operation_result.error)
        message = {
            "status": "error",
            "message": f"Error starting {instance["instance_name"]} in {instance["zone"]}.",
        }

        return message

    else:
        instance_attributes = await health_check(discord_client=discord_client, instance=instance)

        message = {
            "status": "success",
            "message": f"`{instance["instance_name"]}` in `{instance["zone"]}` is `{instance_attributes["instance_status"]}` successfully.",
        }

        return message


async def get_instance(discord_client):
    all_instances = await discord_client.loop.run_in_executor(
        executor=None,
        func=lambda: compute_client.aggregated_list(project=GOOGLE_CLOUD_PROJECT),
    )

    instances_list = [
        {"instance_name": instance.name, "zone": zone.split("/")[-1]}
        for zone, instances_scoped_list in all_instances
        if instances_scoped_list.instances
        for instance in instances_scoped_list.instances
        if instance.labels
        and label_key in instance.labels
        and instance.labels[label_key] == label_value
    ]

    zone = instances_list[0]["zone"]
    instance_name = instances_list[0]["instance_name"]
    instance = {"zone": zone, "instance_name": instance_name}

    return instance


async def start(discord_client, instance):
    instance_attributes = await health_check(
        discord_client=discord_client, instance=instance
    )

    if instance_attributes["instance_status"] == compute_v1.Instance.Status.RUNNING.name:
        message = {
            "message": f"`{instance["instance_name"]}` in `{instance["zone"]}` is already `{instance_attributes["instance_status"] }`.",
            "log_message": f"locked: {instance_attributes["instance_status"] }",
        }

        return message

    elif instance_attributes["instance_status"]  in [
        compute_v1.Instance.Status.STOPPED.name,
        compute_v1.Instance.Status.TERMINATED.name,
    ]:
        operation = compute_client.start(
            project=GOOGLE_CLOUD_PROJECT, zone=instance["zone"], instance=instance["instance_name"]
        )

        message = await operation_result(discord_client=discord_client, operation_name=operation.name, instance=instance)

        if message.get("status") == "success":
            server_startup_in_progress.add(instance["instance_name"])
            instance_attributes = await health_check(discord_client=discord_client, instance=instance)
            
            try:
                commands = ["./start", "./get_start_timestamp"]
                await instance_ssh.remote_exec(discord_client=discord_client, instance_ip=instance_attributes["instance_ip"], commands=commands)

            except Exception as e:
                server_startup_in_progress.remove(instance["instance_name"])
                logger.error(f"Error: {str(e)}")
                message = {
                    "status": "error",
                    "message": f"Error while starting up `{instance["instance_name"]}` in `{instance["zone"]}`.",
                }

                return message

            finally:
                server_startup_in_progress.discard(instance["instance_name"])

            message["instance_ip"] = instance_attributes["instance_ip"]

        return message

    else:
        message = {
            "message": f"`{instance["instance_name"]}` in {instance["zone"]} is `{instance_attributes["instance_status"]}`.",
            "log_message": f"locked: {instance_attributes["instance_status"]}",
        }

        return message


async def stop(discord_client, instance):
    instance_attributes = await health_check(discord_client=discord_client,instance=instance)

    if instance["instance_name"] in server_startup_in_progress:
        message = {
            "message": f"`{instance["instance_name"]}` in `{instance["zone"]}` is starting up NATOPS session.",
            "log_message": "locked: instance startup in progress",
        }

        return message

    if instance["instance_name"] in server_shutdown_in_progress:
        message = {
            "message": f"`{instance["instance_name"]}` in `{instance["zone"]}` is shutting down NATOPS session.",
            "log_message": "locked: instance shutdown in progress",
        }

        return message

    if instance_attributes["instance_status"]  in [
        compute_v1.Instance.Status.STOPPED.name,
        compute_v1.Instance.Status.TERMINATED.name,
    ]:
        
        message = {
            "message": f"`{instance["instance_name"]}` in `{instance["zone"]}` is already `{instance_attributes["instance_status"]}`.",
            "log_message": f"locked: {instance_attributes["instance_status"]}",
        }

        return message

    elif instance_attributes["instance_status"] == compute_v1.Instance.Status.RUNNING.name:
        server_shutdown_in_progress.add(instance["instance_name"])
        session_manager.session_running.discard(instance["instance_name"])

        try:
            commands = ["./stop"]
            await instance_ssh.remote_exec(discord_client=discord_client, instance_ip=instance_attributes["instance_ip"], commands=commands)

        except Exception as e:
            server_shutdown_in_progress.remove(instance["instance_name"])
            logger.error(f"Error: {str(e)}")
            message = {
                "status": "error",
                "message": f"Error while shutting down `{instance["instance_name"]}` in `{instance["zone"]}`.",
            }

            return message

        finally:
            server_shutdown_in_progress.discard(instance["instance_name"])

        operation = compute_client.stop(
            project=GOOGLE_CLOUD_PROJECT, zone=instance["zone"], instance=instance["instance_name"]
        )

        message = await operation_result(discord_client=discord_client, operation_name=operation.name, instance=instance)

        return message

    else:
        message = {
            "message": f"`{instance["instance_name"]}` in {instance["zone"]} is `{instance_attributes["instance_status"]}.`",
            "log_message": f"locked: {instance_attributes["instance_status"]}",
        }

        return message


async def read_console_log(discord_client, instance):
    zone = instance["zone"]
    instance_name = instance["instance_name"]
    instance_info = await discord_client.loop.run_in_executor(
        executor=None,
        func=lambda: compute_client.get(
            project=GOOGLE_CLOUD_PROJECT, zone=zone, instance=instance_name
        ),
    )

    instance_ip = instance_info.network_interfaces[0].access_configs[0].nat_i_p
    console_log = await instance_ssh.remote_exec(
        discord_client=discord_client,
        instance_ip=instance_ip,
        commands=["./read_console_log"],
    )

    console_log_file = await discord_client.loop.run_in_executor(
        executor=None, func=lambda: StringIO(console_log)
    )

    return console_log_file
