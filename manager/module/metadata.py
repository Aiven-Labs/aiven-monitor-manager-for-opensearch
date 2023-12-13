import json
from os import path
from module.helpers import helper


class Metadata:
    """
    A class for managing and generating metadata for monitors in an OpenSearch environment.

    This class handles the creation of README files and metadata JSON files for each monitor, based on their
    configuration and operational status. It supports operations such as metadata generation, README file writing, and
     JSON file creation and reading for monitor metadata.

    Attributes:
        helper (helper): An instance of the helper class for utility functions.
        config (dict): Configuration settings for managing metadata.
        arg (Namespace): An object containing command line arguments.
        instance (dict): A dictionary containing details of the current OpenSearch instance.
        instance_path (str): The file path to the instance's monitor directory.
        monitor_metadata (dict): A dictionary to store metadata for each monitor.
        created (list): A list to keep track of newly created monitors.

    Methods:
        generate(all_monitors, channels): Generates missing metadata for all monitors.
        write_readme(monitor, metadata, channels): Writes a README file for a monitor based on its metadata.
        create_json(monitor, force=False): Creates a metadata JSON file for a monitor.
        read_json(monitor): Reads the metadata JSON file for a monitor and stores its contents.
    """

    def __init__(self, config, instance, arg):
        """
        Initializes the Metadata class with configuration, instance details, and command-line arguments.

        Args:
            config (dict): Configuration settings for managing metadata.
            instance (dict): A dictionary containing details of the current OpenSearch instance.
            arg (Namespace): An object containing command line arguments.
        """
        self.helper = helper(arg)
        self.config = config
        self.arg = arg
        self.instance = instance
        self.helper = helper(arg)
        self.instance_path = (
            f"{self.config['global']['monitor root path']}{self.instance['name']}/"
        )
        self.monitor_metadata = {}
        self.created = []

    def generate(self, all_monitors, channels):
        """
        Generates missing metadata for all monitors and writes README files.

        This method iterates through all monitors, generates metadata JSON files if they are missing, reads existing
        metadata, and writes README files based on the metadata and monitor configuration.

        Args:
            all_monitors (dict): A dictionary containing all monitors.
            channels (list): A list containing channels information.
        """
        for id, monitor in all_monitors.items():
            if self.create_json(monitor, force=False):
                self.created.append(id)
            self.read_json(monitor)
            try:
                self.write_readme(monitor, self.monitor_metadata[id], channels)
            except KeyError:
                pass

    def write_readme(self, monitor, metadata, channels):
        """
        Writes a README file for a given monitor using its metadata and operational details.

        The README includes information such as monitor name, version, status, description, triggers, attributes, and
        references. It uses badges for visual representation of monitor status and severity.

        Args:
            monitor (dict): The monitor configuration.
            metadata (dict): The metadata associated with the monitor.
            channels (list): A list containing channel information for monitor actions.

        Returns:
            bool: True if dry run is enabled, otherwise no return value.
        """
        if self.arg.dryrun:
            return True
        else:
            monitor_name = monitor["monitor"]["name"]
            monitor_path = f"{self.instance_path}{monitor_name}/"
            severity_map = {
                1: "Critical",
                2: "High",
                3: "Medium",
                4: "Low",
                5: "Info",
            }
            severity_badges = {
                1: '![critical badge](https://img.shields.io/badge/P1-CRITICAL-red "Critical") ',
                2: '![high badge](https://img.shields.io/badge/P2-HIGH-orange "High") ',
                3: '![medium badge](https://img.shields.io/badge/P3-MEDIUM-yellow "Medium") ',
                4: '![low badge](https://img.shields.io/badge/P4-LOW-yellow "Low") ',
                5: '![info  badge](https://img.shields.io/badge/P5-INFO-blue "Info") ',
            }
            readme = ""
            readme += f"# {monitor['monitor']['name']} (ver. {monitor['_version']})\n"
            if monitor["monitor"]["enabled"] == True:
                readme += "![Status: Enabled](https://img.shields.io/badge/status-enabled-green)\n"
            elif monitor["monitor"]["enabled"] == False:
                readme += "![Status: Disabled](https://img.shields.io/badge/status-disabled-red)\n"
            else:
                readme += "![Status: Unknown](https://img.shields.io/badge/status-unknown-yellow)\n"

            readme += f"## Description\n\n> {metadata['description']}\n\n"

            try:
                for input in monitor["monitor"]["inputs"]:
                    index_list = []
                    for index in input["search"]["indices"]:
                        index_list.append(index)
                    readme += f"Search indexes: `{', '.join(index_list)}`\n"
            except KeyError:
                pass

            readme += f"\n**Author**: {metadata['author']}\n"
            try:
                readme += f"\n**Schedule**: `{monitor['monitor']['schedule']}`\n"
            except Exception:
                pass

            readme += f"## Triggers\n\n"

            for trigger in monitor["monitor"]["triggers"]:
                readme += "| Trigger | Severity |  Action --> Destination |\n"
                readme += "| :------ | :------- | :---------- |\n"
                readme += f"| {trigger['query_level_trigger']['name']} | {severity_badges[int(trigger['query_level_trigger']['severity'])]} | "
                for action in trigger["query_level_trigger"]["actions"]:
                    template = str(action["message_template"]["source"])
                    try:
                        readme += f"{action['name']} --> {channels[action['destination_id']]}<br>"
                    except KeyError:
                        readme += f"{action['name']} --> Unknown destination ID {action['destination_id']}<br>"
                    readme += "|\n"
                    readme += "\n```\n" + template.replace("\\n", "\n") + "\n```\n\n"

            readme += f"## Attributes\n\n"
            readme += "| Attribute | Value |\n" "|-----------|-------|\n"
            for key, value in metadata["attributes"].items():
                if type(value) != list:
                    value = [value]
                for value in value:
                    if key == "MITRE Technique" and value != "not defined":
                        metadata["references"].append(
                            f"[{key} {value}](https://attack.mitre.org/techniques/{value.split(' ', 1)[0].replace('.', '/')}/)"
                        )
                    if key == "MITRE Tactic" and value != "not defined":
                        metadata["references"].append(
                            f"[{key} {value}](https://attack.mitre.org/tactics/{value.split(' ', 1)[0].replace('.', '/')}/)"
                        )
                    if key == "MITRE Data Source" and value != "not defined":
                        metadata["references"].append(
                            f"[{key} {value}](https://attack.mitre.org/datasources/{value.split(' ', 1)[0].replace('.', '/')}/)"
                        )
                    readme += f"| {key} | {value} |\n"
            readme += "\n"
            readme += "## References\n"
            ref_counter = 0
            for reference in metadata["references"]:
                ref_counter += 1
                readme += f"> {ref_counter}: {reference}  \n"

            readme += "\n_This file has been automatically generated based on monitor and metadata contents. Any changes will be discarded._\n"

            with open(f"{monitor_path}README.md", "w") as output_file:
                output_file.write(readme)
                output_file.write("\n")
            return True

    def create_json(self, monitor, force=False):
        """
        Creates a metadata JSON file for a monitor.

        This method generates a metadata JSON file for a given monitor. It includes default fields and values, which
        can be overridden with user-defined metadata from settings.json.

        Args:
            monitor (dict): The monitor configuration.
            force (bool, optional): If True, overwrites an existing metadata JSON file. Defaults to False.

        Returns:
            bool: True if the metadata JSON file was created successfully, False otherwise.
        """
        if self.arg.dryrun:
            return False
        else:
            data = {}
            monitor_name = monitor["monitor"]["name"]
            monitor_path = f"{self.instance_path}{monitor_name}/"

            if path.exists(f"{monitor_path}metadata.json") and not force:
                return False

            data["id"] = monitor["_id"]
            data["description"] = "No description"
            data["author"] = "Unknown author"
            data["attributes"] = {}
            data["references"] = []

            # Add user-defined metadata attributes or default ones
            metadata_template_attributes = self.config.get("global", {}).get(
                "metadata_template_attributes"
            )
            if metadata_template_attributes:
                for value in metadata_template_attributes:
                    data["attributes"][value] = "not defined"
            else:
                data["attributes"]["MITRE Tactic"] = "not defined"
                data["attributes"]["MITRE Technique"] = "not defined"
                data["attributes"]["MITRE Data Source"] = "not defined"
                data["attributes"]["Playbook"] = "[link](https://)"

            # Add user-defined metadata references or default ones
            metadata_template_references = self.config.get("global", {}).get(
                "metadata_template_references"
            )
            if metadata_template_references:
                data["references"] = metadata_template_references
            else:
                data["references"] = [
                    "https://attack.mitre.org/datasources/",
                    "https://attack.mitre.org/matrices/enterprise/",
                ]

            # Write metadata.json file
            with open(f"{monitor_path}metadata.json", "w") as output_file:
                json.dump(data, output_file, indent=2)
                output_file.write("\n")
            return True

    def read_json(self, monitor):
        """
        Reads the metadata JSON file for a monitor and stores its contents in the monitor_metadata dictionary.

        If the metadata JSON file does not exist, this method will attempt to create it.

        Args:
            monitor (dict): The monitor configuration.

        Returns:
            bool: True if the metadata JSON file was read successfully, False otherwise.
        """
        monitor_name = monitor["monitor"]["name"]
        monitor_path = f"{self.instance_path}{monitor_name}/"

        # If dryrun flag is set, return True without doing anything
        if self.arg.dryrun:
            return True

        # If metadata.json doesn't exist, create it
        if not path.exists(f"{monitor_path}metadata.json"):
            self.create_json(monitor)

        # Try to read metadata.json file and add contents to monitor_metadata dictionary
        try:
            with open(f"{monitor_path}metadata.json", "r") as input_file:
                try:
                    metadata = json.load(input_file)
                except Exception as e:
                    self.helper.error(
                        f"Can not parse '{monitor_path}metadata.json'.", e
                    )
        except FileNotFoundError:
            print("DEBUG: No metadata found.")
            return False

        self.monitor_metadata[monitor["_id"]] = metadata
        return True
