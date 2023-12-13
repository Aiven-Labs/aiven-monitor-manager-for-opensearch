import json
import random
import string
from os import makedirs, listdir, rmdir, remove, path
from module.helpers import helper


class ManageLocalMonitors:
    """
    A class for managing local monitors in an OpenSearch environment.

    This class provides functionalities to clean up monitor directories, store and remove monitors, and load all
    existing monitors into a manageable structure.

    Attributes:
        helper (helper): An instance of the helper class for utility functions.
        config (dict): Configuration settings for managing monitors.
        instance_name (str): The name of the current OpenSearch instance.
        arg (Namespace): An object containing command line arguments.
        instance_path (str): The file path to the instance's monitor directory.
        monitors (dict): A dictionary to store monitor information.
        cleanup (dict): A dictionary to track cleanup operations.

    Methods:
        clean_folders(): Renames local folders to match monitor names and removes mismatches.
        store_monitor(monitor_id, monitor_contents, metadata={}): Stores an individual monitor's data in a file.
        remove_monitor(monitor_name): Removes a monitor from the system.
        load_monitors(): Retrieves all stored monitors in the instance subfolder.
    """

    def __init__(self, config, instance, arg):
        """
        Initializes the ManageLocalMonitors class with configuration, instance details, and command-line arguments.

        Args:
            config (dict): Configuration settings for managing monitors.
            instance (dict): A dictionary containing details of the current OpenSearch instance.
            arg (Namespace): An object containing command line arguments.
        """
        self.helper = helper(arg)
        self.config = config
        self.instance_name = instance["name"]
        self.arg = arg
        self.helper = helper(arg)
        self.instance_path = (
            f"{self.config['global']['monitor root path']}{self.instance_name}/"
        )
        self.monitors = {}
        self.cleanup = {}

    def clean_folders(self):
        """
        Cleans and organizes monitor directories by renaming them to match monitor names and removing directories
        that do not correspond to a valid monitor.

        This method also handles mismatches and asks for user confirmation before moving or deleting directories.

        Returns:
            dict: A dictionary containing the removed folder names as keys and their corresponding monitor names as values.
        """
        if self.arg.dryrun:
            return True
        else:
            try:
                makedirs(f"{self.instance_path}")
            except FileExistsError:
                pass
            directories = [
                x for x in listdir(f"{self.instance_path}") if not x.startswith(".")
            ]  # remove dotfiles

            for monitor_dir in directories:
                # Skip files in root directory
                if path.isfile(f"{self.instance_path}{monitor_dir}"):
                    continue
                try:
                    with open(
                        f"{self.instance_path}{monitor_dir}/monitor.json", "r"
                    ) as contents:
                        try:
                            monitor = json.loads(contents.read())
                        except Exception as e:
                            self.helper.error(
                                f"File '{monitor_dir}/monitor.json' contains errors.",
                                f"{e.__class__.__name__}: {e}",
                            )
                except FileNotFoundError:
                    list = listdir(f"{self.instance_path}{monitor_dir}")
                    if not list:
                        rmdir(f"{self.instance_path}{monitor_dir}")
                        continue
                    else:
                        self.helper.error(
                            f"File monitor.json missing, but directory {monitor_dir} is not empty. Please manually remove the files to re-sync local monitor.",
                            f"Files in directory: {list}",
                        )
                if self.helper.pathsafe(monitor["monitor"]["name"]):
                    pass
                else:
                    badchars = ", ".join(["\\", "/", ":", "*", "?", '"', "<", ">", "|"])
                    self.helper.error(
                        f"Monitor name '{monitor['monitor']['name']}' contains forbidden characters ({badchars}). Please rename the monitor before continuing."
                    )

                if monitor_dir != monitor["monitor"]["name"]:
                    confirmation = self.helper.confirm(
                        f'Do you want to move mismatching monitor from /{monitor_dir} to /{monitor["monitor"]["name"]}?',
                        "mismatch",
                    )
                    if (self.arg.dryrun != True) and (confirmation == True):
                        try:
                            with open(
                                f"{self.instance_path}{monitor_dir}/metadata.json"
                            ) as metafile:
                                metadata = json.loads(metafile.read())
                            remove(f"{self.instance_path}{monitor_dir}/metadata.json")
                        except FileNotFoundError:
                            metadata = {}
                            pass
                        try:
                            remove(f"{self.instance_path}{monitor_dir}/README.md")
                        except FileNotFoundError:
                            pass
                        remove(f"{self.instance_path}{monitor_dir}/monitor.json")
                        rmdir(f"{self.instance_path}{monitor_dir}")
                        self.store_monitor(monitor["_id"], monitor, metadata)
                    self.cleanup[monitor_dir] = monitor["monitor"]["name"]

    def store_monitor(self, monitor_id, monitor_contents, metadata={}):
        """
        Stores the contents of a monitor, including its metadata, in a specific directory structure.

        Args:
            monitor_id (str): The unique identifier of the monitor.
            monitor_contents (dict): The contents of the monitor in JSON format.
            metadata (dict, optional): Additional metadata associated with the monitor. Defaults to an empty dict.

        Returns:
            bool: True if the monitor was stored successfully, False otherwise.
        """

        monitor_name = monitor_contents["monitor"]["name"]
        monitor_path = f"{self.instance_path}{monitor_name}/"

        if self.arg.dryrun:
            return True
        else:
            try:
                makedirs(f"{monitor_path}")
            except FileExistsError:
                pass
            with open(f"{monitor_path}monitor.json", "w") as output_file:
                output_file.write(json.dumps(monitor_contents, indent=2))
                output_file.write("\n")
            if metadata:
                with open(f"{monitor_path}metadata.json", "w") as output_file:
                    output_file.write(json.dumps(metadata, indent=2))
                    output_file.write("\n")
            return True

    def remove_monitor(self, monitor_name):
        """
        Removes a monitor and its associated files from the local file system.

        Args:
            monitor_name (str): The name of the monitor to be removed.

        Raises:
            FileNotFoundError: If the monitor file or directory does not exist.
            OSError: If there is an error while removing the monitor file or directory.

        Returns:
            None
        """

        if self.arg.dryrun:
            return True
        else:
            files_to_remove = ["monitor.json", "metadata.json", "README.md"]
            for file in files_to_remove:
                try:
                    remove(f"{self.instance_path}{monitor_name}/{file}")
                except FileNotFoundError:
                    pass

            rmdir(f"{self.instance_path}{monitor_name}")

    def load_monitors(self):
        """
        Loads all monitors from the instance subfolder into a dictionary for management and filtering.

        This method reads monitor data from local directories, handles JSON decoding, and manages monitor versions.

        Returns:
            dict: A dictionary containing all stored monitors, where the keys are monitor IDs and the values are monitor objects.
        """
        try:
            makedirs(f"{self.instance_path}")
        except FileExistsError:
            pass
        all_monitors = {}
        directories = []
        files = []
        dirlist = [
            x for x in listdir(f"{self.instance_path}") if not x.startswith(".")
        ]  # remove dotfiles

        for item in dirlist:
            full_path = f"{self.instance_path}{item}"
            if path.isdir(full_path):
                directories.append(item)
            elif path.isfile(full_path):
                files.append(full_path)
            else:
                pass

        for monitor_dir in directories:
            try:
                with open(
                    f"{self.instance_path}{monitor_dir}/monitor.json", "r"
                ) as contents:
                    try:
                        monitor = json.loads(contents.read())
                    except Exception as e:
                        self.helper.error(
                            f"JSON decode error: Can not load monitor from '{self.instance_path}{monitor_dir}/monitor.json'",
                            e,
                        )
                    if not "_id" in monitor:
                        self.helper.error(
                            "Parsing error: No '_id' found in new monitor."
                        )
                    if monitor["_id"]:
                        monitor_id = monitor["_id"]
                    else:
                        monitor_id = "create" + "".join(
                            random.choice(string.ascii_lowercase) for i in range(10)
                        )
                    contents.close()
            except FileNotFoundError:
                continue

            if monitor_id in all_monitors:
                if monitor["_version"] > all_monitors[monitor_id]["_version"]:
                    self.remove_monitor(all_monitors[monitor_id]["monitor"]["name"])
                    all_monitors[monitor_id] = monitor
                else:
                    self.remove_monitor(monitor["monitor"]["name"])
            else:
                all_monitors[monitor_id] = monitor

        if self.config["filter"]:
            filtered_monitors = {}
            for id, monitor in all_monitors.items():
                if self.config["filter"].lower() in monitor["monitor"]["name"].lower():
                    filtered_monitors[id] = monitor
            self.monitors = filtered_monitors
        else:
            self.monitors = all_monitors
