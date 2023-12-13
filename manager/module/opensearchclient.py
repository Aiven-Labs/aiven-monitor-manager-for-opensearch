import requests
import json
from module.helpers import helper
from dotenv import load_dotenv, find_dotenv
from os import getenv
from rich import print


class ManageRemoteMonitors:
    """
    A class for managing and interacting with remote OpenSearch monitors.

    This class provides functionality to create, update, and retrieve monitors and alerts from an OpenSearch instance.
    It supports operations such as querying OpenSearch, updating existing monitors, creating new monitors, and
    handling notification channels.

    Attributes:
        headers (dict): Common headers used for HTTP requests.
        helper (helper): An instance of the helper class for utility functions.
        arg (Namespace): An object containing command line arguments.
        config (dict): Configuration settings for managing monitors.
        instance (dict): A dictionary containing details of the OpenSearch instance.
        username (str): The username for authenticating with the OpenSearch instance.
        password (str): The password for authenticating with the OpenSearch instance.
        monitors (dict): A dictionary to store monitor information.

    Methods:
        print_username(): Returns the username.
        get(uri_path, data=None): Performs a GET request to the OpenSearch instance.
        put(uri_path, data): Performs a PUT request to update a resource in OpenSearch.
        post(uri_path, data): Performs a POST request to create a resource in OpenSearch.
        load_monitors(): Loads monitor data from OpenSearch.
        get_monitor_contents(monitor_id): Retrieves contents of a specific monitor.
        update_monitor(monitor_id, monitor_contents): Updates a monitor with given contents.
        create_monitor(monitor): Creates a new monitor in OpenSearch.
        get_notification_channels(): Retrieves notification channel information from OpenSearch.
        get_alerts(): Retrieves alerts from the OpenSearch alerting system.
        run_monitor(monitor_id): Executes a monitor and returns the result.
    """

    headers = {"Content-Type": "application/json"}

    def __init__(self, config, instance, arg):
        """
        Initializes the ManageRemoteMonitors class with configuration, instance details, and command-line arguments.

        Args:
            config (dict): Configuration settings for managing remote monitors.
            instance (dict): A dictionary containing details of the OpenSearch instance.
            arg (Namespace): An object containing command line arguments.
        """
        load_dotenv(find_dotenv())
        self.helper = helper(arg)
        self.arg = arg
        self.config = config
        self.instance = instance
        self.unsafe_characters = '/\?%*:|"<>.'
        self.username = getenv(self.instance["env_username"])
        self.password = getenv(self.instance["env_password"])
        self.monitors = {}

        if not self.username or not self.password:
            self.helper.error(
                f"Missing credentials. Please add your credentials to environmental variables, expecting username: ${self.instance['env_username']}, password: ${self.instance['env_password']}.\nTo store credentials in a file, create an .env file with the variables in the manager/ folder."
            )
        if "AVNS_" in self.username:
            self.helper.error(
                "Aborting! String 'AVNS_' found in username, are you sure that's not your password?"
            )

    def print_username(self):
        """
        Returns the username used for authentication with the OpenSearch instance.

        Returns:
            str: The username.
        """
        return str(self.username)

    def get(self, uri_path, data=None):
        """
        Performs an HTTP GET request to the specified URI path on the OpenSearch instance and returns the JSON response.

        Args:
            uri_path (str): The URI path to query.
            data (dict, optional): Additional data to send with the request. Defaults to None.

        Returns:
            str: The response from the OpenSearch instance as a JSON string.

        Raises:
            SystemExit: If the response status code is not 200.
            requests.exceptions.ConnectionError: If a connection error occurs.
        """
        try:
            response = requests.get(
                f"{self.instance['url']}{uri_path}",
                headers=self.headers,
                auth=(self.username, self.password),
                data=data,
            )
            if response.status_code == 200:
                json_data = json.loads(response.text)
                return json.dumps(json_data, indent=2)
            else:
                print(
                    f"Server {self.instance['url']} returned error {response.status_code}: {response.text}"
                )
                exit(1)
        except requests.exceptions.ConnectionError as e:
            self.helper.error(
                "Connection error. Please check connectivity to the address of your instance.",
                e,
            )

    def put(self, uri_path, data):
        """ "
        Performs an HTTP PUT request to the specified URI path on the OpenSearch instance to update a monitor.

        Args:
            uri_path (str): The API path to update the monitor.
            data (str): The data to be sent in the request body as a string.

        Returns:
            bool: True if the update is successful, False otherwise.

        Raises:
            requests.exceptions.RequestException: If there is an error with the request.

        """
        if self.arg.dryrun:
            return True

        else:
            response = requests.put(
                f"{self.instance['url']}{uri_path}",
                headers=self.headers,
                auth=(self.username, self.password),
                data=data,
            )
            if response.status_code == 200:
                return True
            else:
                self.helper.error(
                    f"Server {self.instance['url']} returned error {response.status_code}: {response.text}"
                )

    def post(self, uri_path, data):
        """
        Sends an HTTP POST request to create a new resource on the OpenSearch instance.

        This method is used to create new resources, such as monitors or alerts, on the OpenSearch instance by sending
        the specified data to a given API path. The method supports a dry run mode, which simulates the POST request
        without actually creating the resource on OpenSearch.

        Args:
            uri_path (str): The API path where the POST request should be sent. This path should be relative to the
              base URL of the OpenSearch instance.
            data (str): A string representation of the data to be sent in the POST request. This data should be in a
               format acceptable by the OpenSearch API (typically JSON).

        Returns:
            dict or bool: Depending on the response status code:
                - If the status code is 200, it returns a dictionary parsed from the response text.
                - If the status code is 201, it indicates a successful resource creation, and a dictionary parsed
                   from the response text is returned.
                - If the `dryrun` flag is set, it returns the parsed data as a dictionary.
                - In other cases, the method raises an error.

        Raises:
            requests.exceptions.RequestException: If there is an error in making the POST request.
            RuntimeError: If the OpenSearch server returns an unexpected status code, indicating a failure to create
               the resource.

        Note:
            The method provides error handling for unexpected status codes by raising a RuntimeError with details from
            the response. In `dryrun` mode, no actual POST request is made, and the method returns the parsed input
            data, allowing for testing or validation of the data to be sent without affecting the OpenSearch instance.
        """
        if self.arg.dryrun:
            return json.loads(data)
        else:
            response = requests.post(
                f"{self.instance['url']}{uri_path}",
                headers=self.headers,
                auth=(self.username, self.password),
                data=data,
            )
            if response.status_code == 200:
                return json.loads(response.text)
            elif response.status_code == 201:
                return json.loads(response.text)
            else:
                self.helper.error(
                    f"Server {self.instance['url']} returned error {response.status_code}: {response.text}"
                )

    def load_monitors(self):
        """
        Fetches and loads all monitor configurations from the OpenSearch instance into a dictionary.

        This method sends a query to the OpenSearch instance to retrieve information about all configured monitors.
        It processes the response to extract relevant monitor data and stores it in an internal dictionary, making it
        accessible for further operations. The method also supports filtering of monitors based on a configuration
        filter, if specified.

        Returns:
            None: This method updates the `monitors` attribute of the class instance, which is a dictionary where each
              key is a monitor ID and the value is the monitor's configuration details.

        Raises:
            requests.exceptions.RequestException: If there is an error in making the request to the OpenSearch API.
            json.JSONDecodeError: If there is an error in parsing the JSON response from the OpenSearch API.

        Note:
            The method uses a 'match_all' query to retrieve up to 10,000 monitors, which should suffice for most
            instances. If a filter is set in the class configuration, only monitors with names containing the filter
            text (case-insensitive) are included in the `monitors` dictionary. The method also standardizes the monitor
            data by resetting the 'last_update_time' field to 0 for each monitor and restructuring the response
            format for consistency.
        """

        query = '{"size": 10000,"query": {"match_all": {}}}'
        response = json.loads(
            self.get("/_plugins/_alerting/monitors/_search", data=query)
        )
        for monitor in response["hits"]["hits"]:
            del monitor["_index"]
            del monitor["_score"]
            monitor["monitor"] = monitor.pop("_source")
            monitor["monitor"]["last_update_time"] = 0

            if self.config["filter"]:
                if self.config["filter"].lower() in monitor["monitor"]["name"].lower():
                    self.monitors[monitor["_id"]] = monitor
            else:
                self.monitors[monitor["_id"]] = monitor

    def get_monitor_contents(self, monitor_id):
        """
        Retrieves detailed information for a specific monitor from the OpenSearch instance using its ID.

        This method makes an HTTP GET request to the OpenSearch Alerting API to fetch detailed information about a
        monitor. It parses the JSON response to provide a comprehensive view of the monitor's configuration, including
        its triggers, conditions, and actions. The method also sets the 'last_update_time' field in the response to 0,
        which can be useful for comparison or synchronization purposes.

        Args:
            monitor_id (str): The unique identifier of the monitor whose details are to be retrieved.

        Returns:
            tuple: A tuple containing two elements:
                1. The monitor ID (str).
                2. A dictionary with the monitor's details as retrieved from the OpenSearch API. This includes all
                   relevant configuration settings and properties of the monitor.

        Raises:
            requests.exceptions.RequestException: If an error occurs during the HTTP GET request to the OpenSearch API.
            json.JSONDecodeError: If there is an issue decoding the JSON response, indicating a possible problem with
            the API response format.

        Note:
            The 'last_update_time' field in the monitor's details is reset to 0 in the returned data. This is a
            deliberate choice to standardize the data format, especially when used for comparisons or subsequent
            processing.
        """
        request = self.get(f"/_plugins/_alerting/monitors/{monitor_id}")
        monitor_contents = json.loads(request)
        monitor_contents["monitor"]["last_update_time"] = 0
        return monitor_id, monitor_contents

    def update_monitor(self, monitor_id, monitor_contents):
        """
        Updates a specified monitor on the OpenSearch instance with new content.

        This method sends a request to the OpenSearch API to update an existing monitor with the provided contents.
        It is capable of handling full monitor configurations including conditions, triggers, and actions. If the
        `dryrun` flag is set, the monitor will not be actually updated, but the intended changes will be returned.

        Args:
            monitor_id (str): The unique identifier of the monitor to be updated.
            monitor_contents (dict): A dictionary containing the new contents for the monitor. This should include all
             necessary configurations that define the monitor's behavior and properties.

        Returns:
            tuple: A tuple where the first element is the monitor ID and the second element is a dictionary containing
              the updated monitor contents. If `dryrun` is set, the returned contents will be the same as the input
              `monitor_contents`.

        Raises:
            requests.exceptions.RequestException: If an error occurs during the PUT request to the OpenSearch API.
            json.JSONDecodeError: If there is an issue decoding the response from the OpenSearch API into JSON format.
            This may indicate a problem with the API response.

        Note:
            The method prints a message to the console indicating the beginning of the update process. If the `dryrun`
             flag is set in the `arg` attribute, no actual update will take place, and the method will simply return
              the provided `monitor_id` and `monitor_contents`.
        """
        print(
            f" - Updating monitor {monitor_contents['monitor']['name']} {monitor_id}..."
        )

        if self.arg.dryrun:
            return monitor_id, monitor_contents

        else:
            json_data = json.dumps(monitor_contents["monitor"], indent=2)
            self.put(f"/_plugins/_alerting/monitors/{monitor_id}", json_data)
            monitor_id, updated_monitor = self.get_monitor_contents(monitor_id)
            return monitor_id, updated_monitor

    def create_monitor(self, monitor):
        """
        Creates a new monitor on the OpenSearch instance using the provided configuration.

        This method submits a new monitor configuration to OpenSearch via an HTTP POST request. The monitor's
        configuration is specified in the provided dictionary. It includes various settings such as conditions,
        triggers, actions, and scheduling details. If the `dryrun` flag is set, the monitor creation is simulated and
        the monitor configuration is returned without actual creation in OpenSearch.

        Args:
            monitor (dict): A dictionary containing the full configuration of the monitor to be created.
              This includes all necessary parameters and settings defining the monitor's behavior.

        Returns:
            tuple: A tuple containing:
                1. The newly created monitor ID (str), as assigned by OpenSearch.
                2. A dictionary representing the monitor configuration as stored in OpenSearch. This includes
                  any modifications or additions made by OpenSearch during the creation process.

        Raises:
            requests.exceptions.RequestException: If there is an error with the POST request to the OpenSearch API.
            json.JSONDecodeError: If there is an issue decoding the JSON response from OpenSearch, indicating a
              possible problem with the response format.

        Note:
            If the `dryrun` flag is enabled, the method will not actually create the monitor on OpenSearch. Instead, it
            will return the provided monitor configuration along with a simulated monitor ID, allowing for testing or
            validation of the configuration without affecting the OpenSearch instance.
        """
        if self.arg.dryrun:
            return monitor["_id"], monitor

        else:
            json_data = json.dumps(monitor)
            new_monitor = self.post(f"/_plugins/_alerting/monitors/", json_data)
            new_monitor["monitor"]["last_update_time"] = 0
            return new_monitor["_id"], new_monitor

    def get_notification_channels(self):
        """
        Retrieves the notification channel configurations from an OpenSearch instance.

        This method queries the OpenSearch API to obtain a list of configured notification channels. It supports
        different API endpoints based on the major version of OpenSearch (version 1 or 2). The method first determines
        the OpenSearch version and then fetches the notification channel data accordingly.

        Returns:
            dict: A dictionary where each key is the ID of a notification channel, and the corresponding value is the
            name of the channel. This dictionary represents all the notification channels configured in the OpenSearch
            instance.

        Raises:
            requests.exceptions.RequestException: If there is an error in making the request to the OpenSearch API.
            json.JSONDecodeError: If there is an error in parsing the JSON response from the OpenSearch API.
            RuntimeError: If the OpenSearch instance is running an unknown major version that is not supported by this method.

        Note:
            The method differentiates between OpenSearch version 1 and version 2, as they have different API endpoints
            and response formats for notification channel configurations. If the version is neither 1 nor 2, a
            RuntimeError is raised, indicating an unsupported OpenSearch version.
        """
        request = self.get("/")
        version_data = json.loads(request)
        version = version_data["version"]["number"]
        version_parts = version.split(".")
        notification_channels = {}

        if version_parts[0] == "2":
            request = self.get("/_plugins/_notifications/configs")
            output = json.loads(request)
            for config_item in output["config_list"]:
                notification_channels[config_item["config_id"]] = config_item["config"][
                    "name"
                ]

        elif version_parts[0] == "1":
            request = self.get("/_plugins/_alerting/destinations")
            output = json.loads(request)
            for config_item in output["destinations"]:
                notification_channels[config_item["id"]] = config_item["name"]

        else:
            self.helper.error(
                "Unknown OpenSearch major version - expecting version 1 or 2. Can not retrieve notification channels.",
                version_data,
            )

        return notification_channels

    def get_alerts(self):
        """
        Retrieves a list of alerts from the OpenSearch instance, optionally filtered by severity, state, and size.

        This method sends a request to the OpenSearch Alerting API to retrieve a list of alerts. It supports filtering
        of the alerts based on their state (e.g., ACTIVE, ACKNOWLEDGED), severity level (e.g., INFO, LOW, MEDIUM, HIGH,
        CRITICAL), and limits the number of alerts returned by specifying a size. The alerts are sorted by their start
        time in ascending order.

        Returns:
            list: A list containing alert data as returned by the OpenSearch API. Each element in the list is a
              dictionary representing an individual alert, including details like its state, severity, and associated
              monitor information.

        Raises:
            requests.exceptions.RequestException: If an error occurs while making the request to the OpenSearch API.
            json.JSONDecodeError: If there is an issue parsing the response from the OpenSearch API.

        Note:
            The method dynamically constructs the query parameters based on the presence of `size`, `state`, and
            `severity` arguments. If these arguments are not set, default values or all-inclusive filters are used.
            The method is designed to provide a flexible way to query a potentially large set of alert data from OpenSearch.
        """

        state = ""
        severity = ""
        size = "100"

        if self.arg.size:
            size = str(self.arg.size[0])

        if self.arg.state:
            state = f"&alertState={self.arg.state[0].upper()}"

        if self.arg.severity:
            if self.arg.severity[0].upper() == "INFO":
                severity = f"&severityLevel=5"
            elif self.arg.severity[0].upper() == "LOW":
                severity = f"&severityLevel=4"
            elif self.arg.severity[0].upper() == "MEDIUM":
                severity = f"&severityLevel=3"
            elif self.arg.severity[0].upper() == "HIGH":
                severity = f"&severityLevel=2"
            elif self.arg.severity[0].upper() == "CRITICAL":
                severity = f"&severityLevel=1"
            else:
                severity = ""

        request = self.get(
            f"/_plugins/_alerting/monitors/alerts?size={size}&sortString=start_time&sortOrder=asc{severity}{state}"
        )
        alerts = json.loads(request)
        alerts = alerts["alerts"]
        return alerts

    def run_monitor(self, monitor_id):
        """
        Executes a specified monitor in a dry run mode using the OpenSearch Alerting plugin.

        This method triggers the execution of a monitor identified by its ID on the OpenSearch instance. It runs the
        monitor in a dry run mode, meaning it simulates the monitor's execution without actually performing the
        alerting actions. This is useful for testing and verifying monitor configurations.

        Args:
            monitor_id (str): The ID of the monitor to execute.

        Returns:
            dict: A dictionary containing the results of the monitor execution. This includes details such as the
            monitor's conditions, actions, and triggered alerts, if any.

        Raises:
            requests.exceptions.RequestException: If there is an error with the POST request.
            json.JSONDecodeError: If there is an error decoding the JSON response from the POST request.
        """
        result = self.post(
            f"/_plugins/_alerting/monitors/{monitor_id}/_execute?dryrun=true", data=""
        )
        return result
