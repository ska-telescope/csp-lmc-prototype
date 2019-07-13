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

    CSP subarray functionality is modeled via a TANGO Device Class, named *CspSubarray*. This class exports
    a set of attributes and methods required for configuration, control and monitoring 
    of the subarray.
"""
# Python standard library
from __future__ import absolute_import
import sys
import os
from future.utils import with_metaclass
# PROTECTED REGION END# //CspMaster.standardlibray_import

# tango imports
import tango
from tango import DebugIt, EventType, DeviceProxy, AttrWriteType
from tango.server import run, DeviceMeta, attribute, command, device_property, class_property

# add the path to import global_enum package.
file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

# Additional import
# PROTECTED REGION ID(CspMaster.additionnal_import) ENABLED START #
#
import global_enum as const
from global_enum import HealthState, AdminMode, ObsState, ObsMode
from skabase.SKASubarray import SKASubarray
import json
# PROTECTED REGION END #    //  CspMaster.additionnal_import

__all__ = ["CspSubarray", "main"]

class CspSubarray(with_metaclass(DeviceMeta, SKASubarray)):
    """
    CSP subarray functionality is modeled via a TANGO Device Class, named *CspSubarray*. This class exports
    a set of attributes and methods required for configuration, control and monitoring 
    of the subarray.
    """
    # PROTECTED REGION ID(CspSubarray.class_variable) ENABLED START #

    class CommandCallBack:
        """
        Class with a method named *cmd_ended*.
        
        The Callback is supplied when the caller issues an asynchronous command: the *cmd_end* callback 
        method gets immediately executed when the command returns.

        Important:
           To use the push model (the one with the callback parameter), the global TANGO model has to
           be changed to PUSH_CALLBACK. Do this with the tango.:class:`ApiUtil().set_asynch_cb_sub_model`
        """
        def cmd_ended(self, evt):
            """
            Method immediately executed when the asynchronous invoked command returns.

            Args:
                evt: A CmdDoneEvent object with information about the device, the command name and
                     errors.
            Returns:
                None
            """

            # NOTE: if we try to access to evt.cmd_name or other paramters, the callback crashes with
            # this error:
            # terminate called after throwing an instance of 'boost::python::error_already_set'
            err = True
            device =''
            command = ''
            for attr in dir(evt):
                if attr == "cmd_name":
                    command = getattr(evt, attr)
                if attr == "device":
                    device = getattr(evt, attr)
                if attr == "err":
                    err = getattr(evt, attr)
            if err == False:
                msg = "Device {} is processing command {}".format(device, command)
                self.dev_logging(msg, tango.LogLevel.LOG_INFO)
            else :
                msg = "Error in executing command {} ended on device {}".format(command,device)
                self.dev_logging(msg, tango.LogLevel.LOG_WARN)
                if command == "Scan":
                    self._obs_state = ObsState.READY.value
                    self._obs_mode  = ObsMode.IDLE.value

    # ---------------
    # Event Callback functions
    # ---------------

    def scm_change_callback(self, evt):
        """
        *Class private method.*

        Retrieve the values of the sub-element sub-arrays SCM attributes subscribed for change
        event at device initialization.

        Args: 
            evt: The event data

        Returns:
            None
        """
        if evt.err is False:
            try:
                if "healthstate" in evt.attr_name:
                    self._cbf_subarray_health_state = evt.attr_value.value
                elif "obsstate" in evt.attr_name: 
                    self._cbf_subarray_obs_state = evt.attr_value.value
                elif "state" in  evt.attr_name:
                    self._cbf_subarray_state = evt.attr_value.value
                else:
                    self.dev_logging("Attribute {} not yet handled".format(evt.attr_name), 
                                     tango.LogLevel.LOG_ERR)
                    
                if evt.attr_value.name in ["State","state", "healthState","healthState"]:
                    self.__set_subarray_state() 
                if evt.attr_value.name in ["obsState","obsstate"]:
                    self.__set_subarray_obs_state() 
            except tango.DevFailed as df:
                self.dev_logging(str(df.args[0].desc), tango.LogLevel.LOG_ERR)
        else: 
            for item in evt.errors: 
                # TODO handle API_EventTimeout
                #
                log_msg = item.reason + ": on attribute " + str(evt.attr_name)
                self.dev_logging(log_msg, tango.LogLevel.LOG_WARN)

    # Class private methods

    def __connect_to_subarrays(self):
        """
        *Class private method.*

        Establish connection with each sub-element sub-array.
        If connection succeeds, the CspSubarrays device subscribes the State, healthState 
        and adminMode attributes of each Sub-element sub-array and registers a callback function
        to handle the events. Exceptions are logged.

        Returns:
            None
        Raises:
            tango.DevFailed: raises an execption if connection with a sub-element 
            subarray fails
        """

        subarrays_fqdn = []
        subarrays_fqdn.append(self._cbf_subarray_fqdn)
        subarrays_fqdn.append(self._pss_subarray_fqdn)
            
        for fqdn in subarrays_fqdn:
            # initialize the list for each dictionary key-name
            self._se_subarray_event_id[fqdn] = []
            try:
                log_msg = "Trying connection to" + str(fqdn) + " device"
                self.dev_logging(log_msg, int(tango.LogLevel.LOG_INFO))
                device_proxy = DeviceProxy(fqdn)
                device_proxy.ping()
                # add to the list of subarray FQDNS only registered subarrays
                self._se_subarrays_fqdn.append(fqdn)  
                # store the sub-element proxies 
                self._se_subarrays_proxies[fqdn] = device_proxy

                # Subscription of the sub-element State,healthState and adminMode
                ev_id = device_proxy.subscribe_event("State", EventType.CHANGE_EVENT,
                        self.scm_change_callback, stateless=True)
                self._se_subarray_event_id[fqdn].append(ev_id)

                ev_id = device_proxy.subscribe_event("healthState", EventType.CHANGE_EVENT,
                        self.scm_change_callback, stateless=True)
                self._se_subarray_event_id[fqdn].append(ev_id)

                ev_id = device_proxy.subscribe_event("obsState", EventType.CHANGE_EVENT,
                        self.scm_change_callback, stateless=True)
                self._se_subarray_event_id[fqdn].append(ev_id)

            except tango.DevFailed as df:
                for item in df.args:
                    if "DB_DeviceNotDefined" in item.reason:
                        log_msg = "Failure in connection to " + str(fqdn) + \
                                " device: " + str(item.reason)
                        self.dev_logging(log_msg, int(tango.LogLevel.LOG_ERROR))
                tango.Except.throw_exception(df.args[0].reason, "Connection to {} failed".format(fqdn), 
                                         "Connect to subarrays", tango.ErrSeverity.ERR)

    def __connect_to_master(self):
        """
        *Class private method.*

        Establish connection with the CSP sub-element master to get information about:

        * the CBF Master address

        * the max number of CSP and CBF capabilities for each type

        Establish connection with the sub-element Master devices to get information about
        the support capabilities.

        Returns:
            None
        Raises: 
            DevFailed: when connections to the CspMaster and sub-element Master devices fail.
        """
        try:
            self.dev_logging("Trying connection to {}".format(self.CspMaster), int(tango.LogLevel.LOG_INFO))
            cspMasterProxy = tango.DeviceProxy(self.CspMaster)
            cspMasterProxy.ping()
            # get the list of CSP capabilities to recover the max number of capabilities for each 
            # type
            self._csp_capabilities = cspMasterProxy.maxCapabilities
            # try connection to CbfMaster to get information about the number of
            # capabilities and the receptor/vcc mapping
            if cspMasterProxy.cbfAdminMode in [AdminMode.ONLINE.value, AdminMode.MAINTENANCE.value]:
                self._cbfAddress = cspMasterProxy.cbfMasterAddress
                self._cbfMasterProxy = tango.DeviceProxy(self._cbfAddress)
                self._cbfMasterProxy.ping()
                cbf_capabilities = self._cbfMasterProxy.maxCapabilities
                vcc_to_receptor = self._cbfMasterProxy.vccToReceptor
                self._vcc_to_receptor_map = dict([int(ID) for ID in pair.split(":")] for pair in vcc_to_receptor)
                receptor_to_vcc = self._cbfMasterProxy.receptorToVcc
                self._receptor_to_vcc_map = dict([int(ID) for ID in pair.split(":")] for pair in receptor_to_vcc)
                for i in range(len(cbf_capabilities)):
                    cap_type, cap_num = cbf_capabilities[i].split(':')
                    self._cbf_capabilities[cap_type] = int(cap_num)

            # try connection to PssMaster    
            if cspMasterProxy.pssAdminMode in [AdminMode.ONLINE.value, AdminMode.MAINTENANCE.value]:
                self._pssAddress = cspMasterProxy.pssMasterAddress
                self._pssMasterProxy = tango.DeviceProxy(self._pssAddress)
                self._pssMasterProxy.ping()

            # try connection to PstMaster    
            if cspMasterProxy.pstAdminMode in [AdminMode.ONLINE.value, AdminMode.MAINTENANCE.value]:
                self._pstAddress = cspMasterProxy.pstMasterAddress
                self._pstMasterProxy = tango.DeviceProxy(self._pstAddress)
                self._pstMasterProxy.ping()
        except AttributeError as attr_err:
            msg = "Attribute error:" + str(attr_err)
            self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
        except tango.DevFailed as df:
            tango.Except.throw_exception("Connection Failed", df.args[0].desc,
                                         "connect_to_master ", tango.ErrSeverity.ERR)

    def __is_subarray_available(self, subarray_name):
        """
        *Class private method.*

        Check if the sub-element subarray is exported in the TANGO DB. 
        If the subarray device is not present in the list of the connected subarrays, a 
        connection with the device is performed.

        Args:
            subarray_name : the FQDN of the subarray  
        Returns:
            True if the connection with the subarray is established, False otherwise
        """
        try:
            proxy = self._se_subarrays_proxies[subarray_name]
            proxy.ping()
        except KeyError as key_err: 
            # Raised when a mapping (dictionary) key is not found in the set of existing keys.
            # no proxy registered for the subarray device
            proxy = tango.DeviceProxy(subarray_name)
            proxy.ping()
            self._se_subarrays_proxies[subarray_name] = proxy
        except tango.DevFailed as df:
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
        if self._cbf_subarray_state == tango.DevState.OFF:
           self.set_state(tango.DevState.OFF)
           self._health_state = HealthState.DEGRADED.value   
           return
        if self._cbf_subarray_state == tango.DevState.ON:
           self.set_state(tango.DevState.ON)

        if self._pss_subarray_health_state == HealthState.OK.value and\
           self._pst_subarray_health_state == HealthState.OK.value and\
           self._cbf_subarray_health_state == HealthState.OK.value:
           self._health_state = HealthState.OK.value   
        if self._pss_subarray_state == tango.DevState.OFF or self._pst_subarray_state == tango.DevState.OFF:
           self._health_state = HealthState.DEGRADED.value
        if self._pss_subarray_state == tango.DevState.ON and self._pss_subarray_health_state == HealthState.DEGRADED.value:
           self._health_state = HealthState.DEGRADED.value
        if self._pst_subarray_state == tango.DevState.ON and self._pst_subarray_health_state == HealthState.DEGRADED.value:
           self._health_state = HealthState.DEGRADED.value   

    def __set_subarray_obs_state(self):
        """
        *Class private method*

        Set the subarray obsState attribute value. It works only for IMAGING.
        Args:
            None
        Returns:
            None
        """
        # OSS: when obs_mode is set, its value should be considered to set the final 
        # obs_state of the sub-array
        #if self._cbf_subarray_obs_state == ObsState.READY.value and self._obs_mode == ObsMode.IMAGING.value:
        if self._cbf_subarray_obs_state == ObsState.READY.value :
            self._obs_state = ObsState.READY.value
        #if self._cbf_subarray_obs_state == ObsState.IDLE.value and self._obs_mode == ObsMode.IMAGING.value:
        if self._cbf_subarray_obs_state == ObsState.IDLE.value:
            self._obs_state = ObsState.IDLE.value
            self._obs_mode = ObsMode.IDLE.value

        # analyze only IMAGING mode.
        #TODO: ObsMode should be defined as a mask because we can have more
        # than one obs_mode active for a sub-array


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
        max_dim_x= 1500,
    )
    """
    *Class attribute*

    The list of Search Beam Capability IDs assigned to the subarray.

    *Type*: array of DevUShort
    """

    timingBeams = attribute(
        dtype=('uint16',),
        max_dim_x= 16,
    )
    """
    *Class attribute*

    The list of Timing Beam Capability IDs assigned to the subarray.

    *Type*: array of DevUShort
    """

    vlbiBeams = attribute(
        dtype=('uint16',),
        max_dim_x= 20,
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
        doc="The healthState ttribute value of the Search Beams Capbilities assigned to the subarray.",
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
        See *Common definition* paragraph for corrispondences among Ushort values and healthState labels.

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
        See *Common definition* paragraph for corrispondences among Ushort values and obsState labels.
    """

    receptors = attribute(name ="receptors", label="receptors", forwarded=True
    )
    """
    The list of receptors assigned to the subarray.

    *Forwarded attribute*

    *_root_att*: mid_csp_cbf/sub_elt/subarray_N/receptors
    """

    vccState = attribute(name="vccState", label="vccState",
        forwarded=True
    )
    """
    The State attribute value of the VCCs assigned to the subarray.

    *Forwarded attribute*

    *_root_att*: mid_csp_cbf/sub_elt/subarray_N/reportVCCState
    """

    vccHealthState = attribute(name="vccHealthState", label="vccHealthState",
        forwarded=True
    )
    """
    The healthState attribute value of the VCCs assigned to the subarray.

    *Forwarded attribute*

    *_root_att*: mid_csp_cbf/sub_elt/subarray_N/reportVCChealthState
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
        print("file:", __file__)
        self.set_state(tango.DevState.INIT)
        self._health_state = HealthState.UNKNOWN.value
        self._admin_mode   = AdminMode.ONLINE.value
        # NOTE: need to adjust SKAObsDevice class because some of its
        # attributes (such as obs_state, obs_mode nad command_progress) are not 
        # visibile from the derived classes!!
        self._obs_mode     = ObsMode.IDLE.value
        self._obs_state    = ObsState.IDLE.value
        # get subarray ID
        if self.SubID:
            self._subarray_id = int(self.SubID)
        else:
            self._subarray_id = int(self.get_name()[-2:])  # last two chars of FQDN
        # sub-element Subarray State and healthState initialization
        self._cbf_subarray_state        = tango.DevState.UNKNOWN
        self._cbf_subarray_health_state = HealthState.UNKNOWN.value
        self._cbf_subarray_obs_state    = ObsState.IDLE.value   
        self._pss_subarray_state        = tango.DevState.UNKNOWN
        self._pss_subarray_health_state = HealthState.UNKNOWN.value
        self._pss_subarray_obs_state    = ObsState.IDLE.value   
        self._pst_subarray_state        = tango.DevState.UNKNOWN
        self._pst_subarray_health_state = HealthState.UNKNOWN.value
        self._pst_subarray_obs_state    = ObsState.IDLE.value   

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
        self._vcc_to_receptor_map = {}
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
        self._command_cb = self.CommandCallBack()

        # build the sub-element sub-array FQDNs
        if self._subarray_id < 10:
            self._cbf_subarray_fqdn = self.CbfSubarrayPrefix + "0" + str(self._subarray_id)
            self._pss_subarray_fqdn = self.PssSubarrayPrefix + "0" + str(self._subarray_id)
        else:    
            self._cbf_subarray_fqdn = self.CbfSubarrayPrefix + "0" + str(self._subarray_id)
            self._pss_subarray_fqdn = self.PssSubarrayPrefix + "0" + str(self._subarray_id)

        try:
            self.__connect_to_master()
            self.__connect_to_subarrays()
        except tango.DevFailed as df:    
            for item in df.args:
                log_msg = "Error in {}: {}". format(item.origin, item.reason)
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
        pass
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
        pass
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
            receptors = self._se_subarrays_proxies[self._cbf_subarray_fqdn].receptors
            if receptors:
                for receptor_id in list_of_receptors: 
                    vcc_id = self._receptor_to_vcc_map[receptor_id]
                    self._vcc.append(vcc_id) 
        except KeyError as key_err:
            msg ="No {} found".format(key_err)
            tango.Except.re_throw_exception("Read attribute failure", msg,
                                            "read_vcc", tango.ErrSeverity.ERR)
        except tango.DevFailed as df:
            tango.Except.re_throw_exception("Read attribute failure", df.args[0].desc,
                                            "read_vcc", tango.ErrSeverity.ERR)
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

    @command(
    )
    @DebugIt()
    def EndScan(self):
        """
        *Class method*
        End the execution of a running scan.

        Raises:
            tango.DevFailed: if the subarray *obsState* is not SCANNING or if an exception is caught\
                    during the command execution.
        """
        # PROTECTED REGION ID(CspSubarray.EndScan) ENABLED START #
        # Check if the EndScan command can be executed. This command is allowed when the 
        # Subarray State is SCANNING.
        if self._obs_state != ObsState.SCANNING.value:
            #get the obs_state label
            for obs_state in ObsState:
                if obs_state == self._obs_state:
                    break
            log_msg = "Subarray obs_state is {}, not SCANNING".format(obs_state.name)
            tango.Except.throw_exception("Command failed", log_msg,
                                         "EndScan", tango.ErrSeverity.ERR)
        proxy = 0
        #TODO: the command is forwarded only to CBF. Future implementation has to
        # check the observing mode and depending on this, the command is forwarded to
        # the interested sub-elements.
        if self.__is_subarray_available(self._cbf_subarray_fqdn):
            try:     
                proxy = self._se_subarrays_proxies[self._cbf_subarray_fqdn]
                # forward asynchrnously the command to the CbfSubarray
                proxy.command_inout_asynch("EndScan", self._command_cb)
            except tango.DevFailed as df:
                for item in df.args:
                    log_msg = item.desc
                    self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
                    tango.Except.re_throw_exception(df, "Command failed", 
                                             "CspSubarray EndScan command failed", 
                                             "Command()",
                                             tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CspSubarray.EndScan

    @command(
    dtype_in=('str',), 
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
            #get the obs_state label
            for obs_state in ObsState:
                if obs_state == self._obs_state:
                    break
            log_msg = "Subarray is in {} state, not READY".format(obs_state.name)
            tango.Except.throw_exception("Command failed", log_msg,
                                         "Scan", tango.ErrSeverity.ERR)
        proxy = 0
        if self.__is_subarray_available(self._cbf_subarray_fqdn):
            try:     
                proxy = self._se_subarrays_proxies[self._cbf_subarray_fqdn]
                # forward the command to the CbfSubarray asynchrnously
                proxy.command_inout_asynch("Scan", argin, self._command_cb)
                self._obs_state = ObsState.SCANNING.value
            except tango.DevFailed as df:
                for item in df.args:
                    log_msg = item.desc
                    self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
                    tango.Except.re_throw_exception(df, "Command failed", 
                                             "CspSubarray Scan command failed", 
                                             "Command()",
                                             tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CspSubarray.Scan

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
        # the list with subarray affiliation of each receptor
        # OSS: num_of_vcc is the max number of VCCs instantiate for this element. 
        # So it may be num_of_vcc < 197. The vcc_id of the 
        # instantiated VCC capabilities are ALWAYS assigned starting from 1 up to 
        # num_of_vcc. Each vcc_id map to a vcc_fqdn inside CbfMaster, for example 
        # we can have the following situation:
        # vcc_id = 1 -> mid_csp_cbf/vcc/vcc_005
        # vcc_id = 2 -> mid_csp_cbf/vcc/vcc_011
        # .....
        # vcc_id = 17 -> mid_csp_cbf/vcc/vcc_191

        #Check if the AddReceptors command can be executed. Receptors can be assigned to a subarray
        #only when its obsState is IDLE or READY. 
        if self._obs_state not in [ObsState.IDLE.value, ObsState.READY.value]:
            #get the obs_state label
            for obs_state in ObsState:
                if obs_state == self._obs_state:
                    break
            log_msg = "Subarray obs_state is {}, not IDLE or READY".format(obs_state.name)
            tango.Except.throw_exception("Command failed", log_msg,
                                         "AddReceptors", tango.ErrSeverity.ERR)
        try:
            num_of_vcc = self._cbf_capabilities["VCC"]
            receptor_membership = [0] * num_of_vcc
            # the list of receptor to assign to the subarray
            receptor_to_assign = []
            # connect to CbfMaster to get the list of all VCCs affilitiation and build 
            # the corresponding receptorId affiliation list
            if not self._cbfMasterProxy:
                self._cbfMasterProxy = tango.DeviceProxy(self._cbfAddress)
            # check if device is connected
            self._cbfMasterProxy.ping()
            vcc_membership = self._cbfMasterProxy.reportVCCSubarrayMembership
            # TODO: get the  list of available receptors
            # available_receptors = cspMasterProxy.availableReceptorIDs
            # vccID range is [1, 197]!!
            # vcc_id range is [0,196]!!
            for vcc_id in range(num_of_vcc):
                # get the associated receptor ID: this value can be any value in 
                # the range [1,197]!!
                receptorID = self._vcc_to_receptor_map[vcc_id + 1]
                receptor_membership[receptorID - 1] = vcc_membership[vcc_id]
        except KeyError as key_err:
            log_msg = "Can't access to CbfMaster {} information".format(str(key_err))
            self.dev_logging(str(key_err), tango.LogLevel.LOG_ERROR)
            if not self._cbf_capabilities :
                tango.Except.throw_exception("Command failed", log_msg,
                                             "AddReceptors", tango.ErrSeverity.ERR)
        except tango.DevFailed as df:
            for item in df.args:
                if "Failed to connect to device" in item.desc:
                    self._cbfMasterProxy = 0
            tango.Except.throw_exception("Command failed", df.args[0].desc,
                                         "AddReceptors", tango.ErrSeverity.ERR)
        for receptorId in argin:
            # check if the specified recetorID is valid, that is a number
            # in the range [1-197]
            # TODO if receptorId in available_receptors:
            if receptorId in range(1, const.NUM_OF_RECEPTORS + 1):
                # check if the required receptor is already assigned
                if receptor_membership[receptorId - 1] in list(range(1,17)):
                    sub_id = receptor_membership[receptorId - 1]
                    log_msg = "Receptor " + str(receptorId) + \
                              " already assigned to subarray " + str(sub_id)
                    self.dev_logging(log_msg, tango.LogLevel.LOG_WARN)
                else :
                    receptor_to_assign.append(receptorId)
            else:
                log_msg = "Receptor " + str(receptorId) + " invalid value"
                self.dev_logging(log_msg, tango.LogLevel.LOG_WARN)

        # check if the list of receptors to assign is empty
        if not receptor_to_assign: 
            log_msg = "The required receptors are already assigned to the subarray"
            self.dev_logging(log_msg, tango.LogLevel.LOG_INFO)
            return  
        # check if the CspSubarray is already connected to the CbfSubarray
        proxy = 0
        if self.__is_subarray_available(self._cbf_subarray_fqdn):
            try:     
                proxy = self._se_subarrays_proxies[self._cbf_subarray_fqdn]
                # forward the command to the CbfSubarray
                proxy.command_inout("AddReceptors", receptor_to_assign)
            except tango.DevFailed as df:
                for item in df.args:
                    log_msg = item.desc
                    self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
                    tango.Except.re_throw_exception(df, "Command failed", 
                                             "CspSubarray AddReceptors command failed", 
                                             "Command()",
                                             tango.ErrSeverity.ERR)
            except TypeError as err:
                # Raised when an operation or function is applied to an object of inappropriate type. 
                # The associated value is a string giving details about the type mismatch.
                log_msg =  "TypeError: " + str(err)
                self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
                tango.Except.throw_exception("Command failed", log_msg,
                                             "AddReceptors", tango.ErrSeverity.ERR)
        else:
            log_msg = "Subarray " + str(self._cbf_subarray_fqdn) + " not registered!"
            self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
            tango.Except.throw_exception("Command failed", log_msg,
                                         "AddReceptors", tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CspSubarray.AddReceptors

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
            tango.DevFailed: raised if the subarray *obState* attribute is not IDLE or READY, or \
                    when an exception is caught during command execution.
        """
        # PROTECTED REGION ID(CspSubarray.RemoveReceptors) ENABLED START #

        # Check if the RemoveReceptors command can be executed. Receptors can be removed from a subarray
        # only when its obsState is IDLE or READY. 
        if self._obs_state not in [ObsState.IDLE.value, ObsState.READY.value]:
            #get the obs_state label
            for obs_state in ObsState:
                if obs_state == self._obs_state:
                    break
            log_msg = "Subarray obs_state is {}, not IDLE or READY".format(obs_state.name)
            tango.Except.throw_exception("Command failed", log_msg,
                                         "RemoveReceptors", tango.ErrSeverity.ERR)

        # check if the CspSubarray is already connected to the CbfSubarray
        proxy = 0
        if self.__is_subarray_available(self._cbf_subarray_fqdn):
            try:
                proxy = self._se_subarrays_proxies[self._cbf_subarray_fqdn]
                # read fron Cbfubarray the list of assigned receptors
                receptors = proxy.receptors
                # check if the list of assigned receptors is empty.
                if not receptors:
                    self.dev_logging("RemoveReceptors: no receptor to remove", tango.LogLevel.LOG_INFO)
                    return
                receptors_to_remove = []
                # check if the receptors to remove belong to the subarray
                for receptor_id in argin:
                    if receptor_id in receptors:
                        receptors_to_remove.append(receptor_id)
                # forward the command to CbfSubarray
                proxy.RemoveReceptors(receptors_to_remove)
            except tango.DevFailed as df:
                log_msg = "RemoveReceptors:" + df.args[0].desc
                self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
                tango.Except.re_throw_exception(df, "Command failed", 
                        "CspSubarray RemoveReceptors command failed", 
                        "Command()", tango.ErrSeverity.ERR)
        else:
            log_msg = "Subarray " + str(self._cbf_subarray_fqdn) + " not registered!"
            self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
            tango.Except.throw_exception("Command failed", log_msg,
                                         "RemoveReceptors", tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CspSubarray.RemoveReceptors

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

        # Check if the RemoveAllReceptors command can be executed. Receptors can be removed from a subarray
        # only when its obsState is IDLE or READY. 
        if self._obs_state not in [ObsState.IDLE.value, ObsState.READY.value]:
            #get the obs_state label
            for obs_state in ObsState:
                if obs_state == self._obs_state:
                    break
            log_msg = "Subarray obs_state is {}, not IDLE or READY".format(obs_state.name)
            tango.Except.throw_exception("Command failed", log_msg,
                                         "RemoveAllReceptors", tango.ErrSeverity.ERR)
        proxy = 0
        if self.__is_subarray_available(self._cbf_subarray_fqdn):
            try:
                proxy = self._se_subarrays_proxies[self._cbf_subarray_fqdn]
                # check if the list of assigned receptors is empty
                receptors = proxy.receptors
                if not receptors:
                    self.dev_logging("RemoveReceptors: no receptor to remove", tango.LogLevel.LOG_INFO)
                    return
                # forward the command to the CbfSubarray
                proxy.command_inout("RemoveAllReceptors")
                #self._vcc = []
            except tango.DevFailed as df:
                log_msg = "RemoveAllReceptors:" + df.args[0].desc
                self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
                tango.Except.re_throw_exception(df, "Command failed", 
                        "CspSubarray RemoveAllReceptors command failed", 
                        "Command()", tango.ErrSeverity.ERR)
        else:
            log_msg = "Subarray " + str(self._cbf_subarray_fqdn) + " not registered!"
            self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
            tango.Except.throw_exception("Command failed", log_msg,
                                         "RemoveAllReceptors", tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CspSubarray.RemoveAllReceptors

    def is_ConfigureScan_allowed(self):
        """
        *TANGO is_allowed method*: filter the external request depending on the current device state.\n
        Check if the ConfigureScan method can be issued on the subarray.\n
        A scan configuration can be performed when the subarray *State* is ON (that is, \
        at least one receptor is assigned to it)

        Returns:
            True if the command can be executed, otherwise False
        """
        #TODO: checks other states?
        if self.get_state() in [tango.DevState.OFF]:
            return False
        return True

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
            for obs_state in ObsState:
                if obs_state == self._obs_state:
                    break
            log_msg = "Subarray is in {} state, not IDLE or READY".format(obs_state.name)
            tango.Except.throw_exception("Command failed", log_msg,
                                         "Scan", tango.ErrSeverity.ERR)
        # check connection with CbfSubarray
        if not self.__is_subarray_available(self._cbf_subarray_fqdn):
            log_msg = "Subarray " + str(self._cbf_subarray_fqdn) + " not registered!"
            self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
            tango.Except.throw_exception("Command failed", log_msg,
                                         "ConfigureScan execution", tango.ErrSeverity.ERR)
        # the dictionary with the scan configuration
        argin_dict = {}
        try:
            # for test purpose we load the json configuration from an
            # external file.
            # TO REMOVE!!
            if (argin == "load"):
                filename = os.path.join(commons_pkg_path, "test_ConfigureScan_basic.json")
                with open(filename) as json_file:
                    #load the file into a dictionary
                    argin_dict = json.load(json_file)
                    #dump the dictionary into the input string to forward to CbfSubarray
                    argin = json.dumps(argin_dict)
            else:        
                argin_dict = json.loads(argin)
        except FileNotFoundError as file_err:
            log_msg= "File not found"
            self.dev_logging(str(file_err), tango.LogLevel.LOG_ERROR)
            tango.Except.throw_exception("Command failed", str(file_err),
                                         "ConfigureScan execution", tango.ErrSeverity.ERR)
        except json.JSONDecodeError as e:  # argument not a valid JSON object
            # this is a fatal error
            msg = "Scan configuration object is not a valid JSON object. Aborting configuration."
            self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
            tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                           tango.ErrSeverity.ERR)
        # Validate scanID.
        # If not given, abort the scan configuration.
        # If malformed, abort the scan configuration.
        if "scanID" in argin_dict:
            if int(argin_dict["scanID"]) <= 0:  # scanID not positive
                msg = "'scanID' must be positive (received {}). "\
                    "Aborting configuration.".format(int(argin_dict["scanID"]))
                # this is a fatal error
                self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
                tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                               tango.ErrSeverity.ERR)
            #TODO: add on CspMaster the an attribute with the list of scanID 
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
            tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
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
                msg = "'frequencyBand' must be one of {} (received {}). "\
                    "Aborting configuration.".format(frequency_bands, argin_dict["frequencyBand"])
                # this is a fatal error
                self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
                tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                               tango.ErrSeverity.ERR)
        else:  # frequencyBand not given
            msg = "'frequencyBand' must be given. Aborting configuration."
            # this is a fatal error
            self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
            tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
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
                    msg = "'band5Tuning' must be an array of length 2. Aborting configuration."
                    # this is a fatal error
                    self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
                    tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                   tango.ErrSeverity.ERR)

                stream_tuning = [*map(float, argin_dict["band5Tuning"])]
                if frequency_band == 4:
                    if not all([5.85 <= stream_tuning[i] <= 7.25 for i in [0, 1]]):
                        msg = "Elements in 'band5Tuning must be floats between 5.85 and 7.25 "\
                            "(received {} and {}) for a 'frequencyBand' of 5a. "\
                            "Aborting configuration.".format(stream_tuning[0], stream_tuning[1])
                        # this is a fatal error
                        self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
                        tango.Except.throw_exception("Command failed", msg,
                                                       "ConfigureScan execution",
                                                       tango.ErrSeverity.ERR)
                else:  # self._frequency_band == 5
                    if not all([9.55 <= stream_tuning[i] <= 14.05 for i in [0, 1]]):
                        msg = "Elements in 'band5Tuning must be floats between 9.55 and 14.05 "\
                            "(received {} and {}) for a 'frequencyBand' of 5b. "\
                            "Aborting configuration.".format(stream_tuning[0], stream_tuning[1])
                        # this is a fatal error
                        self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
                        tango.Except.throw_exception("Command failed", msg,
                                                       "ConfigureScan execution",
                                                       tango.ErrSeverity.ERR)
            else:
                msg = "'band5Tuning' must be given for a 'frequencyBand' of {}. "\
                    "Aborting configuration".format(["5a", "5b"][frequency_band - 4])
                # this is a fatal error
                self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
                tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                               tango.ErrSeverity.ERR)

        # Forward the ConfigureScan command to CbfSubarray.
        try:
            proxy = self._se_subarrays_proxies[self._cbf_subarray_fqdn]
            proxy.ping()
            self._obs_state = ObsState.CONFIGURING.value
            proxy.command_inout("ConfigureScan", argin) 
            self._obs_mode = proxy.obsMode
            self._valid_scan_configuration = argin
        except tango.DevFailed as df:
            log_msg = ''
            for item in df.args:
                log_msg += item.reason + " " + item.desc
            self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
            tango.Except.re_throw_exception(df, "Command failed", 
                    "CspSubarray ConfigureScan command failed", 
                    "Command()", tango.ErrSeverity.ERR)
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
        pass
        # PROTECTED REGION END #    //  CspSubarray.AddSearchBeams

    @command(
    dtype_in='uint16', 
    doc_in="The number of SearchBeam Capabilities to remove from the sub-arrays.\nAll the search beams are removed from the sub-array if the input number \nis equal to the max number of search bem capabilities (1500 for MID)", 
    )
    @DebugIt()
    def RemoveNumOfSearchBeams(self, argin):
        """
        Note: 
            Still to be implemented
        *Class method*

        Remove the specified number of Search Beams capabilities from the subarray.
        
        Args:
            argin: The number of SearchBeams Capabilities to remove from the subarray. If equal\
            to the max number of search bem capabilities (1500 for MID), all the search beams are removed.
        Returns:
            None
        """
        # PROTECTED REGION ID(CspSubarray.RemoveSearchBeams) ENABLED START #
        pass
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
        pass
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
        pass
        # PROTECTED REGION END #    //  CspSubarray.AddVlbiBeams

    @command(
    dtype_in=('uint16',), 
    doc_in="The list of Search Beam Capabilities ID to assign to the sub-array.", 
    )
    @DebugIt()
    def AddSearchBeamsID(self, argin):
        """
        Note: 
            Still to be implemented
        *Class method*

        Add the specified Search Beams Capability IDs to the subarray.
        This method requires some knowledge of the internal behavior of the PSS machine,\
        because Seach Beam capabilities with PSS pipelines belonging to the same PSS node,\ 
        can't be assigned to different subarrays.

        Args:
            argin: The list of Search Beams Capability IDs to assign to the subarray.
            Type: array of DevUShort
        Returns:
            None
        References:
            AddNumOfSearchBeams
        """
        # PROTECTED REGION ID(CspSubarray.AddSearchBeamsID) ENABLED START #
        pass
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
        pass
        # PROTECTED REGION END #    //  CspSubarray.RemoveSearchBeamsID

    @command(
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
        pass
        # PROTECTED REGION END #    //  CspSubarray.RemoveTimingBeams

    @command(
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
        pass
        # PROTECTED REGION END #    //  CspSubarray.RemoveVlbiBeams

# ----------
# Run server
# ----------

def main(args=None, **kwargs):
    # PROTECTED REGION ID(CspSubarray.main) ENABLED START #
    return run((CspSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CspSubarray.main

if __name__ == '__main__':
    main()
