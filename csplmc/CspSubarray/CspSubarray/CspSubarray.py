# -*- coding: utf-8 -*-
#
# This file is part of the CspSubarray project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" CspSubarray prototype

CspSubarray TANGO Device Class
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
from tango.server import run, DeviceMeta, attribute, command, device_property

# add the path to import global_enum package.
file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

# Additional import
# PROTECTED REGION ID(CspMaster.additionnal_import) ENABLED START #
#
import global_enum as const
from global_enum import HealthState, AdminMode, ObsState, ObsMode
from skabase.  SKASubarray import SKASubarray
import json
# PROTECTED REGION END #    //  CspMaster.additionnal_import

__all__ = ["CspSubarray", "main"]

class CspSubarray(with_metaclass(DeviceMeta, SKASubarray)):
    """
    CspSubarray TANGO Device Class
    """
    # PROTECTED REGION ID(CspSubarray.class_variable) ENABLED START #

    # ---------------
    # Event Callback functions
    # ---------------
    def cmd_done_cb(self):
        self.dev_logging("Asynch command accepted!", tango.LogLevel.LOG_INFO)

    def scm_change_callback(self, evt):
        """
        Class private method.
        Retrieve the values of the sub-element sub-arrays SCM attributes subscribed for change
        event at device initialization.

        :param evt: The event data

        :return: None
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
                    self.dev_logging("Attribute {} not still handled".format(evt.attr_name), 
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
        Class private method.
        Establish connection with each sub-element sub-array.
        If connection succeeds, the CspSubarrays device subscribes the State, healthState 
        and adminMode attributes of each Sub-element sub-array and registers a callback function
        to handle the events.
        Exceptions are logged.
        Args:
            None
        Returns:
            None
        """
        for fqdn in self._se_subarrays_fqdn:
            # initialize the list for each dictionary key-name
            self._se_subarray_event_id[fqdn] = []
            try:
                log_msg = "Trying connection to" + str(fqdn) + " device"
                self.dev_logging(log_msg, int(tango.LogLevel.LOG_INFO))
                device_proxy = DeviceProxy(fqdn)
                device_proxy.ping()
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
        Class private method.
        Establish connection with the CSP sub-element master to get information about:
        - the CBF Master address
        - the max number of CSP and CBF capabilities for each type
        Args:
            None
        Returns:
            None
        Raises: 
            Raise a DevFailed exception if connections fail.
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
                self._se_subarrays_fqdn.append(self._cbf_subarray_fqdn)

            # try connection to PssMaster    
            if cspMasterProxy.pssAdminMode in [AdminMode.ONLINE.value, AdminMode.MAINTENANCE.value]:
                self._pssAddress = cspMasterProxy.pssMasterAddress
                self._pssMasterProxy = tango.DeviceProxy(self._pssAddress)
                self._pssMasterProxy.ping()
                self._se_subarrays_fqdn.append(self._pss_subarray_fqdn)

            # try connection to PstMaster    
            if cspMasterProxy.pstAdminMode in [AdminMode.ONLINE.value, AdminMode.MAINTENANCE.value]:
                self._pstAddress = cspMasterProxy.pstMasterAddress
                self._pstMasterProxy = tango.DeviceProxy(self._pstAddress)
                self._pstMasterProxy.ping()
        except tango.DevFailed as df:
            tango.Except.throw_exception("Connection Failed", df.args[0].desc,
                                         "connect_to_master ", tango.ErrSeverity.ERR)

    def __is_subarray_available(self, subarray_name):
        """
        Class private method.
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
        Class private method.
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
        Class private method.
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
    # Device Properties
    # -----------------
    CspMaster = device_property(
        dtype='str', default_value="mid_csp/elt/master"
    )

    CbfSubarrayPrefix = device_property(
        dtype='str', default_value="mid_csp_cbf/sub_elt/subarray_"
    )

    PssSubarrayPrefix = device_property(
        dtype='str', default_value="mid_csp_pss/sub_elt/subarray_"
    )

    # ----------
    # Attributes
    # ----------

    scanID = attribute(
        dtype='uint64',
        access=AttrWriteType.READ_WRITE,
    )

    corrInherentCap = attribute(
        dtype='str',
    )

    pssInherentCap = attribute(
        dtype='str',
    )

    pstInherentCap = attribute(
        dtype='str',
    )

    vlbiInherentCap = attribute(
        dtype='str',
    )

    cbfSubarrayState = attribute(
        dtype='DevState',
    )

    pssSubarrayState = attribute(
        dtype='DevState',
    )

    cbfSubarrayHealthState = attribute(
        dtype='DevEnum',
        label="CBF Subarray Health State",
        doc="CBF Subarray Health State",
        enum_labels=["OK", "DEGRADED", "FAILED", "UNKNOWN", ],
    )

    pssSubarrayHealthState = attribute(
        dtype='DevEnum',
        label="PSS Subarray Health State",
        doc="PSS Subarray Health State",
        enum_labels=["OK", "DEGRADED", "FAILED", "UNKNOWN", ],
    )

    cbfSubarrayObsState = attribute(
        dtype='DevEnum',
        label="CBF Subarray Observing State",
        doc="The CBF subarray observing state.",
        enum_labels=["IDLE", "CONFIGURING", "READY", "SCANNING", "PAUSED", "ABORTED", "FAULT", ],
    )

    pssSubarrayObsState = attribute(
        dtype='DevEnum',
        label="PSS Subarray Observing State",
        doc="The PSS subarray observing state.",
        enum_labels=["IDLE", "CONFIGURING", "READY", "SCANNING", "PAUSED", "ABORTED", "FAULT", ],
    )

    pssSubarrayAddr = attribute(
        dtype='str',
        doc="The PSS Subarray TANGO address.",
    )

    cbfSubarrayAddr = attribute(
        dtype='str',
        doc="The CBF Subarray TANGO address.",
    )

    validScanConfiguration = attribute(
        dtype='str',
        label="Valid Scan Configuration",
        doc="Store the last valid scan configuration.",
    )

    receptors = attribute(
        dtype=('uint',),
        max_dim_x=197,
        label="Receptor IDs",
        doc="The list of receptor IDs assigned to the subarray.",
    )

    fsp = attribute(
        dtype=('uint16',),
        max_dim_x=27,
    )

    vcc = attribute(
        dtype=('uint16',),
        max_dim_x=197,
    )

    searchBeams = attribute(
        dtype=('uint16',),
        max_dim_x= 1500,
    )

    timingBeams = attribute(
        dtype=('uint16',),
        max_dim_x= 16,
    )

    vlbiBeams = attribute(
        dtype=('uint16',),
        max_dim_x= 20,
    )

    searchBeamsState = attribute(
        dtype=('DevState',),
        max_dim_x=1500,
    )

    timingBeamsState = attribute(
        dtype=('DevState',),
        max_dim_x=16,
    )

    vlbiBeamsState = attribute(
        dtype=('DevState',),
        max_dim_x=20,
    )

    searchBeamsHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=1500,
    )

    timingBeamsHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=16,
    )

    vlbiBeamsHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=20,
    )

    timingBeamsObsState = attribute(
        dtype=('uint16',),
        max_dim_x=16,
        label="Timing Beams obsState",
        doc="The observation state of assigned timing beams.",
    )
    vccState = attribute(name="vccState", label="vccState",
        forwarded=True
    )
    vccHealthState = attribute(name="vccHealthState", label="vccHealthState",
        forwarded=True
    )
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
        SKASubarray.init_device(self)
        # PROTECTED REGION ID(CspSubarray.init_device) ENABLED START #
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
        self._receptors = []        # list of receptors  assigned to subarray
        self._fsp = []              # list of FSPs assigned to subarray`

        self._cbf_subarray_fqdn = ''
        self._pss_subarray_fqdn = ''
        # build the sub-element sub-array fqdn
        if self._subarray_id < 10:
            self._cbf_subarray_fqdn = self.CbfSubarrayPrefix + "0" + str(self._subarray_id)
            self._pss_subarray_fqdn = self.PssSubarrayPrefix + "0" + str(self._subarray_id)
        else:    
            self._cbf_subarray_fqdn = self.CbfSubarrayPrefix + "0" + str(self._subarray_id)
            self._pss_subarray_fqdn = self.PssSubarrayPrefix + "0" + str(self._subarray_id)

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
        try:
            self.__connect_to_master()
            self.__connect_to_subarrays()
            self._receptors = self._se_subarrays_proxies[self._cbf_subarray_fqdn].receptors
            #TODO: read also the vcc!!
            if not self._receptors:
                self.dev_logging("No receptor assigned to the subarray", tango.LogLevel.LOG_INFO)
            else:
                self.dev_logging("{} assigned to the subarray".format(self._receptors), tango.LogLevel.LOG_INFO)
                for receptorId in self._receptors:
                    vcc_id = self._receptor_to_vcc_map[receptorId]
                    self._vcc.append(vcc_id)
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
        # PROTECTED REGION ID(CspSubarray.scanID_read) ENABLED START #
        return self._scan_ID 
        # PROTECTED REGION END #    //  CspSubarray.scanID_read

    def write_scanID(self, value):
        # PROTECTED REGION ID(CspSubarray.scanID_write) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CspSubarray.scanID_write

    def read_corrInherentCap(self):
        # PROTECTED REGION ID(CspSubarray.corrInherentCap_read) ENABLED START #
        return ''
        # PROTECTED REGION END #    //  CspSubarray.corrInherentCap_read

    def read_pssInherentCap(self):
        # PROTECTED REGION ID(CspSubarray.pssInherentCap_read) ENABLED START #
        return ''
        # PROTECTED REGION END #    //  CspSubarray.pssInherentCap_read

    def read_pstInherentCap(self):
        # PROTECTED REGION ID(CspSubarray.pstInherentCap_read) ENABLED START #
        return ''
        # PROTECTED REGION END #    //  CspSubarray.pstInherentCap_read

    def read_vlbiInherentCap(self):
        # PROTECTED REGION ID(CspSubarray.vlbiInherentCap_read) ENABLED START #
        return ''
        # PROTECTED REGION END #    //  CspSubarray.vlbiInherentCap_read

    def read_cbfSubarrayState(self):
        # PROTECTED REGION ID(CspSubarray.cbfSubarrayState_read) ENABLED START #
        return self._cbf_subarray_state
        # PROTECTED REGION END #    //  CspSubarray.cbfSubarrayState_read

    def read_pssSubarrayState(self):
        # PROTECTED REGION ID(CspSubarray.pssSubarrayState_read) ENABLED START #
        return self._pss_subarray_state
        # PROTECTED REGION END #    //  CspSubarray.pssSubarrayState_read

    def read_cbfSubarrayHealthState(self):
        # PROTECTED REGION ID(CspSubarray.cbfSubarrayHealthState_read) ENABLED START #
        return self._cbf_subarray_health_state
        # PROTECTED REGION END #    //  CspSubarray.cbfSubarrayHealthState_read

    def read_pssSubarrayHealthState(self):
        # PROTECTED REGION ID(CspSubarray.pssSubarrayHealthState_read) ENABLED START #
        return self._pss_subarray_health_state
        # PROTECTED REGION END #    //  CspSubarray.pssSubarrayHealthState_read

    def read_cbfSubarrayObsState(self):
        # PROTECTED REGION ID(CspSubarray.cbfSubarrayObsState_read) ENABLED START #
        return self._cbf_subarray_obs_state
        # PROTECTED REGION END #    //  CspSubarray.cbfSubarrayObsState_read

    def read_pssSubarrayObsState(self):
        # PROTECTED REGION ID(CspSubarray.pssSubarrayObsState_read) ENABLED START #
        return self._pss_subarray_obs_state
        # PROTECTED REGION END #    //  CspSubarray.pssSubarrayObsState_read

    def read_pssSubarrayAddr(self):
        # PROTECTED REGION ID(CspSubarray.pssSubarrayAddr_read) ENABLED START #
        return self._pss_subarray_fqdn
        # PROTECTED REGION END #    //  CspSubarray.pssSubarrayAddr_read

    def read_cbfSubarrayAddr(self):
        # PROTECTED REGION ID(CspSubarray.cbfSubarrayAddr_read) ENABLED START #
        return self._cbf_subarray_fqdn
        # PROTECTED REGION END #    //  CspSubarray.cbfSubarrayAddr_read

    def read_validScanConfiguration(self):
        # PROTECTED REGION ID(CspSubarray.validScanConfiguration_read) ENABLED START #
        return self._valid_scan_configuration
        # PROTECTED REGION END #    //  CspSubarray.validScanConfiguration_read

    def read_receptors(self):
        # PROTECTED REGION ID(CspSubarray.receptors_read) ENABLED START #
        return self._receptors
        # PROTECTED REGION END #    //  CspSubarray.receptors_read

    def read_fsp(self):
        # PROTECTED REGION ID(CspSubarray.fsp_read) ENABLED START #
        return self._fsp
        # PROTECTED REGION END #    //  CspSubarray.fsp_read

    def read_vcc(self):
        # PROTECTED REGION ID(CspSubarray.vcc_read) ENABLED START #
        return self._vcc
        # PROTECTED REGION END #    //  CspSubarray.vcc_read

    def read_searchBeams(self):
        # PROTECTED REGION ID(CspSubarray.vcc_read) ENABLED START #
        return self._search_beams
        # PROTECTED REGION END #    //  CspSubarray.vcc_read

    def read_timingBeams(self):
        # PROTECTED REGION ID(CspSubarray.vcc_read) ENABLED START #
        return self._timing_beams
        # PROTECTED REGION END #    //  CspSubarray.vcc_read

    def read_vlbiBeams(self):
        # PROTECTED REGION ID(CspSubarray.vcc_read) ENABLED START #
        return self._vlbi_beams
        # PROTECTED REGION END #    //  CspSubarray.vcc_read

    def read_searchBeamsState(self):
        # PROTECTED REGION ID(CspSubarray.searchBeamsState_read) ENABLED START #
        return [tango.DevState.UNKNOWN]
        # PROTECTED REGION END #    //  CspSubarray.searchBeamsState_read

    def read_timingBeamsState(self):
        # PROTECTED REGION ID(CspSubarray.timingBeamsState_read) ENABLED START #
        return [tango.DevState.UNKNOWN]
        # PROTECTED REGION END #    //  CspSubarray.timingBeamsState_read

    def read_vlbiBeamsState(self):
        # PROTECTED REGION ID(CspSubarray.vlbiBeamsState_read) ENABLED START #
        return [tango.DevState.UNKNOWN]
        # PROTECTED REGION END #    //  CspSubarray.vlbiBeamsState_read

    def read_searchBeamsHealthState(self):
        # PROTECTED REGION ID(CspSubarray.searchBeamsHealthState_read) ENABLED START #
        return [0]
        # PROTECTED REGION END #    //  CspSubarray.searchBeamsHealthState_read

    def read_timingBeamsHealthState(self):
        # PROTECTED REGION ID(CspSubarray.timingBeamsHealthState_read) ENABLED START #
        return [0]
        # PROTECTED REGION END #    //  CspSubarray.timingBeamsHealthState_read

    def read_vlbiBeamsHealthState(self):
        # PROTECTED REGION ID(CspSubarray.vlbiBeamsHealthState_read) ENABLED START #
        return [0]
        # PROTECTED REGION END #    //  CspSubarray.vlbiBeamsHealthState_read

    def read_timingBeamsObsState(self):
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
                # forward the command to the CbfSubarray
                proxy.command_inout_asynch("EndScan", self.cmd_done_cb)
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
                # forward the command to the CbfSubarray
                proxy.command_inout_asynch("Scan", argin, self.cmd_done_cb)
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

    def is_AddReceptors_allowed(self):
        """
        Check if the AddReceptors command can be executed. Receptors can be assigned to a subarray
        only when its obsState is IDLE or READY. 

        Returns:
            True if the command can be executed, otherwise False
        """
        if self._obs_state not in [ObsState.IDLE.value, ObsState.READY.value]:
            return False
        return True

    @command(
    dtype_in=('uint16',), 
    doc_in="List of the receptor IDs to add to the subarray.", 
    )
    @DebugIt()
    def AddReceptors(self, argin):
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

        num_of_vcc = self._cbf_capabilities["VCC"]
        receptor_membership = [0] * num_of_vcc
        # the list of receptor to assign to the subarray
        receptor_to_assign = []
        # get the list of all VCCs affilitiation and build the corresponding
        # receptorId affiliation list
        try:
            if not self._cbfMasterProxy:
                self._cbfMasterProxy = tango.DeviceProxy(self._cbfAddress)
            # check if device is connected
            self._cbfMasterProxy.ping()
            vcc_membership = self._cbfMasterProxy.reportVCCSubarrayMembership
            # vccID range is [1, 197]!!
            # vcc_id range is [0,196]!!
            for vcc_id in range(num_of_vcc):
                # get the associated receptor ID: this value can be any value in 
                # the range [1,197]!!
                receptorID = self._vcc_to_receptor_map[vcc_id + 1]
                receptor_membership[receptorID - 1] = vcc_membership[vcc_id]
        except tango.DevFailed as df:
            for item in df.args:
                if "Failed to connect to device" in item.desc:
                    self._cbfMasterProxy = 0
            tango.Except.throw_exception("Command failed", df.args[0].desc,
                                         "AddReceptors", tango.ErrSeverity.ERR)
        for receptorId in argin:
            # check if the specified recetorID is valid, that is a number
            # in the range [1-197]
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
                # read the updated list of the assigned receptors
                self._receptors = proxy.receptors
                # build the list with the VCCs assigned to the sub-array
                self._vcc = []
                for receptor_id in self._receptors:
                    vcc_id = self._receptor_to_vcc_map[receptor_id]
                    self._vcc.append(vcc_id) 
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

    def is_RemoveReceptors_allowed(self):
        """
        Check if the RemoveReceptors command can be executed. Receptors can be removed from a subarray
        only when its obsState is IDLE or READY. 

        Returns:
            True if the command can be executed, otherwise False
        """
        if self._obs_state not in [ObsState.IDLE.value, ObsState.READY.value]:
            return False
        return True

    @command(
    dtype_in=('uint16',), 
    doc_in="The list with the receptor IDs to remove", 
    )
    @DebugIt()
    def RemoveReceptors(self, argin):
        """
        Remove the receptors from a subarray.
        Argin:
            The list of the receptor IDs to remove from the subarray.
            Type: array of DevUShort
        Returns:
            None
        Raises:
            tango.DevFailed exception if the command fails.
        """
        # PROTECTED REGION ID(CspSubarray.RemoveReceptors) ENABLED START #
        # check if the list of assigned receptors is empty.
        if not self._receptors:
            self.dev_logging("RemoveReceptors: no receptor to remove", tango.LogLevel.LOG_INFO)
            return
        # check if the CspSubarray is already connected to the CbfSubarray
        proxy = 0
        if self.__is_subarray_available(self._cbf_subarray_fqdn):
            try:
                proxy = self._se_subarrays_proxies[self._cbf_subarray_fqdn]
                # forward the command to CbfSubarray
                proxy.RemoveReceptors(argin)
                # update the list of assigned receptors
                self._receptors = proxy.receptors
                # update the list of assigned VCCs
                self._vcc = []
                for receptor_id in self._receptors:
                    vcc_id = self._receptor_to_vcc_map[receptor_id]
                    self._vcc.append(vcc_id) 
                # TODO
                # If the list of receptors is empty do we explicity set State to OFF 
                # or do we rely on CbfSubarray State change?
                # if not self._receptors:
                #    self.set_state(tango.DevState.OFF)
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

    def is_RemoveAllReceptors_allowed(self):
        """
        Check if the RemoveAllReceptors command can be executed. Receptors can be removed from a subarray
        only when its obsState is IDLE or READY. 

        Returns:
            True if the command can be executed, otherwise False
        """
        if self._obs_state not in [ObsState.IDLE.value, ObsState.READY.value]:
            return False
        return True
    @command(
    )
    @DebugIt()
    def RemoveAllReceptors(self):
        """
        Remove all the assigned receptors from a subarray.
        Argin:
            None
        Returns:
            None
        Raises:
            tango.DevFailed exception if the command fails.
        """
        # PROTECTED REGION ID(CspSubarray.RemoveAllReceptors) ENABLED START #
        # check if the list of assigned receptors is empty
        if not self._receptors:
            self.dev_logging("RemoveReceptors: no receptor to remove", tango.LogLevel.LOG_INFO)
            return
        proxy = 0
        if self.__is_subarray_available(self._cbf_subarray_fqdn):
            try:
                proxy = self._se_subarrays_proxies[self._cbf_subarray_fqdn]
                # forward the command to the CbfSubarray
                proxy.command_inout("RemoveAllReceptors")
                # re-read the list of assigned receptors
                self._receptors = proxy.receptors
                if not self._receptors:
                    self._vcc = []
                    # TODO
                    # Do we explicity set State to OFF or do we rely on CbfSubarray State change?
                    #self.set_state(tango.DevState.OFF)
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
        Check if a ConfigureScan command can be executed. A scan configuration can be performed 
        when the Subarray is ON (that is, at least one receptor is assigned to it)

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
        Configure a scan for the subarray.
        Argin:
            a JSON-encoded string with the parameters to configure a scan.
        Returns:
            None
        Raises:
            tango.DevFailed exception if the configuration is not valid.

        **Note**: Part of this code (the input string parsing) comes from the CBF project 
        developed by J.Jjang (NRC-Canada)
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
                with open("test_ConfigureScan_basic.json") as json_file:
                    #load the file into a dictionary
                    argin_dict = json.load(json_file)
                    # dump the dictionary into the input string to forward to CbfSubarray
                    argin = json.dumps(argin_dict)
            else:        
                argin_dict = json.loads(argin)
        except FileNotFoundError as file_err:
            self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
            tango.Except.throw_exception("Command failed", file_err,
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
            proxy.command_inout("ConfigureScan", argin) 
            self._obs_state = ObsState.CONFIGURING.value
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
        # PROTECTED REGION ID(CspSubarray.AddSearchBeams) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CspSubarray.AddSearchBeams

    @command(
    dtype_in='uint16', 
    doc_in="The number of SearchBeam Capabilities to remove from the sub-arrays.\nAll the search beams are removed from the sub-array if the input number \nis equal to the max number of search bem capabilities (1500 for MID)", 
    )
    @DebugIt()
    def RemoveNumOfSearchBeams(self, argin):
        # PROTECTED REGION ID(CspSubarray.RemoveSearchBeams) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CspSubarray.RemoveSearchBeams

    @command(
    dtype_in=('uint16',), 
    doc_in="The list of timing beams IDs to assign to the subarray", 
    )
    @DebugIt()
    def AddTimingBeams(self, argin):
        # PROTECTED REGION ID(CspSubarray.AddTimingBeams) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CspSubarray.AddTimingBeams

    @command(
    dtype_in=('uint16',), 
    doc_in="The list of Vlbi beams ID to assign to the subarray.", 
    )
    @DebugIt()
    def AddVlbiBeams(self, argin):
        # PROTECTED REGION ID(CspSubarray.AddVlbiBeams) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CspSubarray.AddVlbiBeams

    @command(
    dtype_in=('uint16',), 
    doc_in="The list of Search Beam Capabilities ID to assign to the sub-array.", 
    )
    @DebugIt()
    def AddSearchBeamsID(self, argin):
        # PROTECTED REGION ID(CspSubarray.AddSearchBeamsID) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CspSubarray.AddSearchBeamsID

    @command(
    dtype_in=('uint16',), 
    doc_in="The list of Search Beams IDs to remove from the sub-array.", 
    )
    @DebugIt()
    def RemoveSearchBeamsID(self, argin):
        # PROTECTED REGION ID(CspSubarray.RemoveSearchBeamsID) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CspSubarray.RemoveSearchBeamsID

    @command(
    )
    @DebugIt()
    def RemoveTimingBeams(self):
        # PROTECTED REGION ID(CspSubarray.RemoveTimingBeams) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CspSubarray.RemoveTimingBeams

    @command(
    )
    @DebugIt()
    def RemoveVlbiBeams(self):
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
