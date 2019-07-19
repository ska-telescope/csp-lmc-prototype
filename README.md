[![Documentation Status](https://readthedocs.org/projects/csp-lmc-prototype/badge/?version=latest)](https://developer.skatelescope.org/projects/csp-lmc-prototype/en/latest/?badge=latest)
<!--Required extensions: table-->
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

At the present time the `CSP.LMC` prototype implements two TANGO devices:

* the `CSPMaster` device: based on the `SKA Base SKAMaster` class, it represents a primary point of contact for CSP Monitor and Control.  
It implements CSP state and mode indicators and a limited set of housekeeping commands.
* the `CspSubarray` device: based on the `SKA Base SKASubarray` class, models a CSP subarray.

__NOTE__
>Support for `CbfTestMaster` has been removed from the docker environment because there is already in place the [Mid CBF project](https://github.com/ska-telescope/mid-cbf-mcs), providing a complete set of CBF.LMC devices.

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

The script `start_prototype` in the project root directory starts the CSP.LMC TANGO devices, doing some preliminary controls.

The script:

 * checks if the TANGO DB is up and running
 * configure the CSP.LMC devices properties
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

The same sequence of operations has to be repeated for the `CspMaster` and `CspSubarray` otherwise no TANGO client is able to subscribe and receive `events` for that device.

A dedicated script (based on the work done by the NCRA team) has been written to perform this procedure in automatic way (see [configureAttrProperties.py](csplmc/configureAttrProperties.py). 
Run this script after the start of the CSP prototype devices. 

## How to run in Docker containers

The CSP.LMC prototype can run also in a containerised environment.   
In this particular case, some containers run a small number of the Mid-CBF.LMC devices: the 
`CbfMaster`, one instance of the `CbfSubarray`, four instances of the Very Coarse Channelizer (VCC) devices and four instance of the Frequency Slice Processor (FPS) devices.  
In this environment it's possible to execute some preliminary integration tests, as for example 
the assignment/release of receptors to a `CSPSubarray`.   
The Mid-CBF.LMC containers are created pulling the `mid-cbf-mcs` project image from the nexus repository.  
The containerised environment relies on three YAML configuration files:
`csplmc-tangodb.yml`, `csp-lmc.yml` and `mid-cbf-mcs.yml`. Each file includes the stages 
to run the the CSP TANGO DB, CSP.LMC and Mid-CBF.LMC TANGO devices inside separate docker containers.
Makefile has been modified to run docker-compose with all these files.  
The configuration of the CSP.LMC TANGO DB is performed using the 
[dsconfig project](https://github.com/MaxIV-KitsControls/lib-maxiv-dsconfig). 
Configuration for CSP.LMC and Mid-CBF.LMC devices are in two separate files: 
[csplmc\_dsconfig.json](csplmc/data/csplmc_dsconfig.json) and [midcbf\_dsconfig.json](csplmc/data/midcbf_dsconfig.json)  
From the project root directory issue the command:

```bash
make up
```
At the end of the procedure the command

<pre><code>docker ps</code></pre>  
shows the list of the running containers:

|                          |                                                      |
| ------------------------ |: --------------------------------------------------- |
| `csplmc-tangodb`:        | the MariaDB database with the TANGO database tables  |
| `csplmc-databaseds`:     | the TANGO DB device server                           |
| `csplmc-cspmaster`:      | the CspMaster TANGO device                           |
| `csplmc-cspsubarray01`:  | the instance 01 of the CspSubarray TANGO device      |
| `csplmc-rsyslog-csplmc`: | the rsyslog container for the CSP.LMC devices        |
| `csplmc-cbfmaster`:      | the CbfMaster TANGO device                           |
| `csplmc-cbfsubarray01`:  | the instance 01 of the CbfSubarray TANGO device      |
| `csplmc-vcc[001-004]`:   | four instances of the Mid-CBF VCC TANGO devices      |
| `csplmc-fsp[01-04]`:     | four instances of the Mid-CBF FSP TANGO devices      |

To stop the Docker containers, issue the command

<pre><code>make down</code></pre>  
from the prototype root directory. The command stops and removes all the containers of the project.


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
<code><pre>make test</pre></code>  
from the root project directory.

## Troubleshooting

If the CSPMaster State and healthState attributes are not correctly updated, please check the configuration of the following attributes of the CbfMaster device:
* State
* healthState

If a TANGO client doesn't correctly update the CSPMaster device State and healthState, please check the configuration of the following attributes:

* State
* healthState
* cbfState
* cbfHealthState

Please follow the istruction in chapter(#configure) to setup the `polling` and `change events` of an attribute.

## Knonw bugs

### License 
See the LICENSE file for details.

