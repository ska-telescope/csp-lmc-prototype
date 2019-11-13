# -*- coding: utf-8 -*-
#
# This file is part of the CspSubarray project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""
**CspSubarray TANGO Device Class**

CSP subarray functionality is modeled via a TANGO Device Class, named *CspSubarray*.
This class exports a set of attributes and methods required for configuration,
control and monitoring of the subarray.
"""
# PROTECTED REGION ID (CspSubarray.standardlibray_import) ENABLED START #
# Python standard library
# Python standard library
from __future__ import absolute_import
import sys
import os
from future.utils import with_metaclass
from collections import defaultdict
# PROTECTED REGION END# //CspMaster.standardlibray_import

# tango imports
import tango
from tango import DebugIt, EventType, DeviceProxy, AttrWriteType
from tango.server import run, DeviceMeta, attribute, command, device_property, class_property

# PROTECTED REGION ID (CspSubarray.add_path) ENABLED START #
# add the path to import global_enum package.
file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)
# PROTECTED REGION END# //CspSubarray.add_path

# Additional import
# PROTECTED REGION ID(CspMaster.additionnal_import) ENABLED START #
#
#import global_enum as const
from global_enum import HealthState, AdminMode, ObsState, ObsMode
from skabase.SKASubarray import SKASubarray
import json
# PROTECTED REGION END #    //  CspMaster.additionnal_import

__all__ = ["CspSubarray", "main"]

class CspSubarray(with_metaclass(DeviceMeta, SKASubarray)):
    """
    CSP subarray functionality is modeled via a TANGO Device Class, named *CspSubarray*.
    This class exports a set of attributes and methods required for configuration,
    control and monitoring of the subarray.
    """
    # PROTECTED REGION ID(CspSubarray.class_variable) ENABLED START #

    # ---------------
    # Event Callback functions
    # ---------------
    def __cmd_ended(self, evt):
        """
        Method immediately executed when the asynchronous invoked
        command returns.

        Args:
            evt: A CmdDoneEvent object. This class is used to pass data
            to the callback method in asynchronous callback model for command
            execution.

            It has the following members:
                - device     : (DeviceProxy) The DeviceProxy object on which the
                               call was executed.
                - cmd_name   : (str) The command name
                - argout_raw : (DeviceData) The command argout
                - argout     : The command argout
                - err        : (bool) A boolean flag set to true if the command
                               failed. False otherwise
                - errors     : (sequence<DevError>) The error stack
                - ext
        Returns:
            None
        """
        # NOTE:if we try to access to evt.cmd_name or other paramters, sometime
        # the callback crashes withthis error:
        # terminate called after throwing an instance of 'boost::python::error_already_set'
        #
        try:
            # Can happen evt empty??
            if evt:
                if not evt.err:
                    msg = "Device {} is processing command {}".format(evt.device,
                                                                      evt.cmd_name)
                    # TODO:
                    # update the valid_scan_configuration attribute. If the command
                    # is running the configuration has been validated
                    # if cmd == "ConfigureScan":
                    # .......
                    self.dev_logging(msg, tango.LogLevel.LOG_INFO)
                else:
                    msg = "Error in executing command {} ended on device {}.\n".format(evt.cmd_name,
                                                                                       evt.device)
                    msg += " Desc: {}".format(evt.errors[0].desc)
                    self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
                    # obsState and obsMode values take on the CbfSubarray's values via
                    # the subscribe/publish mechanism
            else:
                self.dev_logging("cmd_ended callback: evt is empty!!",
                                 tango.LogLevel.LOG_ERRO)
        except tango.DevFailed as df:
            msg = ("CommandCallback cmd_ended failure - desc: {}"
                   " reason: {}".format(df.args[0].desc, df.args[0].reason))
            self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
        except Exception as ex:
            msg = "CommandCallBack cmd_ended general exception: {}".format(str(ex))
            self.dev_logging(msg, tango.LogLevel.LOG_ERROR)

    def __scm_change_callback(self, evt):
        """
        *Class private method.*

        Retrieve the values of the sub-element sub-arrays SCM attributes subscribed
        for change event at device initialization.

        Args:
            evt: The event data

        Returns:
            None
        """
        try:
            dev_name = evt.device.dev_name()
            if not evt.err:
                # control if the device name is in the list of the
                # subarray fqdn and that is found in the attribute's FQDN
                if (dev_name in self._se_subarrays_fqdn and evt.attr_name.find(dev_name) > 0):
                    if evt.attr_value.name.lower() == "healthstate":
                        self._se_subarray_healthstate[dev_name] = evt.attr_value.value
                    elif evt.attr_value.name.lower() == "state":
                        self._se_subarray_state[dev_name] = evt.attr_value.value
                    elif evt.attr_value.name.lower() == "adminmode":
                        self._se_subarray_adminmode[dev_name] = evt.attr_value.value
                    elif evt.attr_value.name.lower() == "obsstate":
                        # look for transition from SCANNING to READY/IDLE before
                        # storing the new value into the attribute
                        if self._se_subarray_obsstate[dev_name] == ObsState.SCANNING:
                            if evt.attr_value.value in [ObsState.READY, ObsState.IDLE]:
                                self.dev_logging("Scan ended on subarray {}".format(dev_name),
                                                 tango.LogLevel.LOG_INFO)
                        self._se_subarray_obsstate[dev_name] = evt.attr_value.value
                    else:
                        self.dev_logging(("Attribute {} not yet handled".format(evt.attr_name)),
                                         tango.LogLevel.LOG_ERR)
                else:
                    log_msg = ("Unexpected change event for"
                               " attribute: {}".format(str(evt.attr_name)))
                    self.dev_logging(log_msg, tango.LogLevel.LOG_WARN)
                    return
                # update the SCM values for the CSP subarray
                if evt.attr_value.name.lower() in ["state", "healthstate"]:
                    self.__set_subarray_state()
                if evt.attr_value.name.lower() == "obsstate":
                    self.__set_subarray_obs_state()
            else:
                for item in evt.errors:
                    # TODO:handle API_EventTimeout
                    log_msg = "{}: on attribute {}".format(item.reason, str(evt.attr_name))
                    self.dev_logging(log_msg, tango.LogLevel.LOG_WARN)
                    # NOTE: received when a command execution takes more than 3 sec.
                    # (TANGO TIMEOUT default value)
                    if item.reason == "API_CommandTimeout":
                        self.dev_logging(("Command Timeout out"), tango.LogLevel.LOG_WARN)
        except tango.DevFailed as df:
            self.dev_logging(str(df.args[0].desc), tango.LogLevel.LOG_ERR)

    #
    # Class private methods
    #
    def __connect_to_subarrays(self):
        """
        *Class private method.*

        Establish connection with each sub-element subarray.
        If connection succeeds, the CspSubarray device subscribes the State, healthState
        and adminMode attributes of each Sub-element subarray and registers a callback function
        to handle the events. Exceptions are logged.

        Returns:
            None
        Raises:
            tango.DevFailed: raises an exception if connection with a sub-element
            subarray fails
        """

        subarrays_fqdn = []
        subarrays_fqdn.append(self._cbf_subarray_fqdn)
        subarrays_fqdn.append(self._pss_subarray_fqdn)
        subarrays_fqdn.append(self._pst_subarray_fqdn)
        for fqdn in subarrays_fqdn:
            # initialize the list for each dictionary key-name
            self._se_subarray_event_id[fqdn] = []
            try:
                log_msg = "Trying connection to {} device".format(str(fqdn))
                self.dev_logging(log_msg, int(tango.LogLevel.LOG_INFO))
                device_proxy = DeviceProxy(fqdn)
                device_proxy.ping()
                # add to the FQDN subarray list, only the subarrays
                # available in the TANGO DB
                self._se_subarrays_fqdn.append(fqdn)
                # store the Sub-elements subarray proxies
                self._se_subarrays_proxies[fqdn] = device_proxy

                # Subscription of the Sub-element subarray SCM states
                ev_id = device_proxy.subscribe_event("State",
                                                     EventType.CHANGE_EVENT,
                                                     self.__scm_change_callback,
                                                     stateless=True)
                self._se_subarray_event_id[fqdn].append(ev_id)

                ev_id = device_proxy.subscribe_event("healthState",
                                                     EventType.CHANGE_EVENT,
                                                     self.__scm_change_callback,
                                                     stateless=True)
                self._se_subarray_event_id[fqdn].append(ev_id)

                ev_id = device_proxy.subscribe_event("obsState",
                                                     EventType.CHANGE_EVENT,
                                                     self.__scm_change_callback,
                                                     stateless=True)
                self._se_subarray_event_id[fqdn].append(ev_id)

                ev_id = device_proxy.subscribe_event("adminMode",
                                                     EventType.CHANGE_EVENT,
                                                     self.__scm_change_callback,
                                                     stateless=True)
                self._se_subarray_event_id[fqdn].append(ev_id)
            except tango.DevFailed as df:
                for item in df.args:
                    if "DB_DeviceNotDefined" in item.reason:
                        log_msg = ("Failure in connection to {}"
                                   " device: {}".format(str(fqdn), str(item.reason)))
                        self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
                tango.Except.throw_exception(df.args[0].reason,
                                             "Connection to {} failed".format(fqdn),
                                             "Connect to subarrays",
                                             tango.ErrSeverity.ERR)

    def __connect_to_master(self):
        """
        *Class private method.*

        Establish connection with the CSP Master and Sub-element Master devices to
        get information about:

        * the CBF/PSS/PST Master address

        * the max number of CBF capabilities for each supported capability type

        Returns:
            None
        Raises:
            DevFailed: when connections to the CspMaster and sub-element Master devices fail.
        """
        try:
            self.dev_logging("Trying connection to {}".format(self.CspMaster),
                             tango.LogLevel.LOG_INFO)
            cspMasterProxy = tango.DeviceProxy(self.CspMaster)
            cspMasterProxy.ping()
            # get the list of CSP capabilities to recover the max number of
            # capabilities for each type
            self._csp_capabilities = cspMasterProxy.maxCapabilities
            # try connection to CbfMaster to get information about the number of
            # capabilities and the receptor/vcc mapping
            if cspMasterProxy.cbfAdminMode in [AdminMode.ONLINE, AdminMode.MAINTENANCE]:
                self._cbfAddress = cspMasterProxy.cbfMasterAddress
                self._cbfMasterProxy = tango.DeviceProxy(self._cbfAddress)
                self._cbfMasterProxy.ping()
                cbf_capabilities = self._cbfMasterProxy.maxCapabilities
                # build the list of receptor ids
                receptor_to_vcc = self._cbfMasterProxy.receptorToVcc
                self._receptor_to_vcc_map = dict([int(ID) for ID in pair.split(":")]
                                                 for pair in receptor_to_vcc)
                # build the list of the installed receptors
                self._receptor_id_list = list(self._receptor_to_vcc_map.keys())
                for i in range(len(cbf_capabilities)):
                    cap_type, cap_num = cbf_capabilities[i].split(':')
                    self._cbf_capabilities[cap_type] = int(cap_num)

            # try connection to PssMaster
            # Do we need to connect to PssMaster?
            # All SearchBeams information should be available via the CspMaster
            if cspMasterProxy.pssAdminMode in [AdminMode.ONLINE, AdminMode.MAINTENANCE]:
                self._pssAddress = cspMasterProxy.pssMasterAddress
                self._pssMasterProxy = tango.DeviceProxy(self._pssAddress)
                self._pssMasterProxy.ping()
                #TODO: retrieve information about the available SearchBeams

            # try connection to PstMaster
            # Do we need to connect to PstMaster?
            # All TimingBeams information should be available via the CspMaster
            if cspMasterProxy.pstAdminMode in [AdminMode.ONLINE, AdminMode.MAINTENANCE]:
                self._pstAddress = cspMasterProxy.pstMasterAddress
                self._pstMasterProxy = tango.DeviceProxy(self._pstAddress)
                self._pstMasterProxy.ping()
                #TODO: retrieve information about the available TimingBeams
        except AttributeError as attr_err:
            msg = "Attribute error: {}".format(str(attr_err))
            self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
        except tango.DevFailed as df:
            tango.Except.throw_exception("Connection Failed",
                                         df.args[0].desc,
                                         "connect_to_master",
                                         tango.ErrSeverity.ERR)

    def __is_subarray_available(self, subarray_name):
        """
        *Class private method.*

        Check if the sub-element subarray is exported in the TANGO DB.
        If the subarray device is not present in the list of the connected
        subarrays, the connection with the0 device is performed.

        Args:
            subarray_name : the FQDN of the subarray
        Returns:
            True if the connection with the subarray is established, False otherwise
        """
        try:
            proxy = self._se_subarrays_proxies[subarray_name]
            proxy.ping()
        except KeyError:
            # Raised when a mapping (dictionary) key is not found in the set
            # of existing keys.
            # no proxy registered for the subarray device
            proxy = tango.DeviceProxy(subarray_name)
            proxy.ping()
            self._se_subarrays_proxies[subarray_name] = proxy
        except tango.DevFailed:
            return False
        return True

    def __set_subarray_state(self):
        """
        *Class private method*

        Set the subarray State and healthState.
        Args:
            None
        Returns:
            None
        """
        self.set_state(self._se_subarray_state[self._cbf_subarray_fqdn])
        self._health_state = HealthState.DEGRADED
        if ((self._se_subarray_healthstate[self._cbf_subarray_fqdn] == HealthState.FAILED) or \
            (self._se_subarray_state[self._cbf_subarray_fqdn] == tango.DevState.FAULT)):
            self._health_state = HealthState.FAILED
            self.set_state(tango.DevState.FAULT)
        if len(self._se_subarray_healthstate) == 3 and \
                list(self._se_subarray_healthstate.values()) == [HealthState.OK,
                                                                 HealthState.OK,
                                                                 HealthState.OK]:
            self._health_state = HealthState.OK
    def __set_subarray_obs_state(self):
        """
        *Class private method*

        Set the subarray obsState attribute value. It works only for IMAGING.
        Args:
            None
        Returns:
            None
        """
        # NOTE: when ObsMode value is set, it should be considered to set the final
        # sub-array ObsState value
        cbf_sub_obstate = self._se_subarray_obsstate[self._cbf_subarray_fqdn]
        pss_sub_obstate = self._se_subarray_obsstate[self._pss_subarray_fqdn]
        pst_sub_obstate = self._se_subarray_obsstate[self._pst_subarray_fqdn]
        # Next lines are valid only for IMAGING mode!!
        self._obs_state = cbf_sub_obstate
        if cbf_sub_obstate == ObsState.IDLE:
            self._obs_mode = ObsMode.IDLE
        # TODO:ObsMode could be defined as a mask because we can have more
        # than one obs_mode active for a sub-array

    def __is_remove_resources_allowed(self):
        """
        **Class private method **
        *TANGO is_allowed method*: filter the external request depending on the \
        current device state.\n
        Check if the method to release the allocated resources can be issued\n
        Resources can be removed from a subarray when its *State* is ON or OFF-

        Returns:
            True if the command can be executed, otherwise False
        """

        if self.get_state() in [tango.DevState.ON, tango.DevState.OFF]:
            return True
        return False

    def __is_add_resources_allowed(self):
        """
        **Class private method **
        *TANGO is_allowed method*: filter the external request depending on the \
        current device state.\n
        Check if the method to add resources to a subarraycan be issued\n
        Resources can be assigned to a subarray when its *State* is OFF or ON-

        Returns:
            True if the command can be executed, otherwise False
        """

        if self.get_state() in [tango.DevState.ON, tango.DevState.OFF]:
            return True
        return False

    # PROTECTED REGION END #    //  CspSubarray.class_variable

    # -----------------
    # Class Properties
    # -----------------

    CbfSubarrayPrefix = class_property(
        dtype='str', default_value="mid_csp_cbf/sub_elt/subarray_"
    )
    """
    *Class property*

    The CBF sub-element subarray FQDN prefix.

    *Type*: DevString

    Example:
        *mid_csp_cbf/sub_elt/subarray_*
    """

    PssSubarrayPrefix = class_property(
        dtype='str', default_value="mid_csp_pss/sub_elt/subarray_"
    )
    """
    *Class property*

    The PSS sub-element subarray FQDN prefix.

    *Type*: DevString

    Example:
        *mid_csp_pss/sub_elt/subarray_*
    """

    PstSubarrayPrefix = class_property(
        dtype='str', default_value="mid_csp_pst/sub_elt/subarray_"
    )
    """
    *Class property*

    The PST sub-element subarray FQDN prefix.

    *Type*: DevString

    Example:
        *mid_csp_pst/sub_elt/subarray_*
    """

    # -----------------
    # Device Properties
    # -----------------

    CspMaster = device_property(
        dtype='str', default_value="mid_csp/elt/master"
    )
    """
    *Device property*

    The CspMaster FQDN.

    *Type*: DevString
    """

    # ----------
    # Attributes
    # ----------

    scanID = attribute(
        dtype='uint64',
        access=AttrWriteType.READ_WRITE,
    )
    """
    *Class attribute*

    The identification number of the scan.

    *Type*: DevULong64
    """

    corrInherentCap = attribute(
        dtype='str',
    )
    """
    *Class attribute*

    The CspSubarray Correlation inherent Capability FQDN.

    *Type*: DevString\n
    """

    pssInherentCap = attribute(
        dtype='str',
    )
    """
    *Class attribute*

    The CspSubarray Pss inherent Capability FQDN.

    *Type*: DevString
    """

    pstInherentCap = attribute(
        dtype='str',
    )
    """
    *Class attribute*

    The CspSubarray Pst inherent Capability FQDN.

    *Type*: DevString
    """

    vlbiInherentCap = attribute(
        dtype='str',
    )
    """
    *Class attribute*

    The CspSubarray Vlbi inherent Capability FQDN.

    *Type*: DevString
    """

    cbfSubarrayState = attribute(
        dtype='DevState',
    )
    """
    *Class attribute*

    The CBF sub-element subarray State attribute value.

    *Type*: DevState
    """

    pssSubarrayState = attribute(
        dtype='DevState',
    )
    """
    *Class attribute*

    The PSS sub-element subarray State attribute value.

    *Type*: DevState
    """

    cbfSubarrayHealthState = attribute(
        dtype='DevEnum',
        label="CBF Subarray Health State",
        doc="CBF Subarray Health State",
        enum_labels=["OK", "DEGRADED", "FAILED", "UNKNOWN", ],
    )
    """
    *Class attribute*

    The CBF sub-element subarray healthState attribute value.

    *Type*: DevEnum

    *enum_labels*: ["OK", "DEGRADED", "FAILED", "UNKNOWN", ]
    """

    pssSubarrayHealthState = attribute(
        dtype='DevEnum',
        label="PSS Subarray Health State",
        doc="PSS Subarray Health State",
        enum_labels=["OK", "DEGRADED", "FAILED", "UNKNOWN", ],
    )
    """
    *Class attribute*

    The PSS sub-element subarray healthState attribute value.

    *Type*: DevEnum

    *enum_labels*: ["OK", "DEGRADED", "FAILED", "UNKNOWN", ]
    """

    cbfSubarrayObsState = attribute(
        dtype='DevEnum',
        label="CBF Subarray Observing State",
        doc="The CBF subarray observing state.",
        enum_labels=["IDLE", "CONFIGURING", "READY", "SCANNING", "PAUSED", "ABORTED", "FAULT", ],
    )
    """
    *Class attribute*

    The CBF sub-element subarray obsState attribute value.

    *Type*: DevEnum

    *enum_labels*: ["IDLE", "CONFIGURING", "READY", "SCANNING", "PAUSED", "ABORTED", "FAULT", ]
    """

    pssSubarrayObsState = attribute(
        dtype='DevEnum',
        label="PSS Subarray Observing State",
        doc="The PSS subarray observing state.",
        enum_labels=["IDLE", "CONFIGURING", "READY", "SCANNING", "PAUSED", "ABORTED", "FAULT", ],
    )
    """
    *Class attribute*

    The PSS sub-element subarray obsState attribute value.

    *Type*: DevEnum

    *enum_labels*: ["IDLE", "CONFIGURING", "READY", "SCANNING", "PAUSED", "ABORTED", "FAULT", ]
    """

    pssSubarrayAddr = attribute(
        dtype='str',
        doc="The PSS Subarray TANGO address.",
    )
    """
    *Class attribute*

    The PSS sub-element subarray FQDN.

    *Type*: DevString
    """

    cbfSubarrayAddr = attribute(
        dtype='str',
        doc="The CBF Subarray TANGO address.",
    )
    """
    *Class attribute*

    The CBF sub-element subarray FQDN.

    *Type*: DevString
    """

    validScanConfiguration = attribute(
        dtype='str',
        label="Valid Scan Configuration",
        doc="Store the last valid scan configuration.",
    )
    """
    *Class attribute*

    The last valid scan configuration JSON-encoded string.

    *Type*: DevString
    """

    fsp = attribute(
        dtype=('uint16',),
        max_dim_x=27,
    )
    """
    *Class attribute*

    The list of receptor IDs assigned to the subarray.

    *Type*: array of DevUShort
    """

    vcc = attribute(
        dtype=('uint16',),
        max_dim_x=197,
    )
    """
    *Class attribute*

    The list of VCC IDs assigned to the subarray.

    *Type*: array of DevUShort
    """

    searchBeams = attribute(
        dtype=('uint16',),
        max_dim_x=1500,
        )
    """
    *Class attribute*

    The list of Search Beam Capability IDs assigned to the subarray.

    *Type*: array of DevUShort
    """

    timingBeams = attribute(
        dtype=('uint16',),
        max_dim_x=16,
    )
    """
    *Class attribute*

    The list of Timing Beam Capability IDs assigned to the subarray.

    *Type*: array of DevUShort
    """

    vlbiBeams = attribute(
        dtype=('uint16',),
        max_dim_x=20,
    )
    """
    *Class attribute*

    The list of Vlbi Beam Capability IDs assigned to the subarray.

    *Type*: array of DevUShort
    """

    searchBeamsState = attribute(
        dtype=('DevState',),
        max_dim_x=1500,
    )
    """
    *Class attribute*

    The *State* attribue value of the Search Beam Capabilities assigned to the subarray.

    *Type*: array of DevState
    """

    timingBeamsState = attribute(
        dtype=('DevState',),
        max_dim_x=16,
    )
    """
    *Class attribute*

    The *State* attribue value of the Timing Beam Capabilities assigned to the subarray.

    *Type*: array of DevState
    """

    vlbiBeamsState = attribute(
        dtype=('DevState',),
        max_dim_x=20,
    )
    """
    *Class attribute*

    The *State* attribue value of the Vlbi Beam Capabilities assigned to the subarray.

    *Type*: array of DevState
    """

    searchBeamsHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=1500,
        doc="The healthState ttribute value of the Search Beams Capbilities \
             assigned to the subarray.",
    )
    """
    *Class attribute*

    The *healthState* attribute value of the Search Beams Capbilities assigned to the subarray.

    *Type*: array of DevUShort.

    References:
        See *Common definition* paragraph for corrispondences among Ushort values and label
    """

    timingBeamsHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=16,
    )
    """
    *Class attribute*

    The *healthState* attribute value of the Timing Beams Capbilities assigned to the subarray.

    *Type*: array of DevUShort.

    References:
        See *Common definition* paragraph for corrispondences among Ushort values and label
    """

    vlbiBeamsHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=20,
    )
    """
    *Class attribute*

    The *healthState* attribute value of the Vlbi Beams Capbilities assigned to the subarray.

    *Type*: array of DevUShort.

    References:
        See *Common definition* paragraph for corrispondences among Ushort values \
        and healthState labels.

    """

    timingBeamsObsState = attribute(
        dtype=('uint16',),
        max_dim_x=16,
        label="Timing Beams obsState",
        doc="The observation state of assigned timing beams.",
    )
    """
    *Class attribute*

    The *obsState* attribute  value of the Timing Beams Capbilities assigned to the subarray.

    *Type*: array of DevUShort.

    References:
        See *Common definition* paragraph for corrispondences among Ushort values \
        and obsState labels.
    """

    receptors = attribute(name="receptors", label="receptors", forwarded=True)
    """
    The list of receptors assigned to the subarray.

    *Forwarded attribute*

    *_root_att*: mid_csp_cbf/sub_elt/subarray_N/receptors
    """

    vccState = attribute(name="vccState", label="vccState", forwarded=True)
    """
    The State attribute value of the VCCs assigned to the subarray.

    *Forwarded attribute*

    *_root_att*: mid_csp_cbf/sub_elt/subarray_N/reportVCCState
    """

    vccHealthState = attribute(name="vccHealthState", label="vccHealthState", forwarded=True)
    """
    The healthState attribute value of the VCCs assigned to the subarray.

    *Forwarded attribute*

    *_root_att*: mid_csp_cbf/sub_elt/subarray_N/reportVCChealthState
    """
    cbfOutputLink = attribute(name="cbfOutputLink", label="cbfOutputLink", forwarded=True)
    """
    The CBF Subarray output links information.

    *Forwarded attribute*

    *_root_att*: mid_csp_cbf/sub_elt/subarray_N/cbfOutputLinksDistribution
    """

    #
    # These attributes are not defined in CbfMaster.
    #fspState = attribute(name="fspState", label="fspState",
    #    forwarded=True
    #)
    #fspHealthState = attribute(name="fspHealthState",label="fspHealthState",
    #    forwarded=True
    #)

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        """
        *Class method*

        Perform device initialization.
        during initiazlization the CspSubarray device :
        * connects to CSP Master and sub-element master devices

        * sub-element sub-array devices with the same subarray ID

        * subscribes to the sub-element subarrays  State,healthState, obsState attributes\
        for change event

        """

        SKASubarray.init_device(self)
        # PROTECTED REGION ID(CspSubarray.init_device) ENABLED START #
        self.set_state(tango.DevState.INIT)
        self._health_state = HealthState.UNKNOWN
        self._admin_mode   = AdminMode.OFFLINE
        # NOTE: need to adjust SKAObsDevice class because some of its
        # attributes (such as obs_state, obs_mode and command_progress) are not
        # visibile from the derived classes!!
        self._obs_mode  = ObsMode.IDLE
        self._obs_state = ObsState.IDLE
        # get subarray ID
        if self.SubID:
            self._subarray_id = int(self.SubID)
        else:
            self._subarray_id = int(self.get_name()[-2:])  # last two chars of FQDN
        # sub-element Subarray State and healthState initialization
        self._se_subarray_state         = defaultdict(lambda: tango.DevState.UNKNOWN)
        self._se_subarray_healthstate   = defaultdict(lambda: HealthState.UNKNOWN)
        self._se_subarray_obsstate      = defaultdict(lambda: ObsState.IDLE)
        self._se_subarray_adminmode     = defaultdict(lambda: AdminMode.OFFLINE)
        # initialize the list with the capabilities belonging to the sub-array
        # Do we need to know the max number of capabilities for each type?
        self._search_beams = []     # list of SearchBeams assigned to subarray
        self._timing_beams = []     # list of TimingBeams assigned to subarray
        self._vlbi_beams = []       # list of VlbiBeams assigned to subarray
        self._vcc = []              # list of VCCs assigned to subarray
        self._fsp = []              # list of FSPs assigned to subarray`

        self._cbf_subarray_fqdn = ''
        self._pss_subarray_fqdn = ''

        self._se_subarrays_fqdn = []
        self._se_subarrays_proxies = {}
        self._se_subarray_event_id = {}
        self._receptor_to_vcc_map = {}
        self._csp_capabilities = ''
        self._valid_scan_configuration = ''
        # initialize proxy to CBFMaster device
        self._cbfMasterProxy = 0
        self._cbfAddress = ''
        self._cbf_capabilities = {}
        # initialize proxy to PssMaster device
        self._pssMasterProxy = 0
        self._pssAddress = ''
        # initialize proxy to PstMaster device
        self._pstMasterProxy = 0
        self._pstAddress = ''
        # set storage and element logging level
        self._storage_logging_level = int(tango.LogLevel.LOG_INFO)
        self._element_logging_level = int(tango.LogLevel.LOG_INFO)
        # build the sub-element sub-array FQDNs
        self._cbf_subarray_fqdn = '{}{:02d}'.format(self.CbfSubarrayPrefix, self._subarray_id)
        self._pss_subarray_fqdn = '{}{:02d}'.format(self.PssSubarrayPrefix, self._subarray_id)
        self._pst_subarray_fqdn = '{}{:02d}'.format(self.PstSubarrayPrefix, self._subarray_id)
        try:
            self.__connect_to_master()
            self.__connect_to_subarrays()
        except tango.DevFailed as df:
            log_msg = "Error in {}: {}". format(df.args[0].origin, df.args[0].desc)
            self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)

        # to use the push model in command_inout_asynch (the one with the callback parameter),
        # change the global TANGO model to PUSH_CALLBACK.
        apiutil = tango.ApiUtil.instance()
        apiutil.set_asynch_cb_sub_model(tango.cb_sub_model.PUSH_CALLBACK)
        # PROTECTED REGION END #    //  CspSubarray.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(CspSubarray.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CspSubarray.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(CspSubarray.delete_device) ENABLED START #

        #release the allocated event resources
        for fqdn in self._se_subarrays_fqdn:
            event_to_remove = []
            try:
                for event_id in self._se_subarray_event_id[fqdn]:
                    try:
                        self._se_subarrays_proxies[fqdn].unsubscribe_event(event_id)
                        # self._se_subarray_event_id[fqdn].remove(event_id)
                        # in Pyton3 can't remove the element from the list while looping on it.
                        # Store the unsubscribed events in a temporary list and remove them later.
                        event_to_remove.append(event_id)
                    except tango.DevFailed as df:
                        msg = ("Unsubscribe event failure.Reason: {}. "
                               "Desc: {}".format(df.args[0].reason, df.args[0].desc))
                        self.dev_logging(msg, tango.LogLevl.LOG_ERROR)
                    except KeyError as key_err:
                        # NOTE: in PyTango unsubscription of a not-existing event id raises a
                        # KeyError exception not a DevFailed!!
                        msg = "Unsubscribe event failure. Reason: {}".format(str(key_err))
                        self.dev_logging(msg, tango.LogLevl.LOG_ERROR)
                # remove the events from the list
                for k in event_to_remove:
                    self._se_subarray_event_id[fqdn].remove(k)
                # check if there are still some registered events. What to do in this case??
                if self._se_subarray_event_id[fqdn]:
                    msg = "Still subscribed events: {}".format(self._se_subarray_event_id)
                    self.dev_logging(msg, tango.LogLevel.LOG_WARN)
                else:
                    # delete the dictionary entry
                    self._se_subarray_event_id.pop(fqdn)
            except KeyError as key_err:
                msg = " Can't retrieve the information of key {}".format(key_err)
                self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
        # clear the subarrays list and dictionary
        self._se_subarrays_fqdn.clear()
        self._se_subarrays_proxies.clear()

        # PROTECTED REGION END #    //  CspSubarray.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_scanID(self):
        """
        *Attribute method*

        Returns:
            The scan configuration ID.
        """
        # PROTECTED REGION ID(CspSubarray.scanID_read) ENABLED START #
        return self._scan_ID
        # PROTECTED REGION END #    //  CspSubarray.scanID_read

    def write_scanID(self, value):
        """
        Note:
            Not yet implemented.

        *Attribute method*

        Set the scan configuration ID to the defined value.

        Args:
            value: the scan configuration ID
            Type: DevUshort
        Returns:
            The scan configuration ID.
        """
        # PROTECTED REGION ID(CspSubarray.scanID_write) ENABLED START #
        return
        # PROTECTED REGION END #    //  CspSubarray.scanID_write

    def read_corrInherentCap(self):
        """
        *Attribute method*

        Returns:
            The CspSubarray Correlation Inherent Capability FQDN.

            *Type*: DevString
        """
        # PROTECTED REGION ID(CspSubarray.corrInherentCap_read) ENABLED START #
        return ''
        # PROTECTED REGION END #    //  CspSubarray.corrInherentCap_read

    def read_pssInherentCap(self):
        """
        *Attribute method*

        Returns:
            The CspSubarray PSS Inherent Capability FQDN.

            *Type*: DevString
        """
        # PROTECTED REGION ID(CspSubarray.pssInherentCap_read) ENABLED START #
        return ''
        # PROTECTED REGION END #    //  CspSubarray.pssInherentCap_read

    def read_pstInherentCap(self):
        """
        *Attribute method*

        Returns:
            The CspSubarray PST Inherent Capability FQDN.

            *Type*: DevString
        """
        # PROTECTED REGION ID(CspSubarray.pstInherentCap_read) ENABLED START #
        return ''
        # PROTECTED REGION END #    //  CspSubarray.pstInherentCap_read

    def read_vlbiInherentCap(self):
        """
        *Attribute method*

        Returns:
            The CspSubarray VLBI Inherent Capability FQDN.

            *Type*: DevString
        """
        # PROTECTED REGION ID(CspSubarray.vlbiInherentCap_read) ENABLED START #
        return ''
        # PROTECTED REGION END #    //  CspSubarray.vlbiInherentCap_read

    def read_cbfSubarrayState(self):
        """
        *Attribute method*

        Returns:
            The CBF sub-element subarray *State* attribute value.

            *Type*: DevState
        """
        # PROTECTED REGION ID(CspSubarray.cbfSubarrayState_read) ENABLED START #
        return self._cbf_subarray_state
        # PROTECTED REGION END #    //  CspSubarray.cbfSubarrayState_read

    def read_pssSubarrayState(self):
        """
        *Attribute method*

        Returns:
            The PSS sub-element subarray *State* attribute value.

            *Type*: DevState
        """
        # PROTECTED REGION ID(CspSubarray.pssSubarrayState_read) ENABLED START #
        return self._pss_subarray_state
        # PROTECTED REGION END #    //  CspSubarray.pssSubarrayState_read

    def read_cbfSubarrayHealthState(self):
        """
        *Attribute method*

        Returns:
            The CBF sub-element subarray *healtState* attribute value.

            *Type*: DevUShort
        """
        # PROTECTED REGION ID(CspSubarray.cbfSubarrayHealthState_read) ENABLED START #
        return self._cbf_subarray_health_state
        # PROTECTED REGION END #    //  CspSubarray.cbfSubarrayHealthState_read

    def read_pssSubarrayHealthState(self):
        """
        *Attribute method*

        Returns:
            The PSS sub-element subarray *healtState* attribute value.

            *Type*: DevUShort
        """
        # PROTECTED REGION ID(CspSubarray.pssSubarrayHealthState_read) ENABLED START #
        return self._pss_subarray_health_state
        # PROTECTED REGION END #    //  CspSubarray.pssSubarrayHealthState_read

    def read_cbfSubarrayObsState(self):
        """
        *Attribute method*

        Returns:
            The CBF sub-element subarray *obsState* attribute value.

            *Type*: DevUShort
        """
        # PROTECTED REGION ID(CspSubarray.cbfSubarrayObsState_read) ENABLED START #
        return self._cbf_subarray_obs_state
        # PROTECTED REGION END #    //  CspSubarray.cbfSubarrayObsState_read

    def read_pssSubarrayObsState(self):
        """
        *Attribute method*

        Returns:
            The PSS sub-element subarray *obsState* attribute value.

            *Type*: DevUShort
        """
        # PROTECTED REGION ID(CspSubarray.pssSubarrayObsState_read) ENABLED START #
        return self._pss_subarray_obs_state
        # PROTECTED REGION END #    //  CspSubarray.pssSubarrayObsState_read

    def read_pssSubarrayAddr(self):
        """
        *Attribute method*

        Returns:
            The PSS sub-element subarray FQDN.

            *Type*: DevString
        """
        # PROTECTED REGION ID(CspSubarray.pssSubarrayAddr_read) ENABLED START #
        return self._pss_subarray_fqdn
        # PROTECTED REGION END #    //  CspSubarray.pssSubarrayAddr_read

    def read_cbfSubarrayAddr(self):
        """
        *Attribute method*

        Returns:
            The CSP sub-element subarray FQDN.

            *Type*: DevString
        """
        # PROTECTED REGION ID(CspSubarray.cbfSubarrayAddr_read) ENABLED START #
        return self._cbf_subarray_fqdn
        # PROTECTED REGION END #    //  CspSubarray.cbfSubarrayAddr_read

    def read_validScanConfiguration(self):
        """
        *Attribute method*

        Returns:
            The last programmed scan configuration.

            *Type*: DevString (JSON-encoded)
        """
        # PROTECTED REGION ID(CspSubarray.validScanConfiguration_read) ENABLED START #
        return self._valid_scan_configuration
        # PROTECTED REGION END #    //  CspSubarray.validScanConfiguration_read

    def read_fsp(self):
        """
        *Attribute method*

        Returns:
            The list of FSP IDs assigned to the subarray.

            *Type*: array of DevUShort.
        """
        # PROTECTED REGION ID(CspSubarray.fsp_read) ENABLED START #
        return self._fsp
        # PROTECTED REGION END #    //  CspSubarray.fsp_read

    def read_vcc(self):
        """
        *Attribute method*

        Returns:
            The list of VCC IDs assigned to the subarray.

            *Type*: array of DevUShort.
        """
        # PROTECTED REGION ID(CspSubarray.vcc_read) ENABLED START #
        self._vcc = []
        try:
            assigned_receptors = self._se_subarrays_proxies[self._cbf_subarray_fqdn].receptors
            # NOTE: if receptors attribute is empty, assigned_receptors is an empty numpy array
            # and it will just be skipped by the for loop
            for receptor_id in assigned_receptors:
                vcc_id = self._receptor_to_vcc_map[receptor_id]
                self._vcc.append(vcc_id)
        except KeyError as key_err:
            msg = "No {} found".format(key_err)
            tango.Except.throw_exception("Read attribute failure",
                                         msg,
                                         "read_vcc",
                                         tango.ErrSeverity.ERR)
        except tango.DevFailed as df:
            tango.Except.throw_exception("Read attribute failure",
                                         df.args[0].desc,
                                         "read_vcc",
                                         tango.ErrSeverity.ERR)
        return self._vcc
        # PROTECTED REGION END #    //  CspSubarray.vcc_read

    def read_searchBeams(self):
        """
        *Attribute method*

        Returns:
            The list of Search Beam Capability IDs assigned to the subarray.

            *Type*: array of DevUShort.
        """
        # PROTECTED REGION ID(CspSubarray.vcc_read) ENABLED START #
        return self._search_beams
        # PROTECTED REGION END #    //  CspSubarray.vcc_read

    def read_timingBeams(self):
        """
        *Attribute method*

        Returns:
            The list of Timing Beam Capability IDs assigned to the subarray.

            *Type*: array of DevUShort.
        """
        # PROTECTED REGION ID(CspSubarray.vcc_read) ENABLED START #
        return self._timing_beams
        # PROTECTED REGION END #    //  CspSubarray.vcc_read

    def read_vlbiBeams(self):
        """
        *Attribute method*

        Returns:
            The list of Vlbi Beam Capability IDs assigned to the subarray.

            *Type*: array of DevUShort.
        """
        # PROTECTED REGION ID(CspSubarray.vcc_read) ENABLED START #
        return self._vlbi_beams
        # PROTECTED REGION END #    //  CspSubarray.vcc_read

    def read_searchBeamsState(self):
        """
        *Attribute method*

        Returns:
            The Search Beam Capabilities *State* attribute value.

            *Type*: array of DevState
        """
        # PROTECTED REGION ID(CspSubarray.searchBeamsState_read) ENABLED START #
        return [tango.DevState.UNKNOWN]
        # PROTECTED REGION END #    //  CspSubarray.searchBeamsState_read

    def read_timingBeamsState(self):
        """
        *Attribute method*

        Returns:
            The Timing Beam Capabilities *State* attribute value.

            *Type*: array of DevState
        """
        # PROTECTED REGION ID(CspSubarray.timingBeamsState_read) ENABLED START #
        return [tango.DevState.UNKNOWN]
        # PROTECTED REGION END #    //  CspSubarray.timingBeamsState_read

    def read_vlbiBeamsState(self):
        """
        *Attribute method*

        Returns:
            The Vlbi Beam Capabilities *State* attribute value.

            *Type*: array of DevState
        """
        # PROTECTED REGION ID(CspSubarray.vlbiBeamsState_read) ENABLED START #
        return [tango.DevState.UNKNOWN]
        # PROTECTED REGION END #    //  CspSubarray.vlbiBeamsState_read

    def read_searchBeamsHealthState(self):
        """
        *Attribute method*

        Returns:
            The Search Beam Capabilities *healthState* attribute value.

            *Type*: array of DevUShort
        """
        # PROTECTED REGION ID(CspSubarray.searchBeamsHealthState_read) ENABLED START #
        return [0]
        # PROTECTED REGION END #    //  CspSubarray.searchBeamsHealthState_read

    def read_timingBeamsHealthState(self):
        """
        *Attribute method*

        Returns:
            The Timing Beam Capabilities *healthState* attribute value.

            *Type*: array of DevUShort
        """
        # PROTECTED REGION ID(CspSubarray.timingBeamsHealthState_read) ENABLED START #
        return [0]
        # PROTECTED REGION END #    //  CspSubarray.timingBeamsHealthState_read

    def read_vlbiBeamsHealthState(self):
        """
        *Attribute method*

        Returns:
            The Vlbi Beam Capabilities *healthState* attribute value.

            *Type*: array of DevUShort
        """
        # PROTECTED REGION ID(CspSubarray.vlbiBeamsHealthState_read) ENABLED START #
        return [0]
        # PROTECTED REGION END #    //  CspSubarray.vlbiBeamsHealthState_read

    def read_timingBeamsObsState(self):
        """
        *Attribute method*

        Returns:
            The Timing Beam Capabilities *obsState* attribute value.

            *Type*: array of DevUShort
        """
        # PROTECTED REGION ID(CspSubarray.timingBeamsObsState_read) ENABLED START #
        return [0]
        # PROTECTED REGION END #    //  CspSubarray.timingBeamsObsState_read


    # --------
    # Commands
    # --------

    def is_EndScan_allowed(self):
        """
        *TANGO is_allowed method*: filter the external request depending on the \
        current device state.\n
        Check if the Scan method can be issued on the subarray.\n
        The Scan() method can be issue on a subarray if its *State* is ON.

        Returns:
            True if the command can be executed, otherwise False
        """
        #TODO: checks other states?
        if self.get_state() in [tango.DevState.ON]:
            return True
        return False

    @command(
    )
    @DebugIt()
    def EndScan(self):
        """
        *Class method*
        End the execution of a running scan.

        Raises:
            tango.DevFailed: if the subarray *obsState* is not SCANNING or if an exception
            is caught during the command execution.
        """
        # PROTECTED REGION ID(CspSubarray.EndScan) ENABLED START #
        # Check if the EndScan command can be executed. This command is allowed when the
        # Subarray State is SCANNING.
        if self._obs_state != ObsState.SCANNING:
            log_msg = "Subarray obs_state is {}, not SCANNING".format(ObsState(self._obs_state).name)
            tango.Except.throw_exception("Command failed",
                                         log_msg,
                                         "EndScan",
                                         tango.ErrSeverity.ERR)
        proxy = 0
        #TODO:the command is forwarded only to CBF. Future implementation has to
        # check the observing mode and depending on this, the command is forwarded to
        # the interested sub-elements.
        if self.__is_subarray_available(self._cbf_subarray_fqdn):
            try:
                proxy = self._se_subarrays_proxies[self._cbf_subarray_fqdn]
                # forward asynchrnously the command to the CbfSubarray
                proxy.command_inout_asynch("EndScan", self.__cmd_ended)
            except tango.DevFailed as df:
                log_msg = ''
                for item in df.args:
                    log_msg += item.reason + " " + item.desc
                self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
                tango.Except.re_throw_exception(df, "Command failed",
                                                "CspSubarray EndScan command failed",
                                                "Command()",
                                                tango.ErrSeverity.ERR)
            except KeyError as key_err:
                msg = " Can't retrieve the information of key {}".format(key_err)
                self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
                tango.Except.throw_exception("Command failed",
                                             msg,
                                             "EndScan",
                                             tango.ErrSeverity.ERR)
        else:
            log_msg = "Subarray {} not registered".format(str(self._cbf_subarray_fqdn))
            self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
            tango.Except.throw_exception("Command failed",
                                         log_msg,
                                         "EndScan",
                                         tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CspSubarray.EndScan

    def is_Scan_allowed(self):
        """
        *TANGO is_allowed method*: filter the external request depending on the current \
        device state.\n
        Check if the Scan method can be issued on the subarray.\n
        A scan configuration can be performed when the subarray *State* is ON (that is, \
        at least one receptor is assigned to it)

        Returns:
            True if the command can be executed, otherwise False
        """
        #TODO: checks other states?
        if self.get_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in="Activation time of the scan, as seconds since the Linux epoch"
    )
    @DebugIt()
    def Scan(self, argin):
        """
        *Class method*

        Start the execution of scan.

        Raises:
            tango.DevFailed: if the subarray *obsState* is not READY or if an exception is caught\
                    during the command execution.
        """
        # PROTECTED REGION ID(CspSubarray.Scan) ENABLED START #
        # Check if the Scan command can be executed. This command is allowed when the
        # Subarray State is READY.
        if self._obs_state != ObsState.READY.value:
            log_msg = "Subarray is in {} state, not READY".format(ObsState(self._obs_state).name)
            tango.Except.throw_exception("Command failed",
                                         log_msg,
                                         "Scan",
                                         tango.ErrSeverity.ERR)
        proxy = 0
        if self.__is_subarray_available(self._cbf_subarray_fqdn):
            try:
                proxy = self._se_subarrays_proxies[self._cbf_subarray_fqdn]
                # forward the command to the CbfSubarray asynchrnously
                proxy.command_inout_asynch("Scan", argin, self.__cmd_ended)
                # self._obs_state = ObsState.SCANNING.value
            except tango.DevFailed as df:
                log_msg = ''
                for item in df.args:
                    log_msg += item.reason + " " + item.desc
                self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
                tango.Except.re_throw_exception(df, "Command failed",
                                                "CspSubarray Scan command failed",
                                                "Command()",
                                                tango.ErrSeverity.ERR)
            except KeyError as key_err:
                msg = " Can't retrieve the information of key {}".format(key_err)
                self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
                tango.Except.throw_exception("Command failed", msg, "Scan", tango.ErrSeverity.ERR)
        else:
            log_msg = "Subarray {} not registered".format(str(self._cbf_subarray_fqdn))
            self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
            tango.Except.throw_exception("Command failed", log_msg, "Scan", tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CspSubarray.Scan

    def is_AddReceptors_allowed(self):
        """
        *TANGO is_allowed method*: filter the external request depending on the current \
        device state.\n
        Check if the AddReceptors method can be issued on the subarray.\n
        Receptors can be added to a Subarray when its *State* is OFF or ON.

        Returns:
            True if the command can be executed, otherwise False
        """
        return self.__is_add_resources_allowed()

    @command(
        dtype_in=('uint16',),
        doc_in="List of the receptor IDs to add to the subarray.",
    )
    @DebugIt()
    def AddReceptors(self, argin):
        """
        *Class method*

        Add the specified receptor IDs to the subarray.

        Args:
            argin: the list of receptor IDs
            Type: array of DevUShort
        Returns:
            None
        Raises:
            tango.DevFailed: if the CbfSubarray is not available or if an exception\
                    is caught during command execution.
        """
        # PROTECTED REGION ID(CspSubarray.AddReceptors) ENABLED START #
        # Each vcc_id map to a vcc_fqdn inside CbfMaster, for example:
        # vcc_id = 1 -> mid_csp_cbf/vcc/vcc_001
        # vcc_id = 2 -> mid_csp_cbf/vcc/vcc_002
        # .....
        # vcc_id = 17 -> mid_csp_cbf/vcc/vcc_017
        # vcc_id and receptor_id is not the same. The map between vcc_id and receptor_id
        # is built by CbfMaster and exported as attribute.
        # The max number of VCC allocated is defined by the VCC property of the CBF Master.

        # Check if the AddReceptors command can be executed. Receptors can be assigned to a subarray
        # only when its obsState is IDLE.
        if self._obs_state != ObsState.IDLE:
            log_msg = ("AddReceptors not allowed when subarray"
                       " ObsState is {}".format(Obstate(self._obs_state).name))
            tango.Except.throw_exception("Command failed",
                                         log_msg,
                                         "AddReceptors",
                                         tango.ErrSeverity.ERR)
        # the list of available receptor IDs. This number is mantained by the CspMaster
        # and reported on request.
        available_receptors = []
        # the list of receptor to assign to the subarray
        receptor_to_assign = []
        try:
            # access to CspMaster to get information about the list of available receptors
            # and the receptors affiliation to subarrays.
            cspMasterProxy = tango.DeviceProxy(self.CspMaster)
            cspMasterProxy.ping()
            available_receptors = cspMasterProxy.availableReceptorIDs
            #!!!!!!!!!!!!!!!!!
            # NOTE: need to check if available_receptors is None: this happens when all
            # the provided receptors are assigned.
            # NOTE: if the Tango attribute is read-only (as in the case of availableReceptorIDs)
            # the read method returns a None type. If the Tango attribute is RW the read methods
            # returns an empty tuple (whose length is 0)
            #
            # 2019-09-20 NOTE: the previous statement is true for the images of Tango and Pytango
            # 9.2.5, with PyTango not compiled with numpy support!!!
            # After moving to TANGO and PyTango 9.3.0 (compiled with numpy support)
            # if there is no available receptor the call to cspMasterProxy.availableReceptorIDs
            # returns an array= [0] (an empty list generates the error "DeviceAttribute object has
            # no attribute 'value'"). The length of the array is 1 and its value is 0.
            # Checks on available_receptors need to be changed (see below).
            #
            # 2019-10-18: with the new TANGO/PyTango images release (PyTango 9.3.1,
            # TANGO 9.3.3, numpy 1.17.2)
            # the issue of "DeviceAttribute object has no attribute 'value'" has been resolved. Now
            # a TANGO RO attribute initialized to an empty list (see self._available_receptorIDs),
            # returns a NoneType object (as before with PyTango/TANGO 9.2.5 images).
            # The behavior now is coherent, but I don't revert to the old code: this methods keep
            # returning an array with one element = 0 when receptors are not available.
            #!!!!!!!!!!!!!!!!!
            #if not available_receptors:  # old code!!
            # NO available receptors!
            if available_receptors[0] == 0:
                log_msg = "No available receptor to add to subarray {}".format(self._subarray_id)
                self.dev_logging(log_msg, tango.LogLevel.LOG_WARN)
                return
            receptor_membership = cspMasterProxy.receptorMembership
        except tango.DevFailed as df:
            msg = "Failure in getting receptors information:" + str(df.args[0].reason)
            tango.Except.throw_exception("Command failed", msg,
                                         "AddReceptors", tango.ErrSeverity.ERR)
        except AttributeError as attr_err:
            msg = "Failure in reading {}: {}".format(str(attr_err.args[0]), attr_err.__doc__)
            tango.Except.throw_exception("Command failed", msg,
                                         "AddReceptors", tango.ErrSeverity.ERR)
        for receptorId in argin:
            # check if the specified receptor id is a valid number (that is, belongs to the list
            # of provided receptors)
            if receptorId in self._receptor_id_list:
                # check if the receptor id is one of the available receptor Ids
                if receptorId in available_receptors:
                    receptor_to_assign.append(receptorId)
                else:
                    # retrieve the subarray owner
                    sub_id = receptor_membership[receptorId - 1]
                    log_msg = "Receptor {} already assigned to subarray {}".format(str(receptorId),
                                                                                   str(sub_id))
                    self.dev_logging(log_msg, tango.LogLevel.LOG_WARN)
            else:
                log_msg = "Invalid receptor id: {}".format(str(receptorId))
                self.dev_logging(log_msg, tango.LogLevel.LOG_WARN)

        # check if the list of receptors to assign is empty
        if not receptor_to_assign:
            log_msg = "The required receptors are already assigned to a subarray"
            self.dev_logging(log_msg, tango.LogLevel.LOG_INFO)
            return
        # check if the CspSubarray is already connected to the CbfSubarray
        proxy = 0
        if self.__is_subarray_available(self._cbf_subarray_fqdn):
            try:
                proxy = self._se_subarrays_proxies[self._cbf_subarray_fqdn]
                # remove possible receptor repetition
                tmp = set(receptor_to_assign)
                receptor_to_assign = list(tmp)
                # forward the command to the CbfSubarray
                proxy.command_inout("AddReceptors", receptor_to_assign)
            except KeyError as key_err:
                msg = " Can't retrieve the information of key {}".format(key_err)
                self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
                tango.Except.throw_exception("Command failed",
                                             msg,
                                             "AddReceptors",
                                             tango.ErrSeverity.ERR)
            except tango.DevFailed as df:
                log_msg = "AddReceptor command failure."
                for item in df.args:
                    log_msg += "Reason: {}. Desc: {}".format(item.reason, item.desc)
                self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
                tango.Except.re_throw_exception(df, "Command failed",
                                                "CspSubarray AddReceptors command failed",
                                                "Command()",
                                                tango.ErrSeverity.ERR)
            except TypeError as err:
                # Raised when an operation or function is applied to an object of
                # inappropriate type. The associated value is a string giving details about
                # the type mismatch.
                log_msg = "TypeError: {}".format(str(err))
                self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
                tango.Except.throw_exception("Command failed",
                                             log_msg,
                                             "AddReceptors",
                                             tango.ErrSeverity.ERR)
        else:
            log_msg = "Subarray {} not registered!".format(str(self._cbf_subarray_fqdn))
            self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
            tango.Except.throw_exception("Command failed",
                                         log_msg,
                                         "AddReceptors",
                                         tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CspSubarray.AddReceptors

    def is_RemoveReceptors_allowed(self):
        """
        *TANGO is_allowed method*: filter the external request depending on the \
        current device state.\n
        Check if the method can be issued on the subarray.\n
        Re can be removed from a subarray when its *State* is ON or OFF-

        Returns:
            True if the command can be executed, otherwise False
        """
        return self.__is_remove_resources_allowed()

    @command(
        dtype_in=('uint16',),
        doc_in="The list with the receptor IDs to remove",
    )
    @DebugIt()
    def RemoveReceptors(self, argin):
        """
        Remove the receptor IDs from the subarray.

        Args:
            argin: The list of the receptor IDs to remove from the subarray.
            Type: array of DevUShort
        Returns:
            None
        Raises:
            tango.DevFailed: raised if the subarray *obState* attribute is not IDLE, or \
                    when an exception is caught during command execution.
        """
        # PROTECTED REGION ID(CspSubarray.RemoveReceptors) ENABLED START #

        # Check if the RemoveReceptors command can be executed. Receptors can be removed
        # from a subarray only when its obsState is IDLE or READY.
        if self._obs_state != ObsState.IDLE.value:
            #get the obs_state label
            log_msg = ("Command RemoveReceptors not allowed when subarray "
                       "ObsState is {}".format(ObsState(self._obs_state).name))
            tango.Except.throw_exception("Command failed",
                                         log_msg,
                                         "RemoveReceptors",
                                         tango.ErrSeverity.ERR)

        # check if the CspSubarray is already connected to the CbfSubarray
        proxy = 0
        if self.__is_subarray_available(self._cbf_subarray_fqdn):
            try:
                proxy = self._se_subarrays_proxies[self._cbf_subarray_fqdn]
                # read from CbfSubarray the list of assigned receptors
                receptors = proxy.receptors
                #!!!!!!!!!!!!!!!!!
                # 2019-09-20:  New images for TANGO and PyTango images has been released. PyTango
                # is now compiled with th numpy support. In this case the proxy.receptors call
                # does no more return an empty tuple but an empty numpy array.
                # Checks on receptors content need to be changed (see below)
                # NB: the receptors attribute implemented by the CbfSubarray is declared as RW.
                # In this case the read method returns an empty numpy array ([]) whose length is 0.
                #!!!!!!!!!!!!!!!!!

                # check if the list of assigned receptors is empty.
                #if not receptors:
                if len(receptors) == 0:
                    self.dev_logging("RemoveReceptors: no receptor to remove",
                                     tango.LogLevel.LOG_INFO)
                    return
                receptors_to_remove = []
                # check if the receptors to remove belong to the subarray
                for receptor_id in argin:
                    if receptor_id in receptors:
                        receptors_to_remove.append(receptor_id)
                # forward the command to CbfSubarray
                proxy.RemoveReceptors(receptors_to_remove)
                receptors = proxy.receptors
            except tango.DevFailed as df:
                log_msg = "RemoveReceptors:" + df.args[0].desc
                self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
                tango.Except.re_throw_exception(df, "Command failed",
                                                "CspSubarray RemoveReceptors command failed",
                                                "Command()",
                                                tango.ErrSeverity.ERR)
        else:
            log_msg = "Subarray not registered!".format(str(self._cbf_subarray_fqdn))
            self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
            tango.Except.throw_exception("Command failed",
                                         log_msg,
                                         "RemoveReceptors",
                                         tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CspSubarray.RemoveReceptors

    def is_RemoveAllReceptors_allowed(self):
        """
        *TANGO is_allowed method*: filter the external request depending on the \
        current device state.\n
        Check if the method can be issued on the subarray.\n
        Resources can be removed from a subarray when its *State* is ON or OFF-

        Returns:
            True if the command can be executed, otherwise False
        """
        return self.__is_remove_resources_allowed()

    @command(
    )
    @DebugIt()
    def RemoveAllReceptors(self):
        """
        *Class method.*

        Remove all the assigned receptors from the subarray.
        Returns:
            None
        Raises:
            tango.DevFailed: raised if the subarray *obState* attribute is not IDLE or READY, or \
            when an exception is caught during command execution.
        """
        # PROTECTED REGION ID(CspSubarray.RemoveAllReceptors) ENABLED START #

        # Check if the RemoveAllReceptors command can be executed. Receptors can be removed
        # from a subarray only when its obsState is IDLE or READY.
        if self._obs_state != ObsState.IDLE.value:
            log_msg = ("Command RemoveAllReceptors not allowed when subarray"
                       " ObsState is {}".format(ObsState(self._obs_state).name))
            tango.Except.throw_exception("Command failed",
                                         log_msg,
                                         "RemoveAllReceptors",
                                         tango.ErrSeverity.ERR)
        proxy = 0
        if self.__is_subarray_available(self._cbf_subarray_fqdn):
            try:
                proxy = self._se_subarrays_proxies[self._cbf_subarray_fqdn]
                # check if the list of assigned receptors is empty
                receptors = proxy.receptors
                #!!!!!!!!!!!!!!!!!
                # 09/20/2019 ATT:  New images for TANGO and PyTango images has been released.
                # PyTango is now compiled with th numpy support. In this case the proxy.receptors
                # call does no more return an empty tuple but an empty numpy array.
                # Checks on receptors content need to be changed (see below)
                # NB: the receptors attribute implemented by the CbfSubarray is declared as RW.
                # In this case the read method returns an empty numpy array ([]) whose length is 0
                #!!!!!!!!!!!!!!!!!
                #if not receptors:
                if len(receptors) == 0:
                    self.dev_logging("RemoveAllReceptors: no receptor to remove",
                                     tango.LogLevel.LOG_INFO)
                    return
                # forward the command to the CbfSubarray
                proxy.command_inout("RemoveAllReceptors")
                #self._vcc = []
            except tango.DevFailed as df:
                log_msg = ("RemoveAllReceptors failure. Reason: {} "
                           "Desc: {}".format(df.args[0].reason,
                                             df.args[0].desc))
                self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
                tango.Except.re_throw_exception(df, "Command failed",
                                                "CspSubarray RemoveAllReceptors command failed",
                                                "Command()",
                                                tango.ErrSeverity.ERR)
            except KeyError as key_err:
                log_msg = "No key {} found".format(str(key_err))
                tango.Except.throw_exception("Command failed",
                                             log_msg,
                                             "RemoveAllReceptors",
                                             tango.ErrSeverity.ERR)
        else:
            log_msg = "Subarray {} not registered!".format(str(self._cbf_subarray_fqdn))
            self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
            tango.Except.throw_exception("Command failed",
                                         log_msg,
                                         "RemoveAllReceptors",
                                         tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CspSubarray.RemoveAllReceptors

    def is_ConfigureScan_allowed(self):
        """
        *TANGO is_allowed method*: filter the external request depending on the current\
        device state.\n
        Check if the ConfigureScan method can be issued on the subarray.\n
        A scan configuration can be performed when the subarray *State* is ON (that is, \
        at least one receptor is assigned to it)

        Returns:
            True if the command can be executed, otherwise False
        """
        #TODO:checks other states?
        if self.get_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in="A Json-encoded string with the scan configuration.",
    )
    @DebugIt()
    def ConfigureScan(self, argin):
        """
        Note:
            Part of this code (the input string parsing) comes from the CBF project\
                    developed by J.Jjang (NRC-Canada)

        *Class method.*

        Configure a scan for the subarray.

        Args:
            argin: a JSON-encoded string with the parameters to configure a scan.
        Returns:
            None
        Raises:
            tango.DevFailed exception if the configuration is not valid or if an exception\
                    is caught during command execution.
        """
        # PROTECTED REGION ID(CspSubarray.ConfigureScan) ENABLED START #

        # check obs_state: the subarray can be configured only when the obs_state is
        # IDLE or READY (re-configuration)

        if self._obs_state not in [ObsState.IDLE.value, ObsState.READY.value]:
            log_msg = ("Subarray is in {} state, not IDLE or"
                       " READY".format(ObsState(self._obs_state).name))
            tango.Except.throw_exception("Command failed",
                                         log_msg,
                                         "Scan",
                                         tango.ErrSeverity.ERR)
        # check connection with CbfSubarray
        if not self.__is_subarray_available(self._cbf_subarray_fqdn):
            log_msg = "Subarray {} not registered!".format(str(self._cbf_subarray_fqdn))
            self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
            tango.Except.throw_exception("Command failed",
                                         log_msg,
                                         "ConfigureScan execution",
                                         tango.ErrSeverity.ERR)
        # the dictionary with the scan configuration
        argin_dict = {}
        try:
            # for test purpose we load the json configuration from an
            # external file.
            # TO REMOVE!!
            if "load" in argin:
                # skip the 'load' chars and remove spaces from the filename
                fn = (argin[4:]).strip()
                filename = os.path.join(commons_pkg_path, fn)
                with open(filename) as json_file:
                    # load the file into a dictionary
                    argin_dict = json.load(json_file)
                    # dump the dictionary into the input string to forward
                    # to CbfSubarray
                    argin = json.dumps(argin_dict)
            else:
                argin_dict = json.loads(argin)
        except FileNotFoundError as file_err:
            self.dev_logging(str(file_err), tango.LogLevel.LOG_ERROR)
            tango.Except.throw_exception("Command failed",
                                         str(file_err),
                                         "ConfigureScan execution",
                                         tango.ErrSeverity.ERR)
        except json.JSONDecodeError as e:  # argument not a valid JSON object
            # this is a fatal error
            msg = ("Scan configuration object is not a valid JSON object."
                   "Aborting configuration:{}".format(str(e)))
            self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
            tango.Except.throw_exception("Command failed",
                                         msg,
                                         "ConfigureScan execution",
                                         tango.ErrSeverity.ERR)
        # Validate scanID.
        # If not given, abort the scan configuration.
        # If malformed, abort the scan configuration.
        if "scanID" in argin_dict:
            if int(argin_dict["scanID"]) <= 0:  # scanID not positive
                msg = ("'scanID' must be positive (received {}). "
                       "Aborting configuration.".format(int(argin_dict["scanID"])))
                # this is a fatal error
                self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
                tango.Except.throw_exception("Command failed",
                                             msg,
                                             "ConfigureScan execution",
                                             tango.ErrSeverity.ERR)
            #TODO:add on CspMaster the an attribute with the list of scanID
            # of each sub-array
            #elif any(map(lambda i: i == int(argin_dict["scanID"]),
            #             self._proxy_csp_master.subarrayScanID)):  # scanID already taken
            #    msg = "'scanID' must be unique (received {}). "\
            #        "Aborting configuration.".format(int(argin_dict["scanID"]))
            # this is a fatal error
            #    self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
            #    tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
            #                                   tango.ErrSeverity.ERR)
            else:  # scanID is valid
                self._scan_ID = int(argin_dict["scanID"])
        else:  # scanID not given
            msg = "'scanID' must be given. Aborting configuration."
            # this is a fatal error
            self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
            tango.Except.throw_exception("Command failed",
                                         msg,
                                         "ConfigureScan execution",
                                         tango.ErrSeverity.ERR)
        # Validate frequencyBand.
        # If not given, abort the scan configuration.
        # If malformed, abort the scan configuration.
        frequency_band = 0
        if "frequencyBand" in argin_dict:
            frequency_bands = ["1", "2", "3", "4", "5a", "5b"]
            if argin_dict["frequencyBand"] in frequency_bands:
                frequency_band = frequency_bands.index(argin_dict["frequencyBand"])
            else:
                msg = ("'frequencyBand' must be one of {} (received {}). "
                       "Aborting configuration.".format(frequency_bands,
                                                        argin_dict["frequencyBand"]))
                # this is a fatal error
                self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
                tango.Except.throw_exception("Command failed",
                                             msg,
                                             "ConfigureScan execution",
                                             tango.ErrSeverity.ERR)
        else:  # frequencyBand not given
            msg = "'frequencyBand' must be given. Aborting configuration."
            # this is a fatal error
            self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
            tango.Except.throw_exception("Command failed",
                                         msg,
                                         "ConfigureScan execution",
                                         tango.ErrSeverity.ERR)

        # ======================================================================= #
        # At this point, self._scan_ID, self._receptors, and self._frequency_band #
        # are guaranteed to be properly configured.                               #
        # ======================================================================= #

        # Validate band5Tuning, if frequencyBand is 5a or 5b.
        # If not given, abort the scan configuration.
        # If malformed, abort the scan configuration.
        if frequency_band in [4, 5]:  # frequency band is 5a or 5b
            if "band5Tuning" in argin_dict:
                # check if streamTuning is an array of length 2
                try:
                    assert len(argin_dict["band5Tuning"]) == 2
                except (TypeError, AssertionError):
                    msg = ("'band5Tuning' must be an array of length 2."
                           "Aborting configuration.")
                    # this is a fatal error
                    self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
                    tango.Except.throw_exception("Command failed",
                                                 msg,
                                                 "ConfigureScan execution",
                                                 tango.ErrSeverity.ERR)

                stream_tuning = [*map(float, argin_dict["band5Tuning"])]
                if frequency_band == 4:
                    if not all([5.85 <= stream_tuning[i] <= 7.25 for i in [0, 1]]):
                        msg = ("Elements in 'band5Tuning must be floats between"
                               " 5.85 and 7.25 (received {} and {}) for a "
                               "'frequencyBand' of 5a."
                               "Aborting configuration.".format(stream_tuning[0],
                                                                stream_tuning[1]))
                        # this is a fatal error
                        self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
                        tango.Except.throw_exception("Command failed",
                                                     msg,
                                                     "ConfigureScan execution",
                                                     tango.ErrSeverity.ERR)
                else:  # self._frequency_band == 5
                    if not all([9.55 <= stream_tuning[i] <= 14.05 for i in [0, 1]]):
                        msg = ("Elements in 'band5Tuning must be floats between "
                               "9.55 and 14.05 (received {} and {}) for a "
                               "'frequencyBand' of 5b. "
                               "Aborting configuration.".format(stream_tuning[0],
                                                                stream_tuning[1]))
                        # this is a fatal error
                        self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
                        tango.Except.throw_exception("Command failed",
                                                     msg,
                                                     "ConfigureScan execution",
                                                     tango.ErrSeverity.ERR)
            else:
                msg = ("'band5Tuning' must be given for a"
                       " 'frequencyBand' of {}. "
                       "Aborting configuration".format(["5a", "5b"][frequency_band - 4]))
                # this is a fatal error
                self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
                tango.Except.throw_exception("Command failed",
                                             msg,
                                             "ConfigureScan execution",
                                             tango.ErrSeverity.ERR)

        # Forward the ConfigureScan command to CbfSubarray.
        try:
            proxy = self._se_subarrays_proxies[self._cbf_subarray_fqdn]
            proxy.ping()
            # self._obs_state = ObsState.CONFIGURING.value
            # use asynchrnous model
            # in this case the obsMode and the valid scan configuraiton are set
            # at command end
            proxy.command_inout_asynch("ConfigureScan", argin, self.__cmd_ended)
            #self._valid_scan_configuration = argin
        except tango.DevFailed as df:
            log_msg = ''
            for item in df.args:
                log_msg += item.reason + " " + item.desc
            self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
            tango.Except.re_throw_exception(df,
                                            "Command failed",
                                            "CspSubarray ConfigureScan command failed",
                                            "Command()",
                                            tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CspSubarray.ConfigureScan

    @command(
        dtype_in='uint16',
        doc_in="The number of SearchBeams Capabilities to assign to the subarray",
    )
    @DebugIt()
    def AddNumOfSearchBeams(self, argin):
        """
        Note:
            Still to be implemented
        *Class method*

        Add the specified number of Search Beams capabilities to the subarray.

        Args:
            argin: The number of SearchBeams Capabilities to assign to the subarray
        Returns:
            None
        """
        # PROTECTED REGION ID(CspSubarray.AddSearchBeams) ENABLED START #
        return
        # PROTECTED REGION END #    //  CspSubarray.AddSearchBeams

    @command(
        dtype_in='uint16',
        doc_in="The number of SearchBeam Capabilities to remove from the sub-arrays.\n\
            All the search beams are removed from the sub-array if the input number \n\
            is equal to the max number of search bem capabilities (1500 for MID)",
    )
    @DebugIt()
    def RemoveNumOfSearchBeams(self, argin):
        """
        Note:
            Still to be implemented
        *Class method*

        Remove the specified number of Search Beams capabilities from the subarray.

        Args:
            argin: The number of SearchBeams Capabilities to remove from \
            the subarray. If equal to the max number of search bem capabilities \
            (1500 for MID), all the search beams are removed.
        Returns:
            None
        """
        
        # PROTECTED REGION ID(CspSubarray.RemoveSearchBeams) ENABLED START #
        return
        # PROTECTED REGION END #    //  CspSubarray.RemoveSearchBeams

    @command(
        dtype_in=('uint16',),
        doc_in="The list of timing beams IDs to assign to the subarray",
    )
    @DebugIt()
    def AddTimingBeams(self, argin):
        """
        Note:
            Still to be implemented
        *Class method*

        Add the specified Timing Beams Capability IDs to the subarray.

        Args:
            argin: The list of  Timing Beams Capability IDs to assign to the subarray.
            Type: array of DevUShort
        Returns:
            None
        """
        # PROTECTED REGION ID(CspSubarray.AddTimingBeams) ENABLED START #
        return
        # PROTECTED REGION END #    //  CspSubarray.AddTimingBeams

    @command(
        dtype_in=('uint16',),
        doc_in="The list of Vlbi beams ID to assign to the subarray.",
    )
    @DebugIt()
    def AddVlbiBeams(self, argin):
        """
        Note:
            Still to be implemented
        *Class method*

        Add the specified Vlbi Beams Capability IDs to the subarray.
   
        Args:
            argin: The list of Vlbi Beams Capability IDs to assign to the subarray.
            Type: array of DevUShort
        Returns:
            None
        """
        # PROTECTED REGION ID(CspSubarray.AddVlbiBeams) ENABLED START #
        return
        # PROTECTED REGION END #    //  CspSubarray.AddVlbiBeams

    @command(
        dtype_in=('uint16',),
        doc_in="The list of Search Beam Capabilities ID to assign \
                to the sub-array.",
    )
    @DebugIt()
    def AddSearchBeamsID(self, argin):
        """
        Note:
            Still to be implemented
        *Class method*

        Add the specified Search Beams Capability IDs to the subarray.
        This method requires some knowledge of the internal behavior of the PSS machine,\
        because Seach Beam capabilities with PSS pipelines belonging to the same PSS \
        node, can't be assigned to different subarrays.

        Args:
            argin: The list of Search Beams Capability IDs to assign to the subarray.
            Type: array of DevUShort
        Returns:
            None
        References:
            AddNumOfSearchBeams
        """
        # PROTECTED REGION ID(CspSubarray.AddSearchBeamsID) ENABLED START #
        return
        # PROTECTED REGION END #    //  CspSubarray.AddSearchBeamsID

    @command(
        dtype_in=('uint16',),
        doc_in="The list of Search Beams IDs to remove from the sub-array.",
    )
    @DebugIt()
    def RemoveSearchBeamsID(self, argin):
        """
        Note:
            Still to be implemented
        *Class method*

        Remove the specified Search Beam Capability IDs from the subarray.
        
        Args:
            argin: The list of Timing Beams Capability IDs to remove from the subarray.
            Type: Array of unsigned short
        Returns:
            None
        """
        # PROTECTED REGION ID(CspSubarray.RemoveSearchBeamsID) ENABLED START #
        return 
        # PROTECTED REGION END #    //  CspSubarray.RemoveSearchBeamsID

    @command(
        dtype_in=('uint16',),
        doc_in="The list of Timing Beams IDs to remove from the sub-array.",
    )
    @DebugIt()
    def RemoveTimingBeams(self):
        """
        Note:
            Still to be implemented

        *Class method*

        Remove the specified Timing Beam Capability IDs from the subarray.

        Args:
            argin: The list of Timing Beams Capability IDs to remove from the subarray.
            Type: Array of DevUShort
        Returns:
            None
        """
        # PROTECTED REGION ID(CspSubarray.RemoveTimingBeams) ENABLED START #
        return
        # PROTECTED REGION END #    //  CspSubarray.RemoveTimingBeams

    @command(
        dtype_in=('uint16',),
        doc_in="The list of Timing Beams IDs to remove from the sub-array.",
    )
    @DebugIt()
    def RemoveVlbiBeams(self):
        """
        Note:
            Still to be implemented

        *Class method*

        Remove the specified Vlbi Beam Capability IDs from the subarray.
        
        Args:
            argin: The list of Timing Beams Capability IDs to remove from the subarray.
            Type: Array of DevUShort
        Returns:
            None
        """
        # PROTECTED REGION ID(CspSubarray.RemoveVlbiBeams) ENABLED START #
        return
        # PROTECTED REGION END #    //  CspSubarray.RemoveVlbiBeams

    def is_EndSB_allowed(self):
        """
        *TANGO is_allowed method*: filter the external request depending on the \
        current device state.\n
        Check if the EndSB method can be issued on the subarray.\
        The EndSB method can be issued on a subarrays when its *State* is ON-

        Returns:
            True if the command can be executed, otherwise False
        """
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command(
    )
    @DebugIt()
    def EndSB(self):
        """
        *Class method*

        Set the subarray ObsState to IDLE.\n
        Raises
            tango.DevFailed exception if the configuration is not valid or if an exception\
            is caught during command execution.
        """
        # PROTECTED REGION ID(CspSubarray.EndSB) ENABLED START #
        if self._obs_state not in [ObsState.IDLE, ObsState.READY]:
            log_msg = ("Subarray is in {} state, not IDLE or"
                       " READY".format(ObsState(self._obs_state).name))
            tango.Except.throw_exception("Command failed",
                                         log_msg,
                                         "Scan",
                                         tango.ErrSeverity.ERR)
        # check connection with CbfSubarray
        if not self.__is_subarray_available(self._cbf_subarray_fqdn):
            log_msg = "Subarray {} not registered!".format(str(self._cbf_subarray_fqdn))
            self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
            tango.Except.throw_exception("Command failed",
                                         log_msg,
                                         "EndSB execution",
                                         tango.ErrSeverity.ERR)
        try:
            proxy = self._se_subarrays_proxies[self._cbf_subarray_fqdn]
            proxy.ping()
            proxy.command_inout_asynch("EndSB", self.__cmd_ended)
        except tango.DevFailed as df:
            log_msg = ''
            for item in df.args:
                log_msg += item.reason + " " + item.desc
            self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
            tango.Except.re_throw_exception(df, "Command failed",
                                            "CspSubarray EndSB command failed",
                                            "Command()",
                                            tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CspSubarray.EndSB

# ----------
# Run server
# ----------

def main(args=None, **kwargs):
    # PROTECTED REGION ID(CspSubarray.main) ENABLED START #
    return run((CspSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CspSubarray.main

if __name__ == '__main__':
    main()
