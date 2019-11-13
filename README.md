[![Documentation Status](https://readthedocs.org/projects/csp-lmc-prototype/badge/?version=latest)](https://developer.skatelescope.org/projects/csp-lmc-prototype/en/latest/?badge=latest)
[![coverage report](https://gitlab.com/ska-telescope/csp-lmc-prototype/badges/master/coverage.svg)](https://ska-telescope.gitlab.io/csp-lmc-prototype/)
[![pipeline status](https://gitlab.com/ska-telescope/csp-lmc-prototype/badges/master/pipeline.svg)](https://gitlab.com/ska-telescope/csp-lmc-prototype/pipelines)

## Table of contents
* [Description](#description)
* [Getting started](#getting-started)
* [Prerequisities](#prerequisities)
* [Run on local host](#how-to-run-on-local-host)
    * [Start the devices](#start-the-devices)
    * [Configure the devices](#configure-the-devices) 
* [Run in containers](#how-to-run-in-docker-containers)
* [Running tests](#running-tests)
* [Known bugs](#known-bugs)
* [Troubleshooting](#troubleshooting)
* [License](#license)

## Description

At the present time the `CSP.LMC` prototype implements two TANGO devices:

* the `CspMaster` device: based on the `SKA Base SKAMaster` class. The `CspMaster` represents a primary point of contact for CSP Monitor and Control.  
It implements CSP state and mode indicators and a limited set of housekeeping commands.
* the `CspSubarray` device: based on the `SKA Base SKASubarray` class, models a CSP subarray.

## Getting started

The project can be found in the SKA gitlab repository.

To get a local copy of the project:

```bash
git clone https://gitlab.com/ska-telescope/csp-lmc-prototype.git
```
## Prerequisities

* A TANGO development environment properly configured, as described in [SKA developer portal](https://developer.skatelescope.org/en/latest/tools/tango-devenv-setup.html)

* [SKA Base classes](https://gitlab.com/ska-telescope/lmc-base-classes)


## How to run on local host

### Start the devices

The script `start_prototype` in the project root directory starts the `CSP.LMC` TANGO Devices, 
doing some preliminary controls.


The script:

 * checks if the TANGO DB is up and running
 * configure the CSP.LMC devices properties,executing the python script [configureDevices.py](csplmc/configureDevices.py)
 * checks if the CSP.LMC prototype TANGO devices are already registered within the TANGO DB, otherwise it adds them
 * starts the CSP.LMC prototype devices (CspMaster and CspSubarray1).
 * starts the `jive` tool (if installed in the local system).
 
The `stop_prototype` script stops the execution of the `CSP.LMC` prototype TANGO Device servers.

In particular it:

* checks if the `CSP.LMC` prototype TANGO Servers are running
* gets the `pids` of the running servers
* send them the TERM signal

__NOTE__
> The `start_prototype` script starts *only* the CSP.LMC TANGO Devices. 
The [Mid CBF project](https://gitlab.com/ska-telescope/mid-cbf-mcs), provides a complete set of 
`Mid-CBF.LMC` devices that can be used to test the `CSP.LMC` monitor and control capabilities.
**However, the reccommended method to run the whole CSP.LMC prototype is via the use of Docker containers** (see below).

### Configure the devices

Once started, the devices need to be configured into the TANGO DB.
The `jive` tool can be used to set the `polling period` and `change events` for the `healthState` and `State` attributes of both devices.

For example, the procedure to configure the `CspSubarray1` device is as follow:

* start `jive`
* from the top of `jive` window select `Device`
* drill down into the list of devices
* select the device `mid_csp/elt/subarray_01`
* select `Polling` entry (left window) and select the `Attributes` tab (right window)
* select the check button in corrispondence of the `healthState` and `State` entries. The default polling period is set to 3000 ms, it can be changed to 1000.
* select `Events` entry (left window) and select the `Change event` tab (right window)
* set to 1 the `Absolute` entry for the `healthState` attribute

The same sequence of operations has to be repeated for all the provided devices otherwise no TANGO client is able to subscribe and receive `events` for that devices.

A dedicated script (based on the work done by the NCRA team) has been written to perform this procedure in automatic way (see [configureAttrProperties.py](csplmc/configureAttrProperties.py). 
Run this script *only* after the start of the CSP prototype devices. 

__NOTE__
> Both the [configureAttrProperties.py](csplmc/configureAttrProperties.py) and the [configureDevices.py](csplmc/configureDevices.py) scripts 
relies on the JSON file [devices.json](csplmc/devices.json) with the full description of the `CSP.LMC` and `Mid-CBF.LMC` TANGO Devices populating 
the `CSP TANGO DB`. <br/>
To add a new TANGO Device to the TANGO DB, a new entry for the device has to be added to this file. Also the `start_prototype` has to be updated to run the new device.

## How to run in Docker containers

The CSP.LMC prototype can run also in a containerised environment.
Currently only a limitated number of CSP.LMC and Mid-CBF.LMC devices are run in Docker containers:

* the CspMaster and CbfMaster
* two instances of the CSP and CBF subarrays
* four instances of the Very Coarse Channelizer (VCC) devices
* four instance of the Frequency Slice Processor (FPS) devices
* two instances of the TM TelState Simulator devices

The Mid-CBF.LMC containers are created pulling the `mid-cbf-mcs` project image from the [Nexus repository](https://nexus.engageska-portugal.pt). <br/>
The CSP.LMC projects provides a [Makefile](Makefile) to run automatically the system containers and the tests.<br/>
The CSP.LMC containerised environment relies on three YAML configuration files:

* `csplmc-tangodb.yml` 
* `csp-lmc.yml` 
* `mid-cbf-mcs.yml`

Each file includes the stages to run the the `CSP.LMC TANGO DB`, `CSP.LMC` and `Mid-CBF.LMC` TANGO Devices inside 
separate docker containers.<br/>
These YAML files are used by `docker-compose` to run both the CSP.LMC and CBF.LMC TANGO device
instances, that is, to run the whole `Csp.LMC` prototype. In this way, it's possible to execute
some preliminary integration tests, as for example the assignment/release of receptors to a `CSPSubarray` and its configuration to execute a scan in Imaging mode.

The `CSP.LMC` and `Mid-CBF.LMC TANGO` Devices are registered with the same TANGO DB, and its 
configuration is performed via the `dsconfig` TANGO Device provided by the [dsconfig project](https://gitlab.com/MaxIV-KitsControls/lib-maxiv-dsconfig). <br />
This device use a JSON file to configure the TANGO DB. <br/>
The `CSP.LMC` and `Mid-CBF.LMC` projects provide its own  JSON file:
[csplmc\_dsconfig.json](csplmc/data/csplmc_dsconfig.json) and [midcbf\_dsconfig.json](csplmc/data/midcbf_dsconfig.json)  

To run the `CSP.LMC` prototype inside Docker containers, 
issue the command:

```bash
make up
```
from the project root directory. At the end of the procedure the command

<pre><code>docker ps</code></pre>  
shows the list of the running containers:
```
csplmc-tangodb:            the MariaDB database with the TANGO database tables  
csplmc-databaseds:         the TANGO DB device server                          
csplmc-cbf_dsconfig:       the dsconfig container to configure CBF.LMC devices in the TANGO DB
csplmc-cbf_dsconfig:       the dsconfig container to configure CSP.LMC devices in the TANGO DB
csplmc-cspmaster:          the CspMaster TANGO device                          
csplmc-cspsubarray[01-02]: two instances of the CspSubarray TANGO device     
csplmc-cspsubarray02:      the instance 01 of the CspSubarray TANGO device     
csplmc-rsyslog-csplmc:     the rsyslog container for the CSP.LMC devices      
csplmc-rsyslog-cbf :       the rsyslog container for the CBF.LMC devices      
csplmc-cbfmaster:          the CbfMaster TANGO device                        
csplmc-cbfsubarray[01-02]: two instances of the CbfSubarray TANGO device  
csplmc-vcc[001-004]:       four instances of the Mid-CBF VCC TANGO device 
csplmc-fsp[01-04]:         four instances of the Mid-CBF FSP TANGO device      
csplmc-tmcspsubarrayleafnodetest/2: two instances of the TelState TANGO Device 
                           simulator provided by the CBF project to support scan
                           configuration for Subarray1/2
```                            

To stop and removes the Docker containers, issue the command

<pre><code>make down</code></pre>  
from the prototype root directory. 

__NOTE__
>Docker containers are run with the `--network=host` option.
In this case there is no isolation between the host machine and the containers. <br/>
This means that the TANGO DB running in the container is available on port 10000 of the host machine. <br />
Running `jive` on the local host, the `CSP.LMC` and `Mid-CBF.LMC` TANGO Devices registered with the TANGO DB (running in a docker container) 
can be visualized and explored.


## Running tests

The project includes a set of tests for the CspMaster and CspSubarray TANGO Devices that can be found respectively in the folders:

* `csplmc/CspMaster/test`
* `csplmc/CspSubarray/test`

To run the test on the local host issue the command

<code><pre>make test</pre></code>  
from the root project directory.
The test are run in docker containers providing the proper environment setup and isolation.

## Known bugs

*

## Troubleshooting

It may happens that the TANGO attributes configured for polling and/or events via the POGO tools, are not correclty configured when the TANGO Devices start. <br/>
Please check their configuration inside the TANGO DB (where the devices are registered) and 
follow the instructions [here](#configure-the-devices) to setup the `polling` and `change events` of the attribute. <br/>
This issue is generally resolved running the [configureAttrProperties.py](csplmc/configureAttrProperties.py) 
(when the `start_prototype` script is used) or the `dsconfig` container (when the system run in the containerised environment) 
but the configuration files these mechanisms rely on, have to include the necessary information about the properties of the 
attribute concerned.

## License 
See the LICENSE file for details.

