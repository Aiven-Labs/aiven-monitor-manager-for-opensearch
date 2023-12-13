import json
from os import path, getenv, listdir
from module.helpers import helper
from rich import print


class Configuration:
    """
    A class for managing and manipulating configuration files for OpenSearch or similar systems.

    The Configuration class is designed to read, parse, and create JSON configuration files. It provides functionality
     for reading existing configuration files, generating template configurations if none exists, and handling
     path-unsafe characters in configuration values.

    Attributes:
        helper (Helper): An instance of a Helper class, used for utility functions like error handling.
        config_file (str): The file path of the JSON configuration file.
        config (dict): A dictionary representing the parsed configuration data.
        unsafe_characters (str): A string containing characters that are considered unsafe for file paths.

    Methods:
        read_config(): Reads, parses, and validates a configuration file, or creates a template if none exists.
        create_config(): Creates a template configuration file with default settings.
    """

    def __init__(self, arg):
        """
        Initializes the Configuration object with necessary attributes.

        Args:
            arg: An argument required by the helper function for initialization.
        """
        self.helper = helper(arg)
        self.config_file = f"{path.realpath(path.dirname(__file__))}/../settings.json"
        self.config = {}
        self.unsafe_characters = '/\?%*:|"<>.'

    def read_config(self):
        """
        Reads and parses the configuration file, validates its contents, and returns the configuration data.

        This method reads a configuration file in JSON format, parses it, and performs validation checks such as URL
        format and path-safe characters. If the configuration file does not exist, it calls `create_config()` to
        generate a template configuration file.

        Returns:
            dict: A dictionary representing the parsed and validated configuration data.

        Raises:
            SystemExit: If the configuration file contains invalid JSON, if the instance name contains path-unsafe
             characters or starts with a space, or if other critical errors occur.
        """
        if path.isfile(self.config_file):
            with open(self.config_file, "r") as config_file:
                try:
                    self.config = json.loads(config_file.read())
                    self.config["global"][
                        "monitor root path"
                    ] = f"{path.realpath(path.dirname(__file__))}/../../monitors/"
                    if self.config["global"]["slack webhook"]:
                        if self.config["global"]["slack webhook"][0:8] != "https://":
                            slack_env_var = self.config["global"][
                                "slack webhook"
                            ].upper()
                            self.config["global"]["slack webhook"] = getenv(
                                slack_env_var
                            )
                            if self.config["global"]["slack webhook"] == None:
                                self.helper.error(
                                    f"Slack webhook configured but can not find environment variable {slack_env_var}"
                                )
                        else:
                            pass

                except json.decoder.JSONDecodeError as e:
                    self.helper.error(
                        f"Can not parse JSON: {self.config_file}. Fix the file structure or delete the file and run command again to create a template.",
                        e,
                    )
                    print(f"Parse error: {e}")
                    exit(1)
            for instance in self.config["instances"]["opensearch"]:
                for key, value in instance.items():
                    if key == "name":
                        if self.helper.pathsafe(value) == False:
                            self.helper.error(
                                f'Aborting! Path-unsafe characters in instance name "{value}". Not allowed: {self.unsafe_characters}'
                            )
                            exit(1)
            return dict(self.config)
        else:
            self.create_config()
            self.helper.error(
                f"Configuration file missing, {self.config_file} not found.\nCreating a template configuration. Please edit the file to set your preferences."
            )

    def create_config(self):
        """
        Creates a template configuration file in JSON format.

        This method generates a default configuration template with predefined structures and saves it to the
        configuration file path. It is typically called when an existing configuration file is not found.

        Returns:
            None

        Raises:
            SystemExit: If there is an error while writing the configuration template to the file.
        """
        self.config["global"] = {}
        self.config["global"]["slack webhook"] = ""
        self.config["global"]["metadata_template_attributes"] = [
            "MITRE technique",
            "MITRE Tactic",
            "MITRE Data Source",
            "Playbook",
        ]
        self.config["global"]["metadata_template_references"] = [
            "https://attack.mitre.org/datasources/",
            "https://attack.mitre.org/matrices/enterprise/",
        ]
        self.config["instances"] = {}
        self.config["instances"]["opensearch"] = []
        existing_instances = listdir(
            f"{path.realpath(path.dirname(__file__))}/../../monitors/"
        )
        for entry in existing_instances:
            if entry[0:1] == ".":
                existing_instances.remove(entry)
        if len(existing_instances) > 0:
            for instance in existing_instances:
                print("a")
                self.config["instances"]["opensearch"].append(
                    {
                        "active": False,
                        "name": instance,
                        "url": "https://url:port",
                        "env_username": f"{instance.upper()}_USERNAME",
                        "env_password": f"{instance.upper()}_PASSWORD",
                        "note": "Automatically added instance, pre-existing monitor folder found.",
                    }
                )
        self.config["instances"]["opensearch"].append(
            {
                "active": False,
                "name": "example-opensearch-1",
                "url": "https://url:port",
                "env_username": "OS1_API_USERNAME",
                "env_password": "OS1_API_PASSWORD",
            }
        )
        self.config["instances"]["opensearch"].append(
            {
                "active": False,
                "name": "example-opensearch-2",
                "url": "https://url:port",
                "env_username": "OS2_API_USERNAME",
                "env_password": "OS2_API_PASSWORD",
            }
        )

        try:
            with open(self.config_file, "w") as config_file:
                config_file.write(json.dumps(self.config, indent=2))
                return None
        except Exception as e:
            self.helper.error(
                f"Unable to write configuration template to {self.config_file}.", e
            )
