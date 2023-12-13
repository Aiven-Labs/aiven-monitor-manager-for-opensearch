from deepdiff import DeepDiff


class Comparator:
    """
    A class to compare OpenSearch monitors between two different JSON configurations.

    The Comparator class is designed to analyze and identify differences between local and remote OpenSearch monitor
    configurations. It provides functionality to compare monitors, check for version synchronization mismatches, and
    identify changes in monitor names.

    Attributes:
        config (dict): Configuration settings for the Comparator.
        version_sync_mismatch (dict): A dictionary to store monitor IDs and their respective version differences.
        name_sync_mismatch (list): A list to store monitor IDs that have name discrepancies.
        monitor_diff (dict): A dictionary to store differences between local and remote monitors.

    Methods:
        compare_monitors(local_monitors, remote_monitors): Compares all monitors and identifies changes.
        check_version_state(local_monitors, remote_monitors): Checks for version synchronization mismatches between
          local and remote monitors.
        check_name_state(local_monitors, remote_monitors): Identifies monitors that have different names in local and
           remote configurations.
    """

    def __init__(self, config):
        """
        Initializes the Comparator with the given configuration.

        Args:
            config (dict): Configuration settings for the Comparator, including necessary parameters for comparison operations.
        """
        self.config = config
        self.version_sync_mismatch = {}
        self.name_sync_mismatch = []
        self.monitor_diff = {}

    def compare_monitors(self, local_monitors, remote_monitors):
        """
        Compares all monitors between local and remote configurations for changes and stores the differences.

        This method compares the 'monitor' field of each monitor in the local and remote configurations using DeepDiff.
         Differences are stored in the 'monitor_diff' attribute.

        Args:
            local_monitors (dict): A dictionary containing the local monitors with their IDs as keys.
            remote_monitors (dict): A dictionary containing the remote monitors with their IDs as keys.
        """
        for monitor_id, contents in local_monitors.items():
            local_contents = contents["monitor"]
            remote_contents = remote_monitors[monitor_id]["monitor"]
            result = DeepDiff(remote_contents, local_contents, view="tree")
            if result:
                self.monitor_diff[monitor_id] = result.to_json()

    def check_version_state(self, local_monitors, remote_monitors):
        """
        Checks for version synchronization mismatches between local and remote monitors.

        This method compares the '_version' field of each monitor in the local and remote configurations. If the local
        version is older, it records the monitor ID along with both versions in the 'version_sync_mismatch' attribute.

        Args:
            local_monitors (dict): A dictionary containing the local monitors with their IDs as keys.
            remote_monitors (dict): A dictionary containing the remote monitors with their IDs as keys.
        """
        for id, remote_version in remote_monitors.items():
            local_version = local_monitors[id]
            if int(local_version["_version"]) < int(remote_version["_version"]):
                self.version_sync_mismatch[id] = [
                    local_version["monitor"]["name"],
                    remote_version["_version"],
                    local_version["_version"],
                ]

    def check_name_state(self, local_monitors, remote_monitors):
        """
        Identifies monitors that have different names in local and remote configurations.

        This method compares the 'name' field of the 'monitor' object for each monitor in local and remote
        configurations. It prints a message if a name mismatch is found and stores the monitor ID in the
        'name_sync_mismatch' attribute.

        Args:
            local_monitors (dict): A dictionary containing the local monitors with their IDs as keys.
            remote_monitors (dict): A dictionary containing the remote monitors with their IDs as keys.
        """
        for id, remote_version in remote_monitors.items():
            local_version = local_monitors[id]
            if local_version["monitor"]["name"] != remote_version["monitor"]["name"]:
                print(
                    f"Monitor renamed! Local monitor: {local_version['monitor']['name']} Remote monitor: {remote_version['monitor']['name']}"
                )
                self.name_sync_mismatch.append(id)
