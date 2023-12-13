from rich import print
from datetime import datetime


class helper:
    """
    A utility class providing a set of helper functions for error handling, user confirmations, path safety checks,
    and other miscellaneous tasks.

    Attributes:
        arg (Namespace): An object containing command line arguments.
        confirm_all (dict): A dictionary to store confirmation states for different events.

    Methods:
        error(message, e=""): Prints an error message and exits the program.
        confirm(message, event="general"): Asks the user for confirmation on a specific task or event.
        pathsafe(s): Checks if a string is safe to be used as a path.
        timestamp_to_string(timestamp): Converts a timestamp to a human-readable string.
        prepare_for_create(monitor): Prepares a monitor configuration for creation, removing unnecessary fields.
    """

    def __init__(self, arg):
        """
        Initializes the helper class with command line arguments.

        Args:
            arg (Namespace): An object containing command line arguments.
        """
        self.arg = arg
        self.confirm_all = {}  # Store "all" confirmation state by event

    def error(self, message, e=""):
        """
        Prints an error message and additional details if provided, then exits the program.

        Args:
            message (str): The primary error message to be displayed.
            e (optional, str or Exception): Additional details or exception information to be displayed. Defaults
              to an empty string.
        """
        print(f"[red]Error:[/red] {message}")
        if e:
            print(f"[red]Details:[/red] {e}")
        print("Exiting...")
        exit(1)

    def confirm(self, message, event="general"):
        """
        Requests user confirmation for a specified message and event.

        Depending on the command line arguments, this method may automatically confirm the action or ask the user for
        confirmation. Supports a global 'all' confirmation for a specific event. Notifies of dry run when no changes
        are made.

        Args:
            message (str): The message to display when asking for confirmation.
            event (str): The event type for which confirmation is being requested. Defaults to "general".

        Returns:
            bool: True if the action is confirmed, otherwise False.
        """
        if self.arg.force:
            return True

        if self.arg.dryrun:
            prefix = "[magenta](DRY RUN, no changes made)[/magenta]"
        else:
            prefix = ""

        try:
            if self.confirm_all[event]:
                return True
        except KeyError:
            self.confirm_all[event] = False

        confirmation = ""
        while confirmation == "":
            print(f"{prefix} [red]{message}[/red]", end="")
            confirmation = input(f" [yes/no/all] ")

        if confirmation.lower() in ["y", "yes"]:
            return True
        elif confirmation.lower() in ["a", "all"]:
            self.confirm_all[event] = True
            return True
        else:
            return False

    def pathsafe(self, s):
        """
        Checks if the given string is safe to be used as a path.

        This function verifies that the string does not contain any characters that are unsafe for file paths and does
        not start with a space.

        Args:
            s (str): The string to be checked for path safety.

        Returns:
            bool: True if the string is safe to use as a path, otherwise False.
        """
        unsafe_chars = ["\\", "/", ":", "*", "?", '"', "<", ">", "|"]
        if s and s[0] == " ":
            return False
        for char in s:
            if char in unsafe_chars:
                return False
        return True

    def timestamp_to_string(self, timestamp):
        """
        Converts a UNIX timestamp to a human-readable string format.

        Args:
            timestamp (int or str): The UNIX timestamp to be converted.

        Returns:
            str: The human-readable string representation of the timestamp, or '-' if the timestamp is None.
        """
        if timestamp is not None:
            return f"{str(datetime.fromtimestamp(int(str(timestamp)[:-3])))}"
        else:
            return "-"

    def prepare_for_create(self, monitor):
        """
        Prepares a monitor configuration for creation by removing certain keys.

        This method is used to clean up a monitor configuration, removing keys that are not necessary for the creation
        of a new monitor in OpenSearch.

        Args:
            monitor (dict): The monitor configuration to be prepared.

        Returns:
            dict: The cleaned monitor configuration.
        """
        content = monitor["monitor"]
        if not self.pathsafe(content["name"]):
            self.error(
                f"Monitor name {content['name']} is not filepath safe. Please rename the monitor."
            )
        remove_keys = ["enabled_time", "last_update_time", "data_sources", "owner"]
        for key in remove_keys:
            try:
                del content[key]
            except KeyError:
                continue
        try:
            for trigger in content["triggers"]:
                del trigger["document_level_trigger"]["id"]
                for action in trigger["document_level_trigger"]["actions"]:
                    del action["id"]
        except KeyError:
            pass

        try:
            for trigger in content["triggers"]:
                del trigger["query_level_trigger"]["id"]
                for action in trigger["query_level_trigger"]["actions"]:
                    del action["id"]
        except KeyError:
            pass
        return content
