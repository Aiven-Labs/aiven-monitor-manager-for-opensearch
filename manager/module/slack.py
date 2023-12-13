import requests
import json


class SlackMessageBuilder:
    """
    A class for building Slack JSON messages to be sent via webhook.

    Args:
        config (dict): A dictionary containing configuration data for the SlackMessageBuilder.

    Attributes:
        config (dict): A dictionary containing configuration data for the SlackMessageBuilder.
        slack_message (dict): A dictionary representing the Slack message being built.
        slack_webhook (str): The URL of the Slack webhook to which the message will be sent.

    Methods:
        __init__(self, config): Constructor method for initializing the SlackMessageBuilder.
        __str__(self): Returns a string representation of the Slack message being built.
        add(self, type, format, content): Adds a block to the Slack message being built.
        send(self): Sends the Slack message to the configured webhook.
    """

    def __init__(self, config):
        """
        Constructor method for initializing the SlackMessageBuilder.

        Args:
            config (dict): A dictionary containing configuration data for the SlackMessageBuilder.
        """
        self.config = config
        self.slack_message = {}
        self.slack_message["blocks"] = []
        self.slack_webhook = self.config["global"]["slack webhook"]

    def __str__(self):
        """
        Returns a string representation of the Slack message being built.

        Returns:
            str: A string representation of the Slack message being built.
        """
        return f"{json.dumps(self.slack_message, indent=2)}"

    def add(self, content="", type="section", format="mrkdwn"):
        """
        Adds a block to the Slack message being built.

        Args:
            type (str, optional): The type of block to add. Defaults to "section".
            format (str, optional): The format of the text in the block. Defaults to "mrkdwn".
            content (str, optional): The content of the text in the block. Defaults to "".

        Returns:
            None
        """
        if type == "divider":
            slack_block = {}
            slack_block["type"] = "divider"
            self.slack_message["blocks"].append(slack_block)
        else:
            slack_block = {}
            slack_block["type"] = type
            slack_block["text"] = {}
            slack_block["text"]["type"] = format
            slack_block["text"]["text"] = content
            self.slack_message["blocks"].append(slack_block)

    def send(self):
        """
        Sends the Slack message to the configured webhook if one is configured.

        Raises:
            requests.exceptions.RequestException: If there is an error while sending the Slack message.

        Returns:
            None
        """
        if self.slack_webhook[0:5] == "https":
            requests.post(self.slack_webhook, str(self.slack_message))
