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
from global_enum import HealthState, AdminMode, ObsState, ObsMode
from skabase.  SKASubarray import SKASubarray
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
    def scm_change_callback(self, evt):
        """
        Class private method.
        Retrieve the values of the sub-element sub-arrays SCM attributes subscribed for change
        event at device initialization.

        :param evt: The event data

        :return: None
        """
        unknown_device = False
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
        Returns:)
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
        - the max number of capabilities for each type
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
                for i in range(len(cbf_capabilities)):
                    cap_type, cap_num = cbf_capabilities[i].split(':')
                    self._cbf_capabilities[cap_type] = int(cap_num)
                self._se_subarrays_fqdn.append(self.CbfSubarray)

            # try connection to PssMaster    
            if cspMasterProxy.pssAdminMode in [AdminMode.ONLINE.value, AdminMode.MAINTENANCE.value]:
                self._pssAddress = cspMasterProxy.pssMasterAddress
                self._pssMasterProxy = tango.DeviceProxy(self._pssAddress)
                self._pssMasterProxy.ping()
                self._se_subarrays_fqdn.append(self.PssSubarray)

            # try connection to PstMaster    
            if cspMasterProxy.pstAdminMode in [AdminMode.ONLINE.value, AdminMode.MAINTENANCE.value]:
                self._pstAddress = cspMasterProxy.pstMasterAddress
                self._pstMasterProxy = tango.DeviceProxy(self._pstAddress)
                self._pstMasterProxy.ping()
                self._se_subarrays_fqdn.append(self.PstSubarray)
        except tango.DevFailed as df:
            tango.Except.throw_exception("Connection Failed", df.args[0].desc,
                                         "connect_to_master ", tango.ErrSeverity.ERR)

    def __is_subarray_available(self, subarray_name):
        """
        Class private method.
        Check if the sub-element subarray specified by the input argument is 
        available in the TANGO DB. 
        If the subarray device is not present in the list of the connected subarrays, a 
        connection with the device is performed.
        Args:
            subarray_name : the FQDN of the subarray  
        Returns:
            True if the connection with the subarray is established, False otherwise
        """
        try:
            proxy = self._se_subarrays_proxies[subarray_name]
        except KeyError as key_err: 
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
        Set the subarray state and health state.
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
        if self._cbf_subarray_obs_state == ObsState.CONFIGURING.value or\
                self._pss_subarray_obs_state == ObsState.CONFIGURING.value or\
                self._pst_subarray_obs_state == ObsState.CONFIGURING.value:
           self._obs_state = ObsState.CONFIGURING.value
        # analyze only IMAGING mode.
        #TODO: ObsMode need to be defined as a mask because we can have more
        # than one obs_mode active for a sub-array


    # PROTECTED REGION END #    //  CspSubarray.class_variable

    # -----------------
    # Device Properties
    # -----------------
    CspMaster = device_property(
        dtype='str', default_value="mid_csp/elt/master"
    )

    CbfSubarray = device_property(
        dtype='str',
    )

    PssSubarray = device_property(
        dtype='str', 
    )

    PstSubarray = device_property(
        dtype='str', 
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

    pstSubarrayState = attribute(
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

    pstSubarrayHealthState = attribute(
        dtype='DevEnum',
        label="PST Subarray Health State",
        doc="PST Subarray Health State",
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

    pstSubarrayObsState = attribute(
        dtype='DevEnum',
        label="PST Subarray Observing State",
        doc="The PST subarray observing state.",
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

    pstSubarrayAddr = attribute(
        dtype='str',
        label="PST Subarray Address",
        doc="The PST Subarray TANOG address.",
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

    vccState = attribute(name="vccState", label="vccState",
        forwarded=True
    )
    vccHealthState = attribute(name="vccHealthState", label="vccHealthState",
        forwarded=True
    )
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
        self._admin_mode = AdminMode.ONLINE.value
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

        #initialize the list with sub-element sub-arrays addresses
        self._se_subarrays_fqdn = []
        # set default values for sub-element sub-array addresses if not defined in DB
        if self.CbfSubarray == None:
            subarray_fqdn_prefix = "mid_csp_cbf/sub_elt/subarray_"
            if self._subarray_id < 10:
                self.CbfSubarray = subarray_fqdn_prefix + "0" + str(self._subarray_id)
            else:    
                self.CbfSubarray = subarray_fqdn_prefix + str(self._subarray_id)

        if self.PssSubarray == None:
            subarray_fqdn_prefix = "mid_csp_pss/sub_elt/subarray_"
            if self._subarray_id < 10:
                self.PssSubarray = subarray_fqdn_prefix + "0" + str(self._subarray_id)
            else:    
                self.PssSubarray = subarray_fqdn_prefix + str(self._subarray_id)
        if self.PstSubarray == None:
            subarray_fqdn_prefix = "mid_csp_pst/sub_elt/subarray_"
            if self._subarray_id < 10:
                self.PstSubarray = subarray_fqdn_prefix + "0" + str(self._subarray_id)
            else:    
                self.PstSubarray = subarray_fqdn_prefix + str(self._subarray_id)
        self._se_subarrays_proxies = {}
        self._se_subarray_event_id = {}
        self._csp_capabilities = ''
        self._vcc_to_receptor_map = {}
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
            self._receptors = self._se_subarrays_proxies[self.CbfSubarray].receptors
            if not self._receptors:
                self.dev_logging("No receptor assigned to the subarray", tango.LogLevel.LOG_INFO)
            else:
                self.dev_logging("{} assigned to the subarray".format(self._receptors), tango.LogLevel.LOG_INFO)
        except tango.DevFailed as df:    
            for item in df.args:
                log_msg = "Error in {}: {}". format(item.origin, item.reason)
                self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)

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
        return 0
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

    def read_pstSubarrayState(self):
        # PROTECTED REGION ID(CspSubarray.pstSubarrayState_read) ENABLED START #
        return self._pst_subarray_state
        # PROTECTED REGION END #    //  CspSubarray.pstSubarrayState_read

    def read_cbfSubarrayHealthState(self):
        # PROTECTED REGION ID(CspSubarray.cbfSubarrayHealthState_read) ENABLED START #
        return self._cbf_subarray_health_state
        # PROTECTED REGION END #    //  CspSubarray.cbfSubarrayHealthState_read

    def read_pssSubarrayHealthState(self):
        # PROTECTED REGION ID(CspSubarray.pssSubarrayHealthState_read) ENABLED START #
        return self._pss_subarray_health_state
        # PROTECTED REGION END #    //  CspSubarray.pssSubarrayHealthState_read

    def read_pstSubarrayHealthState(self):
        # PROTECTED REGION ID(CspSubarray.pstSubarrayHealthState_read) ENABLED START #
        return self._pst_subarray_health_state
        # PROTECTED REGION END #    //  CspSubarray.pstSubarrayHealthState_read

    def read_cbfSubarrayObsState(self):
        # PROTECTED REGION ID(CspSubarray.cbfSubarrayObsState_read) ENABLED START #
        return self._cbf_subarray_obs_state
        # PROTECTED REGION END #    //  CspSubarray.cbfSubarrayObsState_read

    def read_pssSubarrayObsState(self):
        # PROTECTED REGION ID(CspSubarray.pssSubarrayObsState_read) ENABLED START #
        return self._pss_subarray_obs_state
        # PROTECTED REGION END #    //  CspSubarray.pssSubarrayObsState_read

    def read_pstSubarrayObsState(self):
        # PROTECTED REGION ID(CspSubarray.pstSubarrayObsState_read) ENABLED START #
        return self._pst_subarray_obs_state
        # PROTECTED REGION END #    //  CspSubarray.pstSubarrayObsState_read

    def read_pssSubarrayAddr(self):
        # PROTECTED REGION ID(CspSubarray.pssSubarrayAddr_read) ENABLED START #
        return self.PssSubarray 
        # PROTECTED REGION END #    //  CspSubarray.pssSubarrayAddr_read

    def read_cbfSubarrayAddr(self):
        # PROTECTED REGION ID(CspSubarray.cbfSubarrayAddr_read) ENABLED START #
        return self.CbfSubarray 
        # PROTECTED REGION END #    //  CspSubarray.cbfSubarrayAddr_read

    def read_pstSubarrayAddr(self):
        # PROTECTED REGION ID(CspSubarray.pstSubarrayAddr_read) ENABLED START #
        return self.PstSubarray 
        # PROTECTED REGION END #    //  CspSubarray.pstSubarrayAddr_read

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


    # --------
    # Commands
    # --------

    @command(
    dtype_in=('uint16',), 
    doc_in="List of the receptor IDs to add to the subarray.", 
    )
    @DebugIt()
    def AddReceptors(self, argin):
        # PROTECTED REGION ID(CspSubarray.AddReceptors) ENABLED START #
        # the list with subarray affiliation of each receptor
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
                receptorID = self._vcc_to_receptor_map[vcc_id + 1]
                receptor_membership[receptorID - 1] = vcc_membership[vcc_id]
        except tango.DevFailed as df:
            for item in df.args:
                if "Failed to connect to device" in item.desc:
                    self._cbfMasterProxy = 0
            tango.Except.throw_exception("Command failed", df.args[0].desc,
                                         "AddReceptors", tango.ErrSeverity.ERR)
        for receptorId in argin:
            #check if the specified recetorID is valid
            if receptorId in range(1,198):
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
        #check if the device is already connected to the CbfSubarray
        proxy = 0
        if self.__is_subarray_available(self.CbfSubarray):
            try:     
                proxy = self._se_subarrays_proxies[self.CbfSubarray]
                proxy.command_inout("AddReceptors", receptor_to_assign)
                # read the updated list of the assigned receptors
                self._receptors = proxy.receptors
                # build the list with the VCCs assigned to the sub-array
                receptor_to_vcc_dict = self._cbfMasterProxy.receptorToVcc
                receptor_to_vccId = dict([int(ID) for ID in pair.split(":")] for pair in receptor_to_vcc_dict)
                for receptor_id in self._receptors:
                    vcc_id = receptor_to_vccId[receptor_id]
                    self._vcc.append(vcc_id) 
            except tango.DevFailed as df:
                for item in df.args:
                    log_msg = item.desc
                    self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
                    # TODO: check the kind of failure. If it's a command failure 
                    # re-throw the exception
            except TypeError as err:
                log_msg =  "TypeError: " + str(err)
                self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
                tango.Except.throw_exception("Command failed", log_msg,
                                             "AddReceptors", tango.ErrSeverity.ERR)
        else:
            log_msg = "Subarray " + str(self.CbfSubarray) + " not registered!"
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
        # PROTECTED REGION ID(CspSubarray.RemoveReceptors) ENABLED START #
        try:
            proxy = self._se_subarrays_proxies[self.CbfSubarray]
            proxy.RemoveReceptors(argin)
            # re-read the list of assigned receptors
            self._receptors = proxy.receptors
            # build the list with the VCCs assigned to the sub-array
            for receptor_id in self._receptors:
                vcc_id = receptor_to_vccId[receptor_id]
                self._vcc.remove(vcc_id) 
        except KeyError as key_err: 
            proxy = tango.DeviceProxy(self.CbfSubarray)
            self._se_subarrays_proxies[self.CbfSubarray] = proxy
        except tango.DevFailed as df:
            log_msg = "RemoveReceptors:" + df.args[0].desc
            self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
        # PROTECTED REGION END #    //  CspSubarray.RemoveReceptors

    @command(
    )
    @DebugIt()
    def RemoveAllReceptors(self):
        # PROTECTED REGION ID(CspSubarray.RemoveAllReceptors) ENABLED START #
        try:
            proxy = self._se_subarrays_proxies[self.CbfSubarray]
            proxy.command_inout("RemoveAllReceptors")
            # re-read the list of assigned receptors
            self._receptors = proxy.receptors
            if not self._receptors:
                self._vcc = []
        except KeyError as key_err: 
            proxy = tango.DeviceProxy(self.CbfSubarray)
            self._se_subarrays_proxies[self.CbfSubarray] = proxy
        except tango.DevFailed as df:
            log_msg = "RemoveAllReceptors:" + df.args[0].desc
            self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)
        # PROTECTED REGION END #    //  CspSubarray.RemoveAllReceptors

    @command(
    dtype_in='str', 
    doc_in="A Json-encoded string with the scan configuration.", 
    )
    @DebugIt()
    def ConfigureScan(self, argin):
        # PROTECTED REGION ID(CspSubarray.ConfigureScan) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CspSubarray.ConfigureScan

    @command(
    dtype_in='uint16', 
    doc_in="The number of SearchBeams Capabilities to assign to the subarray", 
    )
    @DebugIt()
    def AddSearchBeams(self, argin):
        # PROTECTED REGION ID(CspSubarray.AddSearchBeams) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CspSubarray.AddSearchBeams

    @command(
    dtype_in='uint16', 
    doc_in="The number of SearchBeam Capabilities to remove from the sub-rrays.", 
    )
    @DebugIt()
    def RemoveSearchBeams(self, argin):
        # PROTECTED REGION ID(CspSubarray.RemoveSearchBeams) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CspSubarray.RemoveSearchBeams

    @command(
    dtype_in='DevVarLongStringArray', 
    doc_in="The TiedArrayBeam type (SearchBeam, TimingBeam, VlbiBeam) and the list \nof the the IDs to remove.\ns.arg[0] = TiedArrayBeam type\nl.arg[0]...l.arg[N] the TiedArray BeamIds.", 
    )
    @DebugIt()
    def AddTiedArrayBeams(self, argin):
        # PROTECTED REGION ID(CspSubarray.AddTiedArrayBeams) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CspSubarray.AddTiedArrayBeams

    @command(
    dtype_in='DevVarLongStringArray', 
    doc_in="The list of list of the TiedArray BeamIds to remove and the type of the TiedArray Beam (SearchBeam, TimingBeam, VlbiBeam)", 
    )
    @DebugIt()
    def RemoveTiedArrayBeams(self, argin):
        # PROTECTED REGION ID(CspSubarray.RemoveTiedArrayBeams) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CspSubarray.RemoveTiedArrayBeams

    @command(
    dtype_in='str', 
    doc_in="The Capability type (SearchBeam, TimingBeam or VlbiBeam)", 
    )
    @DebugIt()
    def RemoveAllTiedArrayBeams(self, argin):
        # PROTECTED REGION ID(CspSubarray.RemoveAllTiedArrayBeams) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CspSubarray.RemoveAllTiedArrayBeams

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(CspSubarray.main) ENABLED START #
    return run((CspSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CspSubarray.main

if __name__ == '__main__':
    main()
