import chevron
import json


class Validate:
    """
    A validation class for evaluating the configuration of monitors in an OpenSearch environment.

    This class is designed to perform various validation checks on monitor configurations, such as checking if monitors
    are enabled, validating specific configurations for OpsGenie and Slack notifications, ensuring correct Mustache
    template syntax, and verifying notification channels.

    Attributes:
        arg (Namespace): An object containing command line arguments.
        config (dict): Configuration settings for validation.
        errors (dict): A dictionary to store validation errors, indexed by monitor names.

    Methods:
        init_errors(monitor): Initializes the error tracking for a given monitor.
        enabled(monitor): Validates if a monitor is enabled.
        opsgenie(monitor): Validates the OpsGenie configuration of a monitor.
        slack(monitor): Validates the Slack configuration of a monitor.
        mustache(monitor): Checks if Mustache templates in monitor actions are correctly formatted.
        channels(monitor, channels): Validates if the monitor's actions reference valid notification channels.
    """

    def __init__(self, config, arg):
        self.arg = arg
        self.config = config
        self.errors = {}

    def init_errors(self, monitor):
        """
        Initializes the error list for a given monitor.

        This method is called to set up an empty list of errors for a monitor, which will be populated during the
        validation process.

        Args:
            monitor (dict): The monitor configuration.

        Returns:
            None
        """
        if monitor.get("_id") != False:
            monitor = monitor["monitor"]
        self.errors[monitor["name"]] = []

    def enabled(self, monitor):
        """
        Validates if a monitor is enabled and records any relevant errors.

        This method checks whether a monitor is enabled and logs an error if it is not. It handles cases where the
        enabled status is missing or has an unexpected value.

        Args:
            monitor (dict): The monitor configuration.

        Returns:
            tuple: A tuple containing a boolean indicating if the monitor is enabled and a string representing the
              validation result for display.
        """
        if monitor.get("_id") != False:
            monitor = monitor["monitor"]

        if not monitor["name"]:
            return False, "[red]Err[/red]"

        try:
            if monitor["enabled"] is True:
                return True, "[green]Yes[/green]"
            elif monitor["enabled"] is False:
                self.errors[monitor["name"]].append("Monitor disabled")
                return False, "[red]No[/red]"
            else:
                self.errors[monitor["name"]].append(
                    "Unknown value for 'monitor.enabled', expecting boolean"
                )
                return False, "[yellow]Unknown[/yellow]"
        except KeyError:
            self.errors[monitor["name"]].append(
                "Key and value for 'monitor.enabled' not found."
            )
            return False, "[red]Fail[/red]"

    def opsgenie(self, monitor):
        """
        Validates the OpsGenie configuration for a monitor.

        This method checks for the correct configuration of OpsGenie alerts in the monitor's actions. It validates
        mandatory keys like 'message', 'description', and 'priority', and logs any errors found.

        Args:
            monitor (dict): The monitor configuration.

        Returns:
            tuple: A tuple containing a boolean indicating the validation result and a string representing the
              result for display.
        """
        if monitor.get("_id") != False:
            monitor = monitor["monitor"]

        if not monitor["name"]:
            return False, "[red]Err[/red]"

        if monitor["triggers"]:
            for trigger in monitor["triggers"]:
                actions = []
                try:
                    for action in trigger["query_level_trigger"]["actions"]:
                        actions.append(action)
                except KeyError:
                    pass

                try:
                    for action in trigger["document_level_trigger"]["actions"]:
                        actions.append(action)
                except KeyError:
                    pass
                for action in actions:
                    if len(action["subject_template"]["source"]) != 0:
                        self.errors[monitor["name"]].append(
                            "Slack message set, OpsGenie webhook will fail"
                        )
                        return False, "[red]Fail[/red]"

                    try:
                        opsgenie_json = json.loads(action["message_template"]["source"])
                        message = opsgenie_json.get("message")
                        description = opsgenie_json.get("description")
                        priority = opsgenie_json.get("priority")

                        if not message:
                            self.errors[monitor["name"]].append(
                                "Key error, OpsGenie mandatory key 'message' missing."
                            )
                            return False, "[red]Fail[/red]"

                        if not description:
                            self.errors[monitor["name"]].append(
                                "Key error, OpsGenie key 'description' missing."
                            )
                            return False, "[red]Fail[/red]"

                        if not priority:
                            self.errors[monitor["name"]].append(
                                "Key error, OpsGenie key 'priority' missing."
                            )
                            return False, "[red]Fail[/red]"

                        if not priority.startswith("P"):
                            self.errors[monitor["name"]].append(
                                "Error in OpsGenie priority, value does not start with P"
                            )
                            return False, "[red]Fail[/red]"

                        if priority != "P{{ctx.trigger.severity}}":
                            self.errors[monitor["name"]].append(
                                f"Priority is not defined with variable, is '{priority}'"
                            )

                        return True, "[green]Pass[/green]"

                    except json.decoder.JSONDecodeError:
                        self.errors[monitor["name"]].append(
                            "JSON decode error while parsing OpsGenie JSON"
                        )
                        return False, "[red]Fail[/red]"

        return False, "[yellow]Miss[/yellow]"

    def slack(self, monitor):
        """
        Validates the Slack configuration for a monitor.

        This method checks the Slack notification setup in the monitor's actions, ensuring that necessary fields like
        'subject' and 'message' are present and logs any errors.

        Args:
            monitor (dict): The monitor configuration.

        Returns:
            tuple: A tuple containing a boolean indicating the validation result and a string representing the result
              for display.
        """
        if monitor["_id"]:
            monitor = monitor["monitor"]

        if not monitor["name"]:
            return False, "[red]Err[/red]"

        if monitor["triggers"]:
            for trigger in monitor["triggers"]:
                actions = []
                try:
                    for action in trigger["query_level_trigger"]["actions"]:
                        actions.append(action)
                except KeyError:
                    pass

                try:
                    for action in trigger["document_level_trigger"]["actions"]:
                        actions.append(action)
                except KeyError:
                    pass
                for action in actions:
                    if len(action["subject_template"]["source"]) < 1:
                        self.errors[monitor["name"]].append("Slack subject missing")
                        return False, "[red]Fail[/red]"
                    if len(action["message_template"]["source"]) < 1:
                        return False, "[red]Fail[/red]"
            return True, "[green]Pass[/green]"
        else:
            self.errors[monitor["name"]].append("Monitor has no triggers")
        return False, "[yellow]Miss[/yellow]"

    def mustache(self, monitor):
        """
        Validates Mustache template syntax in the monitor's actions.

        This method checks if Mustache templates used in monitor actions are correctly formatted and logs any rendering
        errors encountered.

        Args:
            monitor (dict): The monitor configuration.

        Returns:
            tuple: A tuple containing a boolean indicating the validation result, a string representing the result
              for display, and an additional message if applicable.
        """
        if monitor.get("_id") != False:
            monitor = monitor["monitor"]

        if not monitor["name"]:
            return False, "None"

        if monitor["triggers"]:
            for trigger in monitor["triggers"]:
                actions = []
                try:
                    for action in trigger["query_level_trigger"]["actions"]:
                        actions.append(action)
                except KeyError:
                    pass

                try:
                    for action in trigger["document_level_trigger"]["actions"]:
                        actions.append(action)
                except KeyError:
                    pass
                for action in actions:
                    try:
                        chevron.render(action["message_template"]["source"])
                        # Check for presence of required Mustache values
                        return True, "[green]Pass[/green]"
                    except Exception as e:
                        self.errors[monitor["name"]].append(
                            f"Mustache rendering error: {e}"
                        )
                        return False, "[red]Fail[/red]"
        else:
            self.errors[monitor["name"]].append("No triggers defined")
            return False, "[yellow]Miss[/yellow]", ""

    def channels(self, monitor, channels):
        """
        Validates if the monitor's actions reference valid notification channels.

        This method checks if each action in the monitor's triggers points to a valid notification channel in the
        provided channel list and logs any discrepancies.

        Args:
            monitor (dict): The monitor configuration.
            channels (dict): A dictionary of available notification channels.

        Returns:
            tuple: A tuple containing a boolean indicating the validation result, a string representing the result
              for display, and the name of the destination channel if found.
        """
        if monitor.get("_id") != False:
            monitor = monitor["monitor"]

        if not monitor["name"]:
            return False, "None"

        if monitor["triggers"]:
            for trigger in monitor["triggers"]:
                actions = []
                try:
                    for action in trigger["query_level_trigger"]["actions"]:
                        actions.append(action)
                except KeyError:
                    pass

                try:
                    for action in trigger["document_level_trigger"]["actions"]:
                        actions.append(action)
                except KeyError:
                    pass
                for action in actions:
                    try:
                        destination = channels[action["destination_id"]]
                        return True, "[green]Pass[/green]", destination
                    except KeyError:
                        return False, "[red]Fail[/red]", "Not found"
        else:
            return False, "[yellow]Miss[/yellow]", ""
