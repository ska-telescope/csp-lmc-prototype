##############
CSP Subarrays
##############
The core CSP functionality, configuration and execution of signal processing, is configured, controlled 
and monitored via subarrays.

CSP Subarray makes provision to TM to configure a subarray, select Processing Mode and related parameters, 
specify when to start/stop signal processing and/or generation of output products.  
TM accesses directly a CSP Subarray to:

* Assign resources 
* Configure a scan
* Control and monitor states/operations

Resources assignment
=====================
The assignment of Capabilities to a subarray (*subarray composition*) is performed 
in advance of a scan configuration.  
Assignable Capabilities for CSP Mid subarrays are:

* receptors and the associated CBF Very Coarse Channelizers:each VCC processes the input from one receptor.
* CBF Frequency Slice Processors performing one of the available Processing Mode Functions: Correlation, 
  Pulsar Timing Beamforming, Pulsar Search Beamforming, VLBI Beamforming.
* tied-array beams: Search Beams, Timing Beams and Vlbi Beams.

In general resource assignment to a subarray is exclusive, but in some cases (FSPs) the same Capability instance
may be used in shared manner by more then one subarray.

*Note: of all the listed Capabilities, only FSPs are assigned to subarrays via a scan configuration.*

Inherent Capabilities
---------------------
Each CSP subarray has also four permanently assigned *inherent Capabilities*: 

* Correlation
* PSS
* PST
* VLBI

An inherent Capability can be enabled or disabled, but cannot assigned or removed to/from a subarray. 
They correspond to the CSP Mid Processing Modes and are configured via a scan configuration.

Scan configuration
====================

TM provides a complete scan configuration to a subarray via an ASCII JSON encoded string.
Parameters specified via a JSON string are implemented as TANGO Device attributes  
and can be accessed and modified directly using the buil-in TANGO method *write_attribute*.
When a complete and coherent scan configuration is received and the subarray configuration 
(or re-configuration) completed,  the subarray it's ready to observe.

Control and Monitoring
======================
Each CSP Subarray maintains and report the status and state transitions for the 
CSP subarray as a whole and for the individual assigned resources.

In addition to pre-configured status reporting, a CSP Subarray makes provision for the TM and any authorized client, 
to obtain the value of any subarray attribute.

Class Documentation 
===============================
.. automodule:: CspSubarray
   :members:
   :undoc-members:

