#!/usr/bin/env python3

import json
import yaml
import time
from os import path, listdir
from module.opensearchclient import ManageRemoteMonitors
from module.localstorage import ManageLocalMonitors
from module.comparator import Comparator
from module.config import Configuration
from module.helpers import helper
from module.validators import Validate
from module.slack import SlackMessageBuilder
from module.views import View
from module.metadata import Metadata
from rich.console import Console
from rich.table import Table
from rich import box
from rich import print
from rich import print_json
import argparse
import sys


class main:
    exec_start = time.time()
    parser = argparse.ArgumentParser(
        description="""Aiven Monitor Manager syncs OpenSearch monitors with a local repository. 
Manager can also be used to display information about local and remote monitors and alerts, 
and to validate monitors based on customizable validators."""
    )
    parser.add_argument(
        "-s",
        "--sync",
        help="Scan and sync monitor changes",
        action="store_true",
    )
    parser.add_argument(
        "-r",
        "--run",
        help="Test run monitors, use with -l to run a limited subset. Running monitors does not trigger actions.",
        action="store_true",
    )
    parser.add_argument(
        "-V",
        "--verbose",
        help="Show more verbose output",
        action="store_true",
    )
    parser.add_argument(
        "-d",
        "--dryrun",
        help="Do not make any changes to local or remote monitors",
        action="store_true",
    )
    parser.add_argument(
        "-f",
        "-y",
        "--force",
        "--assume-yes",
        help="Do not require confirmation, assume yes to all",
        action="store_true",
    )
    parser.add_argument(
        "-i",
        "--info",
        help="Show information about monitors",
        action="store_true",
    )

    parser.add_argument(
        "-a",
        "--alerts",
        help="Show recent alerts",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "-as",
        "--state",
        help="Combine with -a, filter alerts by state (active, acknowledged, completer, error, deleted)",
        nargs=1,
        type=str,
        choices=["active", "acknowledged", "completed", "error", "deleted"],
        action="store",
        metavar="state",
        default=[],
    )

    parser.add_argument(
        "-al",
        "--severity",
        help="Combine with -a, filter alerts by severity level (info, low, medium, high, critical)",
        nargs=1,
        type=str,
        choices=["info", "low", "medium", "high", "critical"],
        action="store",
        metavar="severity",
        default=[],
    )

    parser.add_argument(
        "-az",
        "--size",
        help="Combine with -a, return a maximum of N alerts (1-10000)",
        nargs=1,
        type=int,
        action="store",
        metavar="size",
        default=False,
    )

    parser.add_argument(
        "-v",
        "--validate",
        help="validate monitors",
        action="store_true",
    )

    parser.add_argument(
        "-p",
        "--print",
        help="print monitors in JSON or YAML",
        nargs=1,
        type=str,
        choices=["yaml", "json"],
        action="store",
        metavar="json/yaml",
        default=False,
    )

    parser.add_argument(
        "-l",
        "--filter",
        nargs="?",
        type=str,
        help="filter monitors by case-insensitive string match in monitor name",
        action="store",
        metavar="filter",
        default=False,
    )

    if not path.isfile(f"{path.realpath(path.dirname(__file__))}/settings.json"):
        print(
            "\nERROR: Configuration file missing. Generate a template config by running any command except --help.\n"
        )

    arg = parser.parse_args()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    helper = helper(arg)
    console = Console()  # Initialize rich text output

    if not arg.force:
        mode = "interactive"
    else:
        mode = "force"

    if arg.dryrun:
        dryrun_notice = ", [magenta]dry run[/magenta]"
    else:
        dryrun_notice = ""

    print(
        f"\n== Starting [bold white]Aiven Monitor Manager[/bold white] in [underline]{mode}[/underline]{dryrun_notice} mode. =="
    )

    config_handler = Configuration(arg)
    config = config_handler.read_config()  # Parse configuration file

    if arg.filter:
        config["filter"] = arg.filter
    else:
        config["filter"] = None

    notify = SlackMessageBuilder(config)
    do_notify = False

    instance_counter = 0
    for instance in config["instances"]["opensearch"]:
        if instance["active"]:
            if "rename-me" in instance["name"]:
                helper.error(
                    f'Instance {instance["name"]} active but not named. Please edit the configuration template and '
                    f"define your own instances. "
                )
                exit(1)
            instance_counter += 1
            print(
                f"\n[bold]Processing OpenSearch instance {instance['name']}...[/bold]"
            )
            if arg.filter:
                print(
                    f" - Filtering results with case-insensitive term match for '{arg.filter}' in monitor name"
                )
            notify.add(f"Aiven Monitor Manager", "header", "plain_text")
            # Initialize local and remote handlers
            remote = ManageRemoteMonitors(config, instance, arg)
            local = ManageLocalMonitors(config, instance, arg)
            compare = Comparator(config)
            validate = Validate(config, arg)

            local.load_monitors()
            remote.load_monitors()
            channels = remote.get_notification_channels()

            if any(
                (arg.info, arg.alerts, arg.severity, arg.size, arg.state, arg.validate)
            ):
                alerts = remote.get_alerts()

            print(
                f" - Loaded {len(remote.monitors)} remote and {len(local.monitors)} local monitors."
            )

            if arg.validate != False:
                table = Table()
                output = []
                columns = [
                    {"name": "Monitor", "justify": "left", "no_wrap": True},
                    {"name": "Enabled", "justify": "center", "no_wrap": True},
                    {"name": "Mustache", "justify": "center", "no_wrap": True},
                    {"name": "OpsGenie", "justify": "center", "no_wrap": True},
                    {"name": "Slack", "justify": "center", "no_wrap": True},
                    {"name": "Destination", "justify": "left", "no_wrap": True},
                    {"name": "Errors", "justify": "left", "no_wrap": False},
                ]

                for column in columns:
                    table.add_column(
                        column["name"],
                        justify=column["justify"],
                        no_wrap=column["no_wrap"],
                    )

                for monitor in local.monitors.items():
                    monitor = monitor[1]
                    validate.init_errors(monitor)
                    e = validate.enabled(monitor)
                    m = validate.mustache(monitor)
                    n = validate.channels(monitor, channels)
                    o = "-", "-"
                    s = "-", "-"
                    if "slack" in n[2].lower():
                        s = validate.slack(monitor)
                        o = True, "-"
                    if "opsgenie" in n[2].lower():
                        if "heartbeat" not in n[2].lower():
                            o = validate.opsgenie(monitor)
                            s = True, "-"
                        else:
                            o = True, "-"
                            s = True, "-"
                    output.append(
                        f"{monitor['monitor']['name']}|{e[1]}|{m[1]}|{o[1]}|{s[1]}|{n[1]} {n[2]}"
                    )

                output.sort()
                for line in output:
                    i = line.split("|")
                    errors = []
                    try:
                        for error in validate.errors[i[0]]:
                            errors.append(f"- {error}")
                        printable_errors = "\n".join(errors)
                    except KeyError:
                        printable_errors = ""

                    table.add_row(i[0], i[1], i[2], i[3], i[4], i[5], printable_errors)
                console.print(table)

            if arg.info:
                view = View(local.monitors, remote.monitors, arg, config)
                compare.compare_monitors(local.monitors, remote.monitors)
                print(f" - Showing monitor information.")
                try:
                    view.monitor_info(compare.monitor_diff, alerts, channels)
                except KeyError as e:
                    helper.error(
                        "Notification channel not found - please validate monitors with --validate.",
                        f"{e.__class__.__name__}: {e}",
                    )

            if arg.alerts or arg.severity or arg.size or arg.state:
                view = View(local.monitors, remote.monitors, arg, config)
                print(f" - Showing alerting information.")
                view.alerts(alerts, channels)

            if arg.print:
                do_print = True
                if len(local.monitors) > 10:
                    do_print = helper.confirm(
                        f"Printing {len(local.monitors)} results, consider using the --filter"
                        f" option to narrow down results.\nDo you want to continue?",
                        "print",
                    )
                if do_print == True:
                    for id, content in local.monitors.items():
                        print(
                            f"-------- Printing monitor {content['monitor']['name']} --------"
                        )
                        if arg.print[0] == "json":
                            print(json.dumps(content, indent=2))
                        elif arg.print[0] == "yaml":
                            print(yaml.dump(content))
                        print("-" * (len(content["monitor"]["name"]) + 35))
            if arg.run:
                print(f"[bold]Running local monitors...[/bold]")
                run_count = 0
                for id, monitor in local.monitors.items():
                    run_count += 1
                    if (monitor["monitor"]["enabled"] == True) or (arg.force == True):
                        run_results = remote.run_monitor(id)
                        status = ""
                        if monitor["monitor"]["enabled"] != True:
                            status = " [yellow](disabled)[/yellow]"
                        # print(run_results)
                        print(
                            f" - {run_count} Ran {run_results['monitor_name']}{status}, searched last {((run_results['period_end'] - run_results['period_start']) / 1000) / 60} minutes: ",
                            end="",
                        )
                        if run_results["error"] != None:
                            print(f"Run error: {run_results['error']}")
                            continue
                        for result in run_results["input_results"]["results"]:
                            try:
                                if len(result["hits"]["hits"]) > 0:
                                    prefix = f"[green]"
                                    suffix = f"[/green]"
                                else:
                                    prefix = suffix = ""
                                print(
                                    f"{prefix}{len(result['hits']['hits'])} hits in {result['took']}ms.{suffix}"
                                )
                            except KeyError:
                                print(f"No hits.")
                        if arg.verbose:
                            print(f"   Full results for monitor id {id}:")
                            print(run_results)
                    else:
                        print(
                            f" - [yellow]Not running[/yellow] disabled monitor {monitor['monitor']['name']}. Use --force to run."
                        )

            if arg.sync:
                notify.add(
                    f'Updates made to OpenSearch instance *{instance["name"]}*, running as user '
                    f"`{remote.print_username()}`"
                )
                notify.add(type="divider")
                print(
                    f"[bold]Cleaning up local folders for folder / name mismatches...[/bold]"
                )
                # Run cleanup job on local folders
                local.clean_folders()
                if local.cleanup:
                    for removed_dir, new_dir in local.cleanup.items():
                        print(
                            f" - Moved [cyan]{removed_dir}[/cyan] to [cyan]{new_dir}[/cyan]"
                        )
                    local.load_monitors()
                else:
                    print(" - [green]OK[/green]: No name mismatches found.")

                # Check for duplicate and pathsafe names in remote monitors
                duplicate_remote_names = []
                for remote_id, remote_contents in remote.monitors.items():
                    if remote_contents["monitor"]["name"] in duplicate_remote_names:
                        helper.error(
                            f"Duplicate names found in OpenSearch: {{remote_contents['monitor']['name']}}. This will cause local storage conflicts. "
                            "Please remove the duplicate monitors."
                        )
                    else:
                        duplicate_remote_names.append(
                            remote_contents["monitor"]["name"]
                        )

                    if not helper.pathsafe(remote_contents["monitor"]["name"]):
                        helper.error(
                            f"File-path unsafe monitor name found in OpenSearch. Please rename the monitor.",
                            f"'{remote_contents['monitor']['name']}'",
                        )

                # Store new remote monitors
                for monitor_id in remote.monitors:
                    if monitor_id in local.monitors:
                        continue
                    else:
                        local.store_monitor(monitor_id, remote.monitors[monitor_id])
                        # Add new remote monitors to local monitors
                        local.monitors[monitor_id] = remote.monitors[monitor_id]
                        print(
                            f" - Storing [cyan]{remote.monitors[monitor_id]['monitor']['name']}[/cyan]..."
                        )

                # Create new local monitors
                print(f"[bold]Searching for new local monitors...[/bold]")
                created_new = False
                skipped = []
                for monitor_id in local.monitors:
                    if monitor_id in remote.monitors:
                        continue
                    else:
                        print(
                            f" - New monitor found: {local.monitors[monitor_id]['monitor']['name']}"
                        )
                        if helper.confirm(
                            "Do you want to create a new remote monitor?"
                        ):
                            created_new = True
                            print(
                                f" - Creating {local.monitors[monitor_id]['monitor']['name']}... ",
                                end="",
                            )
                            new_id, new_contents = remote.create_monitor(
                                helper.prepare_for_create(local.monitors[monitor_id])
                            )
                            print(f"created with ID {new_id}.")
                            local.store_monitor(new_id, new_contents)
                            do_notify = True
                            notify.add(
                                f"Created:\n```Name: {new_contents['monitor']['name']}\nMonitor ID: {new_id}\nType: "
                                f"{new_contents['monitor']['monitor_type']}```"
                            )
                        else:
                            skipped.append(monitor_id)
                for id in skipped:
                    del local.monitors[id]

                if created_new:
                    local.load_monitors()
                    remote.load_monitors()
                else:
                    print(" - [green]OK[/green]: No new monitors found.")

                print("[bold]Checking for updated remote monitors...[/bold]")
                # Check if remote monitors have higher versions than local monitors
                compare.check_version_state(local.monitors, remote.monitors)
                if compare.version_sync_mismatch:
                    for id, info in compare.version_sync_mismatch.items():
                        print(
                            f" - Monitor {info[0]} remote version {info[1]} is newer than local version {info[2]}"
                        )
                        confirmation = helper.confirm(
                            "Do you want to update local monitor? Updating will overwrite local changes.",
                            "sync",
                        )
                        if confirmation:
                            print(
                                f" - Updating local version for {local.monitors[id]['monitor']['name']}"
                            )
                            local.store_monitor(id, remote.monitors[id])
                        else:
                            print(f" - Skipping {info[0]}...")

                    local.load_monitors()
                    local.clean_folders()
                else:
                    print(" - [green]OK[/green]: Monitor versions match.")

                print("[bold]Checking local monitors for changes...[/bold]")
                compare.compare_monitors(local.monitors, remote.monitors)
                if compare.monitor_diff:
                    diff_counter = 0
                    for monitor_id, difference in compare.monitor_diff.items():
                        diff_counter += 1
                        print(
                            f" - [{diff_counter}/{len(compare.monitor_diff)}] Found local changes in [bold]{local.monitors[monitor_id]['monitor']['name']}[/bold]:"
                        )
                        difference = json.loads(difference)

                        # Parse differences to an easy-to-read format
                        print_json(data=difference)

                        confirmation = helper.confirm(
                            "Do you want to update the remote monitor with these changes?",
                            "monitor_update",
                        )
                        if confirmation:
                            updated_id, updated_contents = remote.update_monitor(
                                monitor_id, local.monitors[monitor_id]
                            )
                            local.store_monitor(updated_id, updated_contents)
                            do_notify = True
                            notify.add(
                                f"Updated *{local.monitors[monitor_id]['monitor']['name']}*\n"
                                f"```{json.dumps(difference, indent=2)}```"
                            )
                else:
                    print(
                        f" - [green]OK[/green]: No changes found, local and remote monitors match."
                    )
                notify.add(type="divider")
                notify.add(f"Total monitors on instance: {len(remote.monitors)}")

                print(f"[bold]Updating monitor README files...[/bold]")
                meta = Metadata(config, instance, arg)
                meta.generate(local.monitors, channels)
                if meta.created:
                    for item in meta.created:
                        print(
                            f" - Created template metadata.json for {local.monitors[item]['monitor']['name']}"
                        )

                print(f" - [green]OK[/green]: Everything up to date.")

        elif not instance["active"]:
            continue

        if instance_counter == 0:
            helper.error("No instances configured. Please review settings.json.")
        if do_notify:
            notify.send()
    print(
        f"\n== All done, Aiven Monitor Manager exiting, took {round((time.time() - exec_start), 2)}s. =="
    )


if __name__ == "__main__":
    main()
