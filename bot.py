# Imports
import discord
import dotenv
import redu_logger
import os
import requests
import inspect
import io
from pathlib import Path
from discord.ext import commands
from requests import Response
from typing import Optional


# Development Section
__version__ =  "0.3.1"
required_env_keys = ["TOKEN", "MC_SERVER_MANAGER_URL"]
optional_env_keys = ["GUILD_ID", "WOL_URL"]

# Initialize pathlib Paths
FILE_DIR = Path(__file__).resolve().parent

# Initialize the logger
local_log_file_name = "sarab_bot.log"
local_log_path = str(Path(FILE_DIR / "logs/sarab_bot"))

logger = redu_logger.RemoteLogger(
    local_logging=True,
    remote_logging=False,
    is_main=True,
    local_log_file_name=local_log_file_name,
    local_log_path=local_log_path,
    local_multi_log=True
)


# Helper functions
def get_required_env() -> dict:
    values = {}
    for k in required_env_keys:
        value = os.getenv(k)
        if not value:
            msg = f"Required environment variable '{k}' is missing or don't have any value"
            logger.error(msg)
            raise ValueError(msg)
        values[k] = value
    return values

def get_optional_env() -> dict:
    values = {}
    for k in optional_env_keys:
        value = os.getenv(k)
        if not value:
            logger.warning(f"Optional environment variable '{k}' is missing or don't have any value", True)
        values[k] = value
    return values


# Configurations
dotenv.load_dotenv()
ENV_VALUES = get_required_env()
OPTIONAL_ENV_VALUES = get_optional_env()
TOKEN = ENV_VALUES["TOKEN"]
MC_SERVER_MANAGER_URL = ENV_VALUES["MC_SERVER_MANAGER_URL"]
GUILD_ID = discord.Object(id=OPTIONAL_ENV_VALUES.get("GUILD_ID"))
WOL_URL = OPTIONAL_ENV_VALUES.get("WOL_URL")

intents = discord.Intents.default()
intents.message_content = True


class MCServerController:
    def __init__(self, server_url: str):
        """
        Initializes class

        Args:
            server_url (str): Base URL of the MCServerManager to control
        """
        logger.info("Initializing MCServerController...")
        self.server_url = server_url
        logger.info("Initialized MCServerController")

    @staticmethod
    def _send_request(url: str,
                      json_data: dict,
                      action_desc: str,
                      server_name: str,
                      body_mode: Optional[str] = None) -> tuple[bool, str]:
        """
        Helper method to execute HTTP POST requests and handle standard exceptions.

        Args:
            url: Endpoint of where to send the request
            json_data (dict): A dictionary containing JSON data to be sent with request
            action_desc (str): Description of why the request was sent for logging purposes
            server_name (str): Server to sent action to
            body_mode (Optional[str]): (Optional) Response formatting mode (None, "raw", or "attach")
        Returns:
            tuple: A tuple containing a bool and str
        """
        body_modes = ["raw", "attach"]
        if body_mode and body_mode not in body_modes:
            logger.warning(f"Invalid 'body_mode': {body_mode}. Valid body modes: {body_modes}")
            body_mode = None

        # Helper function to extract json or text safely without crashing on non-JSON payloads
        def safe_get_response_body(res: Optional[Response]):
            if res is None:
                return "None"
            try:
                res_json = res.json()
                # Extract 'logs' value to preserve raw string newlines for self.logs()
                if isinstance(res_json, dict) and "logs" in res_json:
                    return res_json["logs"]
                return res_json
            except requests.exceptions.JSONDecodeError:
                return res.text if res.text else "Empty Response Body"

        try:
            response = requests.post(url=url, json=json_data, timeout=15)
            response.raise_for_status()

            if body_mode == "raw":
                body = safe_get_response_body(response)
                msg = str(body)
            elif body_mode == "attach":
                body = safe_get_response_body(response)
                msg = f"Successfully {action_desc} server '{server_name}'\nResponse: {body}"
            else:
                msg = f"Successfully {action_desc} server '{server_name}'"

            logger.info(msg)
            return True, msg

        except requests.exceptions.Timeout as e:
            body = safe_get_response_body(e.response)
            msg = f"Request timed out while {action_desc} server '{server_name}'\nResponse: {body}"
            logger.error(msg)
        except requests.exceptions.HTTPError as e:
            body = safe_get_response_body(e.response)
            status_code = e.response.status_code if e.response is not None else "Unknown"
            msg = f"HTTP error occurred for server '{server_name}': {e} (Status Code: {status_code})\nResponse: {body}"
            logger.error(msg)
        except requests.exceptions.RequestException as e:
            body = safe_get_response_body(e.response)
            msg = f"Network or connection error occurred while {action_desc} server '{server_name}': {e}\nResponse: {body}"
            logger.error(msg)
        except Exception as e:
            msg = f"An unexpected error occurred: {e}"
            logger.error(msg)

        return False, msg

    def power(self, server_name: str, action: str) -> tuple[bool, str]:
        """
        Power control of an existing Minecraft server

        Args:
            server_name (str): The name of the Minecraft server
            action (str): Power action to perform

        Returns:
            tuple: A tuple containing a bool and str
        """
        logger.info(f"Sending '{action}' request for server '{server_name}'")

        url = f"{self.server_url}/api/power"
        json_data = {
            "server": server_name,
            "action": action
        }

        success, msg = self._send_request(
            url=url,
            json_data=json_data,
            action_desc=f"sent {action} command to",
            server_name=server_name
        )
        return success, msg

    def backup(self, server_name: str) -> tuple[bool, str]:
        """
        Backup an exiting Minecraft server

        Args:
            server_name (str): The name of the Minecraft server

        Returns:
            tuple: A tuple containing a bool and str
        """
        logger.info(f"Sending backup request for server '{server_name}'")

        url = f"{self.server_url}/api/backup"
        json_data = {
            "server": server_name,
        }

        success, msg = self._send_request(
            url=url,
            json_data=json_data,
            action_desc="sent backup command to",
            server_name=server_name
        )
        return success, msg

    def restore_backup(self, server_name: str, backup_id: int=None) -> tuple[bool, str]:
        """
        Restore backup of a Minecraft server

        Args:
            server_name (str): The name of the Minecraft server
            backup_id (int): (Optional) Specific backup id to restore

        Returns:
            tuple: (success (bool), message (str or None))
        """
        logger.info(f"Restoring backup of server '{server_name}'. Backup ID: {backup_id if backup_id else 'latest'}")

        url = f"{self.server_url}/api/restore-backup"
        json_data = {
            "server": server_name,
            "backup_id": backup_id
        }

        success, msg = self._send_request(
            url=url,
            json_data=json_data,
            action_desc=f"sent backup restore command to",
            server_name=server_name
        )
        return success, msg

    def send_command(self, server_name: str, command: str) -> tuple[bool, str]:
        """
        Send command to an exiting Minecraft server

        Args:
            server_name (str): The name of the Minecraft server
            command (str): Command to send

        Returns:
            tuple: A tuple containing a bool and str
        """
        logger.info(f"Sending command '{command}' to server '{server_name}'")

        url = f"{self.server_url}/api/send-command"
        json_data = {
            "server": server_name,
            "command": command
        }

        success, msg = self._send_request(
            url=url,
            json_data=json_data,
            action_desc=f"sent command '{command}' to",
            server_name=server_name
        )
        return success, msg

    def logs(self,
             server_name: str,
             lines: int = None) -> tuple [bool, str]:
        """
        Retrieve logs of a Minecraft server

        Args:
            server_name (str): The name of the Minecraft server
            lines (int): Limit log lines

        Returns:
            tuple: (success (bool), message (str or None))
        """
        logger.info(f"Retrieving logs of server '{server_name}'")

        url = f"{self.server_url}/api/logs"
        json_data = {
            "server": server_name,
            "lines": lines
        }

        success, msg = self._send_request(
            url=url,
            json_data=json_data,
            action_desc=f"retrieved logs",
            server_name=server_name,
            body_mode="raw"
        )

        return success, msg


class SARABHomeController:
    def __init__(self, wol_url: str):
        """
        Initialize class

        Args:
            wol_url (str): URL of an WOL instance
        """
        logger.info(f"Initializing {self.__class__.__name__}...")

        self.wol_url = wol_url

        logger.info(f"Initialized {self.__class__.__name__}")

    @staticmethod
    def _send_request(url: str,
                      json_data: dict,
                      action_desc: str,
                      destination: str,
                      attach_body: bool = False) -> tuple[bool, str]:
        """
        Helper method to execute HTTP POST requests and handle standard exceptions.

        Args:
            url: Endpoint of where to send the request
            json_data (dict): A dictionary containing JSON data to be sent with request
            action_desc (str): Description of why the request was sent for logging purposes
            destination (str): Server to sent action to
            attach_body (bool): (Optional) Attach body info with message in return if success. Default is False

        Returns:
            tuple: success (bool), message (str)
        """

        # Helper function to extract json or text safely without crashing on non-JSON payloads
        def safe_get_response_body(response):
            if response is None:
                return "None"
            try:
                return response.json()
            except requests.exceptions.JSONDecodeError:
                return response.text if response.text else "Empty Response Body"

        try:
            response = requests.post(url=url, json=json_data, timeout=15)
            response.raise_for_status()

            if attach_body:
                body = safe_get_response_body(response)
                msg = f"Successfully {action_desc} at '{destination}'\nResponse: {body}"
            else:
                msg = f"Successfully {action_desc} at '{destination}'"

            logger.info(msg)
            return True, msg

        except requests.exceptions.Timeout as e:
            body = safe_get_response_body(e.response)
            msg = f"Request timed out while {action_desc} at '{destination}'\nResponse: {body}"
            logger.error(msg)
        except requests.exceptions.HTTPError as e:
            body = safe_get_response_body(e.response)
            status_code = e.response.status_code if e.response is not None else "Unknown"
            msg = f"HTTP error occurred for '{destination}': {e} (Status Code: {status_code})\nResponse: {body}"
            logger.error(msg)
        except requests.exceptions.RequestException as e:
            body = safe_get_response_body(e.response)
            msg = f"Network or connection error occurred while {action_desc} at '{destination}': {e}\nResponse: {body}"
            logger.error(msg)
        except Exception as e:
            msg = f"An unexpected error occurred: {e}"
            logger.error(msg)

        return False, msg

    def wol_send(self, device: str = None, mac_address: str = None):
        """
        Send wol request for device to the WOL instance
        Either ``device`` or ``mac_address`` has to have a value.

        Args:
            device (str): (Optional) Device name to send wol request at
            mac_address (str): (Optional) MAC address to send wol request at
        """
        action = "WOL request"
        logger.info(f"Sending {action} at '{device}'")

        url = f"{self.wol_url}/wake"
        json_data = {
            "device": device,
            "mac_address": mac_address
        }

        success, msg = self._send_request(
            url=url,
            json_data=json_data,
            action_desc=f"sent '{action}' to",
            destination=f"{device} ({mac_address})"
        )
        return success, msg



# Primary class
class Client(commands.Bot):
    async def setup_hook(self):
        try:
            guild = GUILD_ID
            synced = await self.tree.sync(guild=guild)
            logger.info(f"Synced {len(synced)} command(s) to guild {guild.id}", True)
        except Exception as e:
            logger.error(f"Error syncing command: {e}")

    async def on_ready(self):
        logger.info(f"Logged in as {self.user}", True)

        try:
            guild = GUILD_ID
            synced = await self.tree.sync(guild=guild)
            logger.info(f"Synced {len(synced)} command(s) to guild {guild.id}", True)
        except Exception as e:
            logger.error(f"Error syncing command: {e}")

    async def on_message(self, message):
        if message.author == self.user:
            return

        logger.debug(f"Message from {message.author}: {message.content}", True)

        if message.content.lower() == "hello sarab bot":
            await message.channel.send(f"Hi there {message.author}")

        await self.process_commands(message)


def main():
    client = Client(command_prefix="!", intents=intents)
    mcsrv_controller = MCServerController(MC_SERVER_MANAGER_URL)
    sarab_home_controller = SARABHomeController(wol_url=WOL_URL)

    if not isinstance(TOKEN, str) or len(TOKEN) <= 0:
        logger.error("'TOKEN' env variable not found. Please check if that key exists on .env file", True)
        return

    # /hello
    @client.tree.command(name="hello", description="Say hello!", guild=GUILD_ID)
    async def command_hello(interaction: discord.Interaction):
        function_name = inspect.currentframe().f_code.co_name
        logger.info(f"Executing '{function_name}'", True)
        await interaction.response.send_message("hello!")

    # /echo
    @client.tree.command(name="echo", description="I will echo anything you give me to echo", guild=GUILD_ID)
    async def command_echo(interaction: discord.Interaction, echo: str):
        function_name = inspect.currentframe().f_code.co_name
        logger.info(f"Executing '{function_name}'", True)
        await interaction.response.send_message(echo)

    # /mcserver_start
    @client.tree.command(name="mcserver_start", description="Start an existing Minecraft server", guild=GUILD_ID)
    async def command_mcserver_start(interaction: discord.Interaction, server_name: str):
        function_name = inspect.currentframe().f_code.co_name
        logger.info(f"Executing '{function_name}'", True)
        _, msg = mcsrv_controller.power(server_name, "start")
        await interaction.response.send_message(msg)

    # /mcserver_stop
    @client.tree.command(name="mcserver_stop", description="Stop an existing Minecraft server", guild=GUILD_ID)
    async def command_mcserver_stop(interaction: discord.Interaction, server_name: str):
        function_name = inspect.currentframe().f_code.co_name
        logger.info(f"Executing '{function_name}'", True)
        _, msg = mcsrv_controller.power(server_name, "stop")
        await interaction.response.send_message(msg)

    # /mcserver_backup
    @client.tree.command(name="mcserver_backup", description="Backup an existing Minecraft server", guild=GUILD_ID)
    async def command_mcserver_backup(interaction: discord.Interaction, server_name: str):
        await interaction.response.defer()
        function_name = inspect.currentframe().f_code.co_name
        logger.info(f"Executing '{function_name}'", True)
        _, msg = mcsrv_controller.backup(server_name)
        await interaction.followup.send(msg)

    # /mcserver_restore_backup
    @client.tree.command(name="mcserver_restore_backup", description="Restore backup of an existing Minecraft server", guild=GUILD_ID)
    async def command_mcserver_restore_backup(interaction: discord.Interaction, server_name: str, backup_id: int = None):
        await interaction.response.defer()
        function_name = inspect.currentframe().f_code.co_name
        logger.info(f"Executing '{function_name}'", True)
        _, msg = mcsrv_controller.restore_backup(server_name=server_name, backup_id=backup_id)
        await interaction.followup.send(msg)

    # /mcserver_command
    @client.tree.command(name="mcserver_command", description="Send command to an existing Minecraft server", guild=GUILD_ID)
    async def command_mcserver_command(interaction: discord.Interaction, server_name: str, command: str):
        function_name = inspect.currentframe().f_code.co_name
        logger.info(f"Executing '{function_name}'", True)
        _, msg = mcsrv_controller.send_command(server_name, command)
        await interaction.response.send_message(msg)

    # /mcserver_logs
    @client.tree.command(name="mcserver_logs", description="Retrieve logs from an existing Minecraft server", guild=GUILD_ID)
    async def command_mcserver_logs(interaction: discord.Interaction, server_name: str, lines: int = None):
        await interaction.response.defer()
        function_name = inspect.currentframe().f_code.co_name
        logger.info(f"Executing '{function_name}'", True)
        _, msg = mcsrv_controller.logs(server_name=server_name, lines=lines)

        if len(msg) > 1900:
            # Send full log as a text file attachment if it exceeds character limits
            file_bytes = io.BytesIO(msg.encode("utf-8"))
            file = discord.File(fp=file_bytes, filename=f"{server_name}_logs.txt")
            await interaction.followup.send(
                content=f"Logs for **{server_name}** have been attached as a file.",
                file=file
            )
        else:
            await interaction.followup.send(f"```text\n{msg}\n```")

    # /wol
    @client.tree.command(name="wol", description="Send wake-on-lan magic packet to a device", guild=GUILD_ID)
    async def command_wol(interaction: discord.Interaction, device: str = None, mac_address: str = None):
        function_name = inspect.currentframe().f_code.co_name
        logger.info(f"Executing '{function_name}'", True)
        _, msg = sarab_home_controller.wol_send(device=device, mac_address=mac_address)
        await interaction.response.send_message(msg)

    client.run(token=TOKEN)


if __name__ == '__main__':
    main()
