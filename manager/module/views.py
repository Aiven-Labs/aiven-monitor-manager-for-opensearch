from rich.console import Console
from rich.table import Table
from module.helpers import helper
from rich import print


class View:
    """
    A class for displaying information about monitors and alerts in an OpenSearch environment.

    This class is responsible for generating and displaying tables that provide insights into the state and
    configuration of monitors and alerts. It utilizes the rich library to create formatted and readable tables
    in the console.

    Attributes:
        local (dict): A dictionary containing local monitor configurations.
        remote (dict): A dictionary containing remote monitor configurations.
        arg (Namespace): An object containing command line arguments.
        config (dict): Configuration settings.
        console (Console): An instance of the Console class from the rich library for formatted output.
        helper (helper): An instance of the helper class for utility functions.

    Methods:
        monitor_info(monitor_diff, alerts, notification_channels): Generates a table displaying detailed information
          about monitors.
        alerts(alerts, notification_channels): Generates a table displaying detailed information about alerts.
    """

    def __init__(self, local_monitors, remote_monitors, arg, config):
        self.local = local_monitors
        self.remote = remote_monitors
        self.arg = arg
        self.config = config
        self.console = Console()
        self.helper = helper(arg)

    def monitor_info(self, monitor_diff, alerts, notification_channels):
        """
        Displays a table with comprehensive information about monitors.

        This method creates a table that lists monitors along with details such as their name, enabled status, version,
        notification settings, number of alerts, and triggers. It also highlights monitors that have updates.

        Args:
            monitor_diff (dict): A dictionary containing differences between local and remote monitors.
            alerts (list): A list of alert data.
            notification_channels (dict): A dictionary of notification channels with their IDs and names.

        Returns:
            None: The method outputs the table to the console.
        """

        table = Table()
        table.add_column("Name", justify="left", no_wrap=True)
        table.add_column("Enabled", justify="left", no_wrap=True)
        table.add_column("Updates", justify="left", no_wrap=True)
        table.add_column("Ver.", justify="left", no_wrap=True, min_width=4)
        table.add_column("Notification", justify="left", no_wrap=True)
        table.add_column("Alerts", justify="left", no_wrap=True)
        table.add_column("Trigger", justify="left", no_wrap=True)
        sortable = []
        channel_counter = {}
        for source in [self.local, self.remote]:
            for id, content in source.items():
                alert_count = 0
                for alert in alerts:
                    if alert["monitor_id"] == id:
                        alert_count += 1
                if alert_count > 0:
                    alert_count = f"[yellow]{alert_count} ->[/yellow]"
                monitor = content["monitor"]
                for trigger in monitor["triggers"]:
                    actions = []
                    mon_type = ""
                    try:
                        for action in trigger["query_level_trigger"]["actions"]:
                            actions.append(action)
                            mon_type = "query_level_trigger"
                    except KeyError:
                        pass

                    try:
                        for action in trigger["document_level_trigger"]["actions"]:
                            actions.append(action)
                            mon_type = "document_level_trigger"
                    except KeyError:
                        pass

                    for action in actions:
                        try:
                            channel = notification_channels[action["destination_id"]]
                        except KeyError:
                            channel = "[red]Unknown notification channel[/red]"
                        if content["_id"] in monitor_diff:
                            has_updates = "[green]Yes[/green]"
                            sortable.append(
                                f"{monitor['name']}|{monitor['enabled']}|{has_updates}|[green]{content['_version']}[/green]|{channel}|{alert_count}|{trigger[mon_type]['name']}"
                            )
                            del monitor_diff[content["_id"]]
                        else:
                            has_updates = "No"
                            sortable.append(
                                f"{monitor['name']}|{monitor['enabled']}|{has_updates}|{content['_version']}|{channel}|{alert_count}|{trigger[mon_type]['name']}"
                            )

        sortable = list(dict.fromkeys(sortable))
        sortable.sort()
        for line in sortable:
            s = line.split("|")
            try:
                channel_counter[s[4]] += 1
            except KeyError:
                channel_counter[s[4]] = 1
            table.add_row(s[0], s[1], s[2], s[3], s[4], s[5], s[6])
        self.console.print(table)
        channel_count = []
        for name, amount in channel_counter.items():
            channel_count.append(f"{name}: {amount}")
        print("Monitor destinations: ", end="")
        print(", ".join(channel_count))

    def alerts(self, alerts, notification_channels):
        """
        Displays a table with detailed information about alerts.

        This method creates a table that provides an overview of alerts, including their state, severity,
        associated monitor and trigger names, start and end times, last notification time, and history.
        It supports filtering by size, severity, and state if specified in the command line arguments.

        Args:
            alerts (list): A list of alert data.
            notification_channels (dict): A dictionary of notification channels with their IDs and names.

        Returns:
            None: The method outputs the table to the console.

        Note:
            The method also displays the number of found alerts and, if applicable, the filters used to
            narrow down the results.
        """
        table_monitor = Table(highlight=True, show_lines=True)
        table_monitor.add_column("State", justify="left", no_wrap=True)
        table_monitor.add_column("Sev.", justify="left", no_wrap=True)
        table_monitor.add_column("Monitor", justify="left", no_wrap=True)
        table_monitor.add_column("Trigger -> Actions", justify="left", no_wrap=False)
        table_monitor.add_column("Start time", justify="left", no_wrap=True)
        table_monitor.add_column("End time", justify="left", no_wrap=True)
        table_monitor.add_column("Last notification", justify="left", no_wrap=True)
        table_monitor.add_column("History", justify="left", no_wrap=False)

        for alert in alerts:
            if self.config["filter"]:
                if self.config["filter"].lower() not in alert["monitor_name"].lower():
                    continue
            # Find destination by id from monitor data
            dest_id_list = []
            actions = []
            try:
                triggers = self.remote[alert["monitor_id"]]["monitor"]["triggers"]
                for trigger in triggers:
                    for level, trigger_contents in trigger.items():
                        if trigger_contents["id"] == alert["trigger_id"]:
                            for action in trigger_contents["actions"]:
                                dest_id_list.append(action["destination_id"])
            except KeyError:
                dest_id_list.append("error")
                pass

            if len(dest_id_list) > 0:
                for dest_id in dest_id_list:
                    if dest_id == "error":
                        actions.append("Key error!")
                    else:
                        actions.append(notification_channels[dest_id])

                if len(actions) == 0:
                    actions = "No actions"
                elif len(actions) == 1:
                    actions = str(actions[0])
                else:
                    actions = ", ".join(actions)
            start_time = self.helper.timestamp_to_string(alert["start_time"])
            end_time = self.helper.timestamp_to_string(alert["end_time"])
            last_notification_time = self.helper.timestamp_to_string(
                alert["last_notification_time"]
            )

            alert_state_mapping = {
                "ERROR": "[red]ERROR[/red]",
                "ACTIVE": "[green]ACTIVE[/green]",
                "ACKNOWLEDGED": "[blue]ACKNOWLEDGED[/blue]",
                "DELETED": "[yellow]DELETED[/yellow]",
            }

            alert_state = alert_state_mapping.get(
                alert["state"].upper(), alert["state"]
            )

            severity_map = {
                "1": "[bold red]CRIT[bold red]",
                "2": "[red]HIGH[red]",
                "3": "[yellow]MED[yellow]",
                "4": "[yellow]LOW[/yellow]",
                "5": "[blue]INFO[/blue]",
            }
            alert["severity"] = severity_map.get(
                alert["severity"], str(alert["severity"])
            )

            linecounter = 0
            if alert["alert_history"]:
                for item in alert["alert_history"]:
                    alert_timestamp = self.helper.timestamp_to_string(item["timestamp"])
                    linecounter += 1
                    if linecounter == 1:
                        table_monitor.add_row(
                            alert_state,
                            alert["severity"],
                            alert["monitor_name"],
                            f"{alert['trigger_name']} [red]->[/red] {actions}",
                            start_time,
                            end_time,
                            last_notification_time,
                            f"{alert_timestamp}: {item['message']}",
                        )
                    else:
                        table_monitor.add_row(
                            " ",
                            " ",
                            " ",
                            " ",
                            " ",
                            " ",
                            "Error history -->",
                            f"{alert_timestamp}: {item['message']}",
                        )
            else:
                if not alert["error_message"]:
                    alert["error_message"] = "[green]-----[/green]"
                table_monitor.add_row(
                    alert_state,
                    alert["severity"],
                    alert["monitor_name"],
                    f"{alert['trigger_name']}\n [red]->[/red] {actions}",
                    start_time,
                    end_time,
                    last_notification_time,
                    "[green]-------[/green]",
                )
        if len(alerts) > 0:
            self.console.print(table_monitor)
        filters = False
        if self.arg.size:
            filters = True
            f1 = f"[bold]size[/bold]: {self.arg.size} "
        else:
            f1 = ""
        if self.arg.severity:
            filters = True
            f2 = f"[bold]severity[/bold]: {self.arg.severity[0]} "
        else:
            f2 = ""
        if self.arg.state:
            filters = True
            f3 = f"[bold]state[/bold]: {self.arg.state[0]}"
        else:
            f3 = ""
        print(f" - Found {len(alerts)} alerts", end="")
        if filters:
            print(f", using filters: {f1}{f2}{f3}")
        else:
            print(".")
