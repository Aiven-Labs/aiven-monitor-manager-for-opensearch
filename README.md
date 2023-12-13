# Aiven Monitor Manager

Aiven Monitor Manager is designed to simplify monitor management for OpenSearch and allow for
handling OpenSearch monitors as code, storing the versions and changes into a repository. It 
utilizes the OpenSearch API for reading, writing and updating monitors using the well-known 
and generally available Requests package. It is an interactive command line application and it's
output is meant for human consumption.

# Installation
1. Clone the repository and switch to repository folder
2. go to ``manager`` folder
3. Create a virtual environment: `python3 -m venv ./venv`
4. Activate the virtual environment `source ./venv/bin/activate`
5. Install requirements `pip3 install -r requirements.txt`
   1. If you have errors regarding `cython` try:
        `PIP_CONSTRAINT=constraint.txt pip install -r requirements.txt`
6. Do an initial run of AMM to generate a template configuration file: ``python3 manager.py -d``
7. Edit your configuration in ``settings.json``
   1. Add your desired opensearch configs and change them to ``active``
8. (optional) create an ``.env`` file to hold your credentials
   1. Format for .env is ```VARIABLE=content```, one entry per line
   2. Add the variables to settings.json
   3. AMM will find and use an .env file in your home folder if it can't find it in the project folder

# Usage
```
usage: manager.py [-h] [-s] [-r] [-V] [-d] [-f] [-i] [-a] [-as state] [-al severity] [-az size] [-v] [-p json/yaml] [-l [filter]]

Aiven Monitor Manager syncs OpenSearch monitors with a local repository. Manager can also be used to display information about local and remote monitors and alerts, and to validate monitors based on
customizable validators.

options:
  -h, --help            show this help message and exit
  -s, --sync            Scan and sync monitor changes
  -r, --run             Test run monitors, use with -l to run a limited subset. Running monitors does not trigger actions.
  -V, --verbose         Show more verbose output
  -d, --dryrun          Do not make any changes to local or remote monitors
  -f, -y, --force, --assume-yes
                        Do not require confirmation, assume yes to all
  -i, --info            Show information about monitors
  -a, --alerts          Show recent alerts
  -as state, --state state
                        Combine with -a, filter alerts by state (active, acknowledged, completer, error, deleted)
  -al severity, --severity severity
                        Combine with -a, filter alerts by severity level (info, low, medium, high, critical)
  -az size, --size size
                        Combine with -a, return a maximum of N alerts (1-10000)
  -v, --validate        validate monitors
  -p json/yaml, --print json/yaml
                        print monitors in JSON or YAML
  -l [filter], --filter [filter]
                        filter monitors by case-insensitive string match in monitor name
```

# Workflow
1) Clone repository or do a `git pull` on existing local copy of repository
2) Run ``manager.py --sync`` to sync monitors
3) Make changes to desired monitors
   1) Optionally run ``manager.py --sync --dryrun`` to do a dry-run of your changes
   2) Dry run will execute with confirmation dialogs, but will skip making any actual changes
4) Run `manager.py --sync` to sync changes.
   1) Optionally, run with `--force` to skip confirming or confirm with ``a``.
   in the dialog.
5) git add, commit and push changes back to monitor repository

## Syncing

``--sync``: AMM will track changes and version state and sync all monitors for all active instances.

``--dryrun``: Runs the sync without making any file changes to local or remote monitors

``--force``: Assume yes to all confirmation dialogs.

``--info``: Print a table of all monitors and display information on them

``--validate``: Run validators against monitors. Currently supports format validation for Slack, Opsgenie and Mustache

``--print``: Print monitor as a highlighted JSON or YAML. If local and remote monitors have differences,
print monitors side by side.

## Creating new monitors

A new monitor can be created using AMM. The easiest way to do this is by starting from an existing monitor. Copy the 
monitor folder with ``cp -r old-monitor new-monitor``, then change the following before making changes into monitor 
logic:

``_id``: Blank the id for the new monitor. AMM will generate a random temporary ID for the monitor for identification
purposes, which will be replaced with the created ID once the monitor is synced with OpenSearch

```monitor.name```: The monitor name is used to both give a human-friendly name for it and name it's directory under
the instance directory root directory. The monitor name should be short and must be unique. If you start by copying
`old-monitor`, change this to `new-monitor`. The automatic cleanup job will check that 
the monitor name matches it's folder. If it doesn't, the folder will be removed and a new folder created with the
monitor name, or the monitor will be deduplicated if an existing name is reused. If several monitors share the same 
name, they will end up overwriting each other.

OpenSearch will allow for duplicate monitor names, but AMM will not as it stores the monitors in folders that
are named in a human-friendly way.

## Configuration

AMM is configured using the settings.json file. If a settings.json is not present, AMM will
create a template configuration file on first run.

OpenSearch credentials are fetched from environmental variables. These variables can be stored in an `.env` file either
in project or user root where they will be read at runtime. The format is `VARIABLENAME=value`, one per line.

### Global settings

 - `"slack webhook": ""` 
   - Slack webhook for notifications. Notifications will not be sent if the
webhook is not configured. AMM currently supports only Slack for notifications. You can either
 configure a https endpoint directly or define an environmental variable that holds the https address.

### Instances

AMM supports an arbitrary amount of OpenSearch instances to be configured and managed centrally. Each instance has it's
own monitor directory under ``monitors`` which is used to store monitor JSON data.

```
  "instances": {
    "opensearch": [
      {
        "active": false,
        "name": "local-test",
        "url": "http://opensearch.kurittu.org:9200",
        "env_username": "LOCAL_OS_U",
        "env_password": "LOCAL_OS_P"
      },
```

 - `"active"`: ``true`` or ``false``
   - Defines whether the instance should be skipped or processed.
   

 - `"name"`: `alphanumeric string`
   - Short name  that is given to the instance in AMM. This also defines which directory the instance monitors are stored. 
Please use a path-safe name and do not use special characters that are not allowed in path names.


 - `"url"`: ``https://subdomain.domain.tld:port/``
   - Location of the OpenSearch instance. Please note that OpenSearch Dashboards, the user interface, has a different
address. 


 - `"env_username"`: ``VARIABLE``
 - `"env_password"`: ``VARIABLE``
   - Which environmental variable to read as username. AMM uses python-dotenv, allowing for storing credentials in an ``.env``
   file in either the project folder or your home root folder. This allows you to store credentials in a file where they
   will be imported from as environmental variables during runtime.

# Caveats

### Deleting monitors

Deleting monitors should require administrator rights, and should not be possible to do with regular user credentials.
The syncing process treats every monitor it can't find in either local or remote sources as a new monitor, and will
create it either remotely or locally.

To delete a monitor, delete it manually from OpenSearch using administrator credentials and then remove the 
corresponding directory from the instance directory.

### Partial support for document-level monitors

Some functionalities do not deal gracefully with document-level monitors and will fail. AMM has been extensively tested
with query-level monitors.

### Bootstrapping a new instance

AMM does not currently sync notification channels, which needs to be done manually when applying monitors to a fresh
OpenSearch instance.

