import base64
import json

from os import environ
from io import StringIO
from google.oauth2 import service_account
from paramiko import RSAKey


def load_gcp_key(gcp_key_string):
    gcp_key_string = base64.b64decode(gcp_key_string).decode("utf-8")
    gcp_key = json.loads(gcp_key_string)
    gcp_credential = service_account.Credentials.from_service_account_info(gcp_key)
    return gcp_credential


def load_ssh_key(ssh_key_string):
    private_key_string = base64.b64decode(ssh_key_string).decode("utf-8")
    private_key_obj = StringIO(private_key_string)
    private_key = RSAKey.from_private_key(file_obj=private_key_obj)
    return private_key


MAINTAINER_ID = environ["MAINTAINER_ID"]
BOT_TOKEN = environ["BOT_TOKEN"]
GOOGLE_CLOUD_PROJECT = environ["GOOGLE_CLOUD_PROJECT"]
FIREWALL_NAME = environ["FIREWALL_NAME"]
SSH_KEY = load_ssh_key(ssh_key_string=environ["SSH_KEY"])
IPINFO_TOKEN = environ["IPINFO_TOKEN"]
VPNIO_TOKEN = environ["VPNIO_TOKEN"]
WEBHOOK_PORT = environ["WEBHOOK_PORT"]
WEBHOOK_AUTH_USERNAME = environ["WEBHOOK_AUTH_USERNAME"]
WEBHOOK_AUTH_PASSWORD = environ["WEBHOOK_AUTH_PASSWORD"]
AUTHORIZED_CHANNELS = [
    int(channel) for channel in environ["AUTHORIZED_CHANNELS"].split(",")
]

gcp_credentials = [
    "GOOGLE_COMPUTE_ENGINE",
    "GOOGLE_CLOUD_STORAGE",
    "GOOGLE_CLOUD_LOGGING",
]

gcp_keys = {credential: credential for credential in gcp_credentials}
for credential, key in gcp_keys.items():
    globals()[credential] = load_gcp_key(gcp_key_string=environ[key])
