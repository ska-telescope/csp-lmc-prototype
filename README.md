[![Documentation Status](https://readthedocs.org/projects/csp-lmc-prototype/badge/?version=latest)](https://developer.skatelescope.org/projects/csp-lmc-prototype/en/latest/?badge=latest)
## Table of contents
* [Description](#description)
* [Getting started](#getting-started)
* [Prerequisities](#prerequisities)
* [Run on local host](#how-to-run-on-local-host)
* [Run in containers](#how-to-run-in-containers)
* [Running tests](#running-tests)
    * [Start the devices](#start-the-devices)
    * [Configure the devices](#configure-the-devices) 
* [Known bugs](#known-bugs)
* [Troubleshooting](#troubleshooting)

## Description

The `CSP.LMC` prototype implements at the moment two TANGO devices:

* the `CSPMaster` device: based on the SKA Base SKAMaster class, it represents a primary point of contact for CSP Monitor and Control.It implements CSP state and mode indicators and a limited set of housekeeping commands.
* the `CbfTestMaster` device: based on the SKA Base SKAMaster class, simulates the CBF Sub-element Master and it's used to test CSP Master basic functionalities.

## Getting started

The project can be found in the SKA github repository.

To get a local copy of the project:

```bash
git clone https://github.com/ska-telescope/csp-lmc-prototype.git
```

## Prerequisities

* A TANGO development environment properly configured as described in [SKA developer portal](https://developer.skatelescope.org/en/latest/tools/tango-devenv-setup.html)

* The SKA Base classes installed


## How to run on local host

### Start the devices

The script `start_prototype` in the project root directory starts the two TANGO devices, doing some preliminary controls.

The script:

 * checks if the TANGO DB is up and running
 * checks if the CSP.LMC prototype TANGO devices are already registered within the TANGO DB, otherwise it adds them
 * starts the CSP.LMC prototype devices in the proper order (CBF Sub-element master first).
 * starts the `jive` tool (if installed in the local system).
 
The `stop_prototype` script stops the execution of the CSP.LMC prototype TANGO Device servers.

In particular it:

* checks if the CSP.LMC prototype TANGO servers are running
* gets the `pids` of the running servers
* send them the TERM signal

### Configure the devices

Once started, the devices need to be configured into the TANGO DB.
The `jive` tool can be used to set the `polling period` and `change events` for the `healthState` and `State` attributes of both devices.

For example, the procedure to configure the `CbfTestMaster` device is as follow:

* start `jive`
* from the top of `jive` window select `Device`
* drill down into the list of devices
* select the device `mid_csp_cbf/sub_elt/master`
* select `Polling` entry (left window) and select the `Attributes` tab (right window)
* select the check button in corrispondence of the `healthState` and `State` entries. The default polling period is set to 3000 ms, it can be changed to 1000.
* select `Events` entry (left window) and select the `Change event` tab (right window)
* set to 1 the `Absolute` entry for the `healthState` attribute

The same sequence of operations has to be repeated for the CspMaster, otherwise no TANGO client is able to subscribe and receive `events` for that device.

A dedicated script (based on the work done by the NCRA team) has been written to perform this procedure in automatic way (see [configurePollingAndEvents.py](csplmc/configurePollingAndEvents.py). 
Run this script after the start of the CSP prototype devices.

## How to run in Docker containers

The CSP.LMC prototype can run also in a containerised environment: the YAML configuration file `docker-compose.yml` includes the stages to run the the CSP.LMC TANGO devices inside separate docker containers.

From the project root directory issue the command:

```bash
make up
```
At the end of the procedure the command

```bash
docker ps
```

shows the list of the running containers:

* csplmc-tangodb: the MariaDB database with the TANGO database tables
* csplmc-databaseds: the TANGO DB device server
* csplmc-cspmaster: the CspMaster TANGO device
* csplmc-cbftestmaster: the CbfTestMaster TANGO device
* csplmc-rsyslog-csplmc: the rsyslog container for the CSP.LMC devices

To stop the Docker containers, issue the command

```bash
make down
```

from the prototype root directory.

__NOTE__
 
>Docker containers are run with the `--network=host` option.
In this case there is no isolation between the host machine and the container. 
So, the TANGO DB running in the container is available on port 10000 of the host machine.
Running `jive` on the local host, the CSP.LMC prototype devices registered 
with the TANGO DB (running in a docker container) can be visualized and explored.


## Running tests

The project includes at the moment one test.
To run the test on the local host, from the `csplmc/CspMaster` directory issue the command

```bash
python setup.py test
```

To run the test into docker containers issue the command 

```bash
make test
```

from the root project directory.

## Troubleshooting

If the CSPMaster State and healthState attributes are not correctly updated, please check the configuration of the following attributes of the CspTestMaster device:
* State
* healthState

If a TANGO client does correctly update the CSPMaster device State and healthState, please check the configuration of the following attributes:

* State
* healthState
* cbfState
* cbfHealthState

Please follow the istruction in chapter(#configure) to setup the `polling` and `change events` of an attribute.

## Knonw bugs

### License 
See the LICENSE file for details.

