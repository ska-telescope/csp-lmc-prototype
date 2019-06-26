# -*- coding: utf-8 -*-
#
# This file is part of the CspMaster project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" CspMaster Tango device prototype

CSPMaster TANGO device class for the CSPMaster prototype
"""
# PROTECTED REGION ID (CspMaster.standardlibray_import) ENABLED START #
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
from global_enum import HealthState, AdminMode
from skabase.SKAMaster.SKAMaster import SKAMaster
from skabase.auxiliary import utils
import release
# PROTECTED REGION END #    //  CspMaster.additionnal_import


__all__ = ["CspMaster", "main"]

class CspMaster(with_metaclass(DeviceMeta, SKAMaster)):
    """
    CSPMaster TANGO device class for the CSPMaster prototype
    """
    # PROTECTED REGION ID(CspMaster.class_variable) ENABLED START #

    # ---------------
    # Event Callback functions
    # ---------------
    def seSCMCallback(self, evt):
        """
        Class private method.
        Retrieve the values of the sub-element SCM attributes subscribed for change
        event at device initialization.

        :param evt: The event data

        :return: None
        """
        unknown_device = False
        if evt.err is False:
            try:
                if "healthstate" in evt.attr_name:
                    if self.CspMidCbf in evt.attr_name:
                        self._cbf_health_state = evt.attr_value.value
                    elif self.CspMidPss in evt.attr_name:
                        self._pss_health_state = evt.attr_value.value
                    elif self.CspMidPst in evt.attr_name:
                        self._pst_health_state = evt.attr_value.value
                    else:
                        # should NOT happen!
                        unknown_device = True    
                elif "state" in evt.attr_name:
                    if self.CspMidCbf in evt.attr_name:
                        self._cbf_state = evt.attr_value.value
                    elif self.CspMidPss in evt.attr_name:
                        self._pss_state = evt.attr_value.value
                    elif self.CspMidPst in evt.attr_name:
                        self._pst_state = evt.attr_value.value
                    else:
                        # should NOT happen!
                        unknown_device = True    

                elif "adminmode" in evt.attr_name: 
                    if self.CspMidCbf in evt.attr_name:
                        self._cbf_admin_mode = evt.attr_value.value
                    elif self.CspMidPss in evt.attr_name:
                            self._pss_admin_mode = evt.attr_value.value
                    elif self.CspMidPst in evt.attr_name:
                            self._pst_admin_mode = evt.attr_value.value
                    else:
                        # should NOT happen!
                        unknown_device = True    
                else: 
                    log_msg = "Attribute {} not still handled".format(evt.attr_name)
                    self.dev_logging(log_msg, tango.LogLevel.LOG_WARN)

                if unknown_device == True:
                    log_msg = "Unexpected change event for attribute: " + \
                                  str(evt.attr_name)
                    self.dev_logging(log_msg, tango.LogLevel.LOG_WARN)
                    return

                log_msg = "New value for " + str(evt.attr_name) + " is " + \
                          str(evt.attr_value.value) 
                self.dev_logging(log_msg, tango.LogLevel.LOG_INFO)
                # update CSP global state
                if "state" in evt.attr_name:
                    self.__set_csp_state()
            except tango.DevFailed as df:
                self.dev_logging(str(df.args[0].desc), tango.LogLevel.LOG_ERR)
            except Exception as except_occurred:
                self.dev_logging(str(except_occurred), tango.LogLevel.LOG_ERR)
        else: 
            for item in evt.errors: 
                # API_EventTimeout: if sub-element device not reachable it transits 
                # to UNKNOWN state.
                if item.reason == "API_EventTimeout":
                    # CBF sub-element
                    if self.CspMidCbf in evt.attr_name:
                        self._cbf_state = tango.DevState.UNKNOWN
                        self._cbf_health_state = HealthState.UNKNOWN.value
                        if self._se_to_switch_off[self.CspMidCbf] == True:
                            self._cbf_state = tango.DevState.OFF
                    # PSS sub-element
                    if self.CspMidPss in evt.attr_name:
                        self._pss_state = tango.DevState.UNKNOWN
                        self._pss_health_state = HealthState.UNKNOWN.value
                        if self._se_to_switch_off[self.CspMidPss] == True:
                            self._cbf_state = tango.DevState.OFF
                    # PST sub-element
                    if self.CspMidPst in evt.attr_name:
                        self._pst_state = tango.DevState.UNKNOWN
                        self._pst_health_state = HealthState.UNKNOWN.value
                        if self._se_to_switch_off[self.CspMidPst] == True:
                            self._cbf_state = tango.DevState.OFF
                    # update the State and healthState of the CSP Element
                    self.__set_csp_state()
                log_msg = item.reason + ": on attribute " + str(evt.attr_name)
                self.dev_logging(log_msg, tango.LogLevel.LOG_WARN)

    # ---------------
    # Class private methods
    # ---------------
    def __set_csp_state(self):
        """
        Class private method.
        Retrieve the State attribute of the CSP sub-elements and aggregate them to build 
        up the CSP global state.

        :param: None

        :return: None
        """
        self.__set_csp_health_state()
        # CSP state reflects the status of CBF. Only if CBF is present CSP can work.
        # The state of PSS and PST sub-elements only contributes to determine the CSP
        # health state.
        self.set_state(self._cbf_state)

    def __set_csp_health_state(self):
        """
        Class private method.
        Retrieve the healthState attribute of the CSP sub-elements and aggregate them
        to build up the CSP health state

        :param: None

        :return: None
        """

        if (self._cbf_health_state == HealthState.OK.value) and \
           (self._pst_health_state == HealthState.OK.value) and \
           (self._pst_health_state == HealthState.OK.value):
            self._health_state = HealthState.OK.value
        elif (self._cbf_health_state == HealthState.UNKNOWN.value):
            self._health_state = HealthState.UNKNOWN.value
        elif (self._cbf_health_state == HealthState.FAILED.value):
            self._health_state = HealthState.FAILED.value
        else:
            self._health_state = HealthState.DEGRADED.value

    def __get_maxnum_of_capabilities(self):
        """
        Class private method.

        Retrieve the max number of CSP Capabilities for each capability type.\n
        The couple [CapabilityType: num] is specified as TANGO Device Property.
        Default values for Mid CSP are:\n
        - Subarray      16 \n
        - SearchBeam  1500 \n
        - TimingBeam    16 \n
        - VlbiBeam      20 \n
        :param: None

        :return: None
        """
        self._search_beams_maxnum =  const.NUM_OF_SEARCH_BEAMS
        self._timing_beams_maxnum =  const.NUM_OF_TIMING_BEAMS
        self._vlbi_beams_maxnum   =  const.NUM_OF_VLBI_BEAMS
        self._subarrays_maxnum    =  const.NUM_OF_SUBARRAYS
        self._available_search_beams_num =  const.NUM_OF_SEARCH_BEAMS
        self._available_timing_beams_num =  const.NUM_OF_TIMING_BEAMS
        self._available_vlbi_beams_num   =  const.NUM_OF_VLBI_BEAMS
        self._available_subarrays_num    =  const.NUM_OF_SUBARRAYS
        if self._max_capabilities:
            try:
                self._search_beams_maxnum = self._max_capabilities["SearchBeam"]
            except KeyError:  # not found in DB
                self._search_beams_maxnum = const.NUM_OF_SEARCH_BEAMS
            try:
                self._timing_beams_maxnum = self._max_capabilities["TimingBeam"]
            except KeyError:  # not found in DB
                self._timing_beams_maxnum = const.NUM_OF_TIMING_BEAMS
            try:
                self._vlbi_beams_maxnum = self._max_capabilities["VlbiBeam"]
            except KeyError:  # not found in DB
                self._vlbi_beams_maxnum = const.NUM_OF_VLBI_BEAMS
            try:
                self._subarrays_maxnum = self._max_capabilities["Subarray"]
            except KeyError:  # not found in DB
                self._subarrays_maxnum = const.NUM_OF_SUBARRAYS
        else:
            self.dev_logging("MaxCapabilities device property not defined. \
                              Use defaul values", tango.LogLevel.LOG_WARN)

    def __get_maxnum_of_receptors(self):

        self._receptors_maxnum = const.NUM_OF_RECEPTORS
        capability_dict = {}
        try:
            proxy = self._se_proxies[self.CspMidCbf]
            proxy.ping()
            vcc_to_receptor = proxy.vccToReceptor
            self._vcc_to_receptor_map = dict([int(ID) for ID in pair.split(":")] for pair in vcc_to_receptor)
            cbf_max_capabilities = proxy.maxCapabilities
            for capability in cbf_max_capabilities:
                cap_type, cap_num = capability.split(':')
                capability_dict[cap_type] = int(cap_num)
            self._receptors_maxnum = capability_dict["VCC"]
            self._receptorsMembership = [0]* self._receptors_maxnum
        except KeyError as key_err:
            log_msg = "Error: no key found for " + str(key_err)
            self.dev_logging(log_msg, int(tango.LogLevel.LOG_ERROR))

        except tango.DevFailed as df:
            log_msg = "Error: " + str(df.args[0].reason)
            self.dev_logging(log_msg, int(tango.LogLevel.LOG_ERROR))

    def __init_capabilities(self):
        """
        Class private method.
        Initialize the CSP capabilities State and Modes attributes.
        """
        self._search_beams_state = [tango.DevState.UNKNOWN for i in range(self._search_beams_maxnum)]
        self._timing_beams_state = [tango.DevState.UNKNOWN for i in range(self._timing_beams_maxnum)]
        self._vlbi_beams_state = [tango.DevState.UNKNOWN for i in range(self._vlbi_beams_maxnum)]
        self._search_beams_health_state = [HealthState.UNKNOWN for i in range(self._search_beams_maxnum)]
        self._timing_beams_health_state = [HealthState.UNKNOWN for i in range(self._timing_beams_maxnum)]
        self._vlbi_beams_health_state = [HealthState.UNKNOWN for i in range(self._vlbi_beams_maxnum)]
        self._search_beams_admin = [AdminMode.ONLINE for i in range(self._search_beams_maxnum)]
        self._timing_beams_admin = [AdminMode.ONLINE for i in range(self._timing_beams_maxnum)]
        self._vlbi_beams_admin = [AdminMode.ONLINE for i in range(self._vlbi_beams_maxnum)]


    def __connect_to_subelements(self):
        """
        Class private method.
        Establish connection with each CSP sub-element.
        If connection succeeds, the CspMaster device subscribes the State, healthState 
        and adminMode attributes of each CSP Sub-element and registers a callback function
        to handle the events (see seSCMCallback()).
        Exceptions are logged.
        Args:
            None
        Returns:
            None
        """
        for fqdn in self._se_fqdn:
            # initialize the list for each dictionary key-name
            self._se_event_id[fqdn] = []
            try:
                self._se_to_switch_off[fqdn] = False
                log_msg = "Trying connection to" + str(fqdn) + " device"
                self.dev_logging(log_msg, int(tango.LogLevel.LOG_INFO))
                device_proxy = DeviceProxy(fqdn)
                device_proxy.ping()

                # store the sub-element proxies 
                self._se_proxies[fqdn] = device_proxy

                # Subscription of the sub-element State,healthState and adminMode
                ev_id = device_proxy.subscribe_event("State", EventType.CHANGE_EVENT,
                        self.seSCMCallback, stateless=True)
                self._se_event_id[fqdn].append(ev_id)

                ev_id = device_proxy.subscribe_event("healthState", EventType.CHANGE_EVENT,
                        self.seSCMCallback, stateless=True)
                self._se_event_id[fqdn].append(ev_id)

                ev_id = device_proxy.subscribe_event("adminMode", EventType.CHANGE_EVENT,
                        self.seSCMCallback, stateless=True)
                self._se_event_id[fqdn].append(ev_id)
            except tango.DevFailed as df:
                for item in df.args:
                    log_msg = "Failure in connection to " + str(fqdn) + \
                            " device: " + str(item.reason)
                    self.dev_logging(log_msg, int(tango.LogLevel.LOG_ERROR))

    def __create_search_beam_group(self):
        """
        Class private method.
        Create a TANGO GROUP to get CSP SearchBeams Capabilities 
        information
        """
        pass

    def __create_timing_beam_group(self):
        """
        Class private method.
        Create a TANGO GROUP to get CSP TimingBeams Capabilities 
        information
        """
        pass

    def __create_vlbi_beam_group(self):
        """
        Class private method.
        Create a TANGO GROUP to get CSP Vlbi Beams Capabilities 
        information
        """
        pass


    # PROTECTED REGION END #    //  CspMaster.class_variable

    # -----------------
    # Device Properties
    # -----------------

    CspMidCbf = device_property(
        dtype='str', default_value="mid_csp_cbf/sub_elt/master",
        doc="TANGO Device property.\n\n The Mid CBF sub-element address\n\n *type*: string",
    )

    CspMidPss = device_property(
        dtype='str', default_value="mid_csp_pss/sub_elt/master",
        doc="TANGO Device property.\n\n The Mid Pss sub-element address\n\n *type*: string",
    )

    CspMidPst = device_property(
        dtype='str', default_value="mid_csp_pst/sub_elt/master",
        doc="TANGO Device property.\n\n The Mid Pst sub-element address\n\n *type*: string",
    )

    CspSubarrays = device_property(
        dtype=('str',),
        doc="TANGO Device property.\n\n The Mid Subarrays addresses\n\n *type*: array of string",
    )

    SearchBeams = device_property(
        dtype=('str',),
        doc="TANGO Device property.\n\n The Mid SearchBeams Capabilities addresses\n\n *type*: array of string",
    )

    TimingBeams = device_property(
        dtype=('str',),
        doc="TANGO Device property.\n\n The Mid TiminingBeam Capabilities addresses\n\n *type*: array of string",
    )

    VlbiBeams = device_property(
        dtype=('str',),
        doc="TANGO Device property.\n\n The Mid VlbiBeam Capabilities addresses\n\n *type*: array of string",
    )

    # ----------
    # Attributes
    # ----------

    # NB: To overide the write method of the adminMode attribute, we need to enable the
    #     "overload attribute" check button in POGO. 
    adminMode = attribute(
        dtype='DevEnum',
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        doc="The admin mode reported for this device. It may interpret the current device \n\
             condition of all managed devices to set this. Most possibly an aggregate attribute.",
        enum_labels=["ON-LINE", "OFF-LINE", "MAINTENANCE", "NOT-FITTED", "RESERVED", ],
    )

    commandProgress = attribute(
        dtype='uint16',
        label="Command progress percentage",
        max_value=100,
        min_value=0,
        polling_period=3000,
        abs_change=5,
        rel_change=2,
        doc="Tango Device attribute.\n\nPercentage progress implemented for commands that\
             result in state/mode \
             transitions for a large number of components and/or are executed in \
             stages (e.g power up, power down)\n\ntype: uint16",
    )

    cspCbfState = attribute(
        dtype='DevState',
        label="CBF status",
        polling_period=3000,
        doc="The CBF sub-element State.",
    )

    cspPssState = attribute(
        dtype='DevState',
        label="PSS status",
        polling_period=3000,
        doc="The PSS sub-element State.",
    )

    cspPstState = attribute(
        dtype='DevState',
        label="PST status",
        polling_period=3000,
        doc="The PST sub-element State",
    )

    cspCbfHealthState = attribute(
        dtype='DevEnum',
        label="CBF Health status",
        enum_labels=["OK", "DEGRADED", "FAILED", "UNKNOWN",],
        polling_period=3000,
        abs_change=1,
        doc="The CBF sub-element health status.",
    )

    cspPssHealthState = attribute(
        dtype='DevEnum',
        label="PSS Health status",
        enum_labels=["OK", "DEGRADED", "FAILED", "UNKNOWN",],
        polling_period=3000,
        abs_change=1,
        doc="The PSS sub-element health status",
    )

    cspPstHealthState = attribute(
        dtype='DevEnum',
        label="PST health status",
        enum_labels=["OK", "DEGRADED", "FAILED", "UNKNOWN",],
        polling_period=3000,
        abs_change=1,
        doc="The PST sub-element health status.",
    )

    cbfMasterAddress = attribute(
        dtype='str',
        doc="The Mid CbfMaster TANGO device FQDN",
    )

    pssMasterAddress = attribute(
        dtype='str',
        doc="The Mid PssMaster TANGO device FQDN",
    )

    pstMasterAddress = attribute(
        dtype='str',
        doc="The Mid PstMaster TANGO device FQDN",
    )

    cbfAdminMode = attribute(
        dtype='DevEnum',
        access=AttrWriteType.READ_WRITE,
        label="CBF administrative Mode",
        polling_period=3000,
        abs_change=1,
        enum_labels=["ON-LINE", "OFF-LINE", "MAINTENANCE", "NOT-FITTED", "RESERVED", ],
        doc="The CbfMaster TANGO Device administration mode",
    )

    pssAdminMode = attribute(
        dtype='DevEnum',
        access=AttrWriteType.READ_WRITE,
        label="PSS administrative mode",
        polling_period=3000,
        abs_change=1,
        enum_labels=["ON-LINE", "OFF-LINE", "MAINTENANCE", "NOT-FITTED", "RESERVED", ],
        doc="The PssMaster TANGO Device administration mode",
    )

    pstAdminMode = attribute(
        dtype='DevEnum',
        access=AttrWriteType.READ_WRITE,
        label="PST administrative mode",
        polling_period=3000,
        abs_change=1,
        enum_labels=["ON-LINE", "OFF-LINE", "MAINTENANCE", "NOT-FITTED", "RESERVED", ],
        doc="The PstMaster TANGO Device administration mode",
    )

    availableCapabilities = attribute(
        dtype=('str',),
        max_dim_x=20,
        doc="A list of available number of instances of each capability type, e.g. `CORRELATOR:512`, `PSS-BEAMS:4`.",
    )

    reportSearchBeamState = attribute(
        dtype=('DevState',),
        max_dim_x=1500,
        label="Search Beams state",
        doc="The State value of CSP SearchBeam Capabilities. Reported as an array of DevState.",
    )

    reportSearchBeamHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=1500,
        label="Search Beams health status",
        doc="The healthState of the CSP SearchBeam Capabilities. Reported as an array \
             of ushort. For ex:\n[0,0,...,1..]",
    )

    reportSearchBeamAdminMode = attribute(
        dtype=('uint16',),
        max_dim_x=1500,
        label="Search beams admin mode",
        doc="Report the administration mode of the search beams as an array \
             of unisgned short. Fo ex:\n[0,0,0,...2..]",
    )

    reportTimingBeamState = attribute(
        dtype=('DevState',),
        max_dim_x=16,
        label="Timing Beams state",
        doc="Report the state of the timing beams as an array of DevState.",
    )

    reportTimingBeamHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=16,
        label="Timing Beams health status",
        doc="*TANGO Attribute*: healhState of the TimingBeam Capabilities as an array \
             of UShort.",
    )

    reportTimingBeamAdminMode = attribute(
        dtype=('uint16',),
        max_dim_x=16,
        label="Timing beams admin mode",
        doc="Report the administration mode of the timing beams as an array \
             of unisgned short. For ex:\n[0,0,0,...2..]",
    )

    reportVlbiBeamState = attribute(
        dtype=('DevState',),
        max_dim_x=20,
        label="VLBI Beams state",
        doc="Report the state of the VLBI beams as an array of DevState.",
    )

    reportVlbiBeamHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=20,
        label="VLBI Beams health status",
        doc="Report the health status of the VLBI beams as an array \
             of unsigned short. For ex:\n[0,0,...,1..]",
    )

    reportVlbiBeamAdminMode = attribute(
        dtype=('uint16',),
        max_dim_x=20,
        label="VLBI beams admin mode",
        doc="Report the administration mode of the VLBI beams as an array \
             of unisgned short. For ex:\n[0,0,0,...2..]",
    )

    cspSubarrayAddress = attribute(
        dtype=('str',),
        max_dim_x=16,
        doc="CSPSubarrays FQDN",
    )

    searchBeamCapAddress = attribute(
        dtype=('str',),
        max_dim_x=1500,
        label="SearchBeamCapabilities FQDNs",
        doc="SearchBeam Capabilities FQDNs",
    )

    timingBeamCapAddress = attribute(
        dtype=('str',),
        max_dim_x=16,
        label="TimingBeam Caapbilities FQDN",
        doc="TimingBeam Capabilities FQDNs.",
    )

    vlbiCapAddress = attribute(
        dtype=('str',),
        max_dim_x=20,
        label="VLBIBeam Capabilities FQDNs",
        doc="VLBIBeam Capablities FQDNs",
    )

    receptorMembership = attribute(
        dtype=('uint16',),
        max_dim_x=197,
        label="Receptor Memebership",
        doc="The receptors affiliation to CSPsub-arrays.",
    )

    searchBeamMembership = attribute(
        dtype=('uint16',),
        max_dim_x=1500,
        label="SearchBeam Memebership",
        doc="The CSP sub-array affiliation of earch beams",
    )

    timingBeamMembership = attribute(
        dtype=('uint16',),
        max_dim_x=16,
        label="TimingBeam Membership",
        doc="The CSPSubarray affiliation of timing beams.",
    )

    vlbiBeamMembership = attribute(
        dtype=('uint16',),
        max_dim_x=20,
        label="VLBI Beam membership",
        doc="The CSPsub-rray affiliation of VLBI beams.",
    )

    availableReceptorIDs = attribute(
        dtype=('uint16',),
        max_dim_x=197,
        label="Available receptors IDs",
        doc="The list of available receptors IDs.",
    )

    # TODO: understand why device crashes if these forwarded attributes are declared
    #vccCapabilityAddress = attribute(name="vccCapabilityAddress", label="vccCapabilityAddress",
    #    forwarded=True
    #)
    #fspCapabilityAddress = attribute(name="fspCapabilityAddress", label="fspCapabilityAddress",
    #    forwarded=True
    #)
    reportVCCState = attribute(name="reportVCCState", label="reportVCCState",
        forwarded=True
    )
    """
    *TANGO Forwarded attribute*.

    Report the State of the Mid CBF Very Coarse Channel TANGO Devices as an array of DevState.

    *__root_att*: /mid_csp_cbf/sub_elt/master/reportVCCState
    """

    reportVCCHealthState = attribute(name="reportVCCHealthState", label="reportVCCHealthState",
        forwarded=True
    )
    """
    *TANGO Forwarded attribute*.

    Report the healthState of the Mid CBF Very Coarse Channel TANGO Devices as an array of UShort.

    *__root_att*: /mid_csp_cbf/sub_elt/master/reportVCCHealthState
    """

    reportVCCAdminMode = attribute(name="reportVCCAdminMode", label="reportVCCAdminMode",
        forwarded=True
    )
    """
    *TANGO Forwarded attribute*.

    Report the adminMode of the Mid CBF Very Coarse Channel TANGO devices as an array of UShort.

    *__root_att*: /mid_csp_cbf/sub_elt/master/reportVccAdminMode  
    """

    reportFSPState = attribute(name="reportFSPState", label="reportFSPState",
        forwarded=True
    )
    """
    *TANGO Forwarded attribute*.

    Report the State of the Mid CBF Frequency Slice Processor TANGO devices as an array of DevState.

    *__root_att*: /mid_csp_cbf/sub_elt/master/reportFSPHealthState
    """

    reportFSPHealthState = attribute(name="reportFSPHealthState", label="reportFSPHealthState",
        forwarded=True
    )
    """
    *TANGO Forwarded attribute*.

    Report the healthState of the Mid CBF Frequency Slice Processor devices as an array of UShort.

    *__root_att*: /mid_csp_cbf/sub_elt/master/reportFSPHealthState
    """

    reportFSPAdminMode = attribute(name="reportFSPAdminMode", label="reportFSPAdminMode",
        forwarded=True
    )
    """
    *TANGO Forwarded attribute*.

    Report the adminMode of the Mid CBF Frequency Slice Processors TANGO Device as \
    an array of UShort.

    *__root_att*: /mid_csp_cbf/sub_elt/master/reportFSPAdminMode
    """

    fspMembership = attribute(name="fspMembership", label="fspMembership",
        forwarded=True
    )
    """
    *TANGO Forwarded attribute*.

    Report the Mid CBF Frequency Slice Processor TANGO Devices subarray affilitation.

    *__root_att*: /mid_csp_cbf/sub_elt/master/fspMembership
    """

    vccMembership = attribute(name="vccMembership", label="vccMembership",
        forwarded=True
    )
    """
    *TANGO Forwarded attribute*.

    Report the Mid CBF Very Coarse Channel TANGO Devices  subarray affilitation.

    *__root_att*: /mid_csp_cbf/sub_elt/master/fspMembership
    """

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKAMaster.init_device(self)
        self._build_state = '{}, {}, {}'.format(release.name, release.version,
                                                release.description)
        self._version_id = release.version
        # PROTECTED REGION ID(CspMaster.init_device) ENABLED START #
        self.set_state(tango.DevState.INIT)
        self._health_state = HealthState.UNKNOWN.value
        self._admin_mode = AdminMode.ONLINE.value

        # initialize attribute values
        self._progress_command = 0;
        # sub-element State,healthState and adminMode initialization
        self._cbf_state        = tango.DevState.UNKNOWN
        self._cbf_health_state = HealthState.UNKNOWN.value
        self._cbf_admin_mode   = AdminMode.ONLINE.value
        self._pss_state        = tango.DevState.UNKNOWN
        self._pss_health_state = HealthState.UNKNOWN.value 
        # PssMaster not present: set it adminMode to OFFLINE
        self._pss_admin_mode   = AdminMode.OFFLINE.value
        self._pst_state        = tango.DevState.UNKNOWN
        self._pst_health_state = HealthState.UNKNOWN.value
        # PstMaster not present: set it adminMode to OFFLINE
        self._pst_admin_mode   = AdminMode.OFFLINE.value

        # set storage and element logging level 
        self._storage_logging_level = int(tango.LogLevel.LOG_INFO)
        self._element_logging_level = int(tango.LogLevel.LOG_INFO)

        # evaluate the CSP element global State and healthState
        #self.__set_csp_state()

        # get the max number of CSP Capabilities for each Csp capability type
        self.__get_maxnum_of_capabilities()
        #initialize the CSP Capabilities State, healthState and adminMode
        self.__init_capabilities()
        #initialize Csp capabilities subarray membership
        self._searchBeamsMembership = [0] * self._search_beams_maxnum
        self._timingBeamsMembership = [0] * self._timing_beams_maxnum
        self._vlbiBeamsMembership   = [0] * self._vlbi_beams_maxnum

        # initialize list with CSP sub-element FQDNs
        self._se_fqdn = []
        self._se_fqdn.append(self.CspMidCbf)
        self._se_fqdn.append(self.CspMidPss)
        self._se_fqdn.append(self.CspMidPst)

        # flag to signal sub-element switch-off request
        self._se_to_switch_off = {}
        for device_name in self._se_fqdn:
            self._se_to_switch_off[device_name] = False
        # initialize the dictionary with sub-element proxies
        self._se_proxies = {}
        # dictionary with list of event ids/sub-element. Need to store the event
        # ids for each sub-element to un-subscribe them at sub-element disconnection.
        self._se_event_id = {}
        # Try connection with sub-elements
        self.__connect_to_subelements()
        self.__get_maxnum_of_receptors()
        # create TANGO Groups to handle SearchBeams, TimingBeams and VlbiBeams
        self.__create_search_beam_group()
        self.__create_timing_beam_group()
        self.__create_vlbi_beam_group()
        # PROTECTED REGION END #    //  CspMaster.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(CspMaster.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CspMaster.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(CspMaster.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CspMaster.delete_device

    # PROTECTED REGION ID#    //  CspMaster private methods
    # PROTECTED REGION END #    //CspMaster private methods 

    # ------------------
    # Attributes methods
    # ------------------

    def write_adminMode(self, value):
        """
        Class method.
        Set the administration mode for the whole CSP element.

        Args:  
            value: one of the administration mode value (ON-LINE,\
            OFF-LInE, MAINTENANCE, NOT-FITTED).
        Returns: 
            None
        """
        # PROTECTED REGION ID(CspMaster.adminMode_write) ENABLED START #
        for fqdn in self._se_fqdn: 
            try:
                device_proxy = self._se_proxies[fqdn]
                device_proxy.adminMode = value
            except KeyError as kerr:
                log_msg = "No proxy to device " + str(kerr)
                self.dev_logging(log_msg, int(tango.LogLevel.LOG_ERROR))
            except tango.DevFailed as df:
                log_msg = "Failure in setting adminMode for device " + str(fqdn) + \
                        ": " + str(df.args[0].reason)
                self.dev_logging(log_msg, int(tango.LogLevel.LOG_ERROR))
        #TODO: what happens if one sub-element fails? 
        self._admin_mode = value
        # PROTECTED REGION END #    //  CspMaster.adminMode_write

    def read_commandProgress(self):
        """
        Class method.

        Returns: 
            Return the commandProgress attribute value.           
        """
        # PROTECTED REGION ID(CspMaster.commandProgress_read) ENABLED START #
        return self._progress_command
        # PROTECTED REGION END #    //  CspMaster.commandProgress_read

    def read_cspCbfState(self):
        """
        Class method.

        Returns: 
            Return the CBF Sub-element State.           
        """
        # PROTECTED REGION ID(CspMaster.cspCbfState_read) ENABLED START #
        return self._cbf_state
        # PROTECTED REGION END #    //  CspMaster.cspCbfState_read

    def read_cspPssState(self):
        """
        Class method.

        Returns: 
            Return the Pss Sub-element State.           
        """
        # PROTECTED REGION ID(CspMaster.cspPssState_read) ENABLED START #
        return self._pss_state
        # PROTECTED REGION END #    //  CspMaster.cspPssState_read

    def read_cspPstState(self):
        """
        Class method.

        Returns: 
            Return the Pst Sub-element State.           
        """
        # PROTECTED REGION ID(CspMaster.cspPstState_read) ENABLED START #
        return self._pst_state
        # PROTECTED REGION END #    //  CspMaster.cspPstState_read

    def read_cspCbfHealthState(self):
        """
        Class method.

        Returns: 
            Return the Cbf Sub-element HealthState.           
        """
        # PROTECTED REGION ID(CspMaster.cspCbfHealthState_read) ENABLED START #
        return self._cbf_health_state
        # PROTECTED REGION END #    //  CspMaster.cspCbfHealthState_read

    def read_cspPssHealthState(self):
        """
        Class method.

        Returns: 
            Return the Pss Sub-element HealthState.           
        """
        # PROTECTED REGION ID(CspMaster.cspPssHealthState_read) ENABLED START #
        return self._pss_health_state
        # PROTECTED REGION END #    //  CspMaster.cspPssHealthState_read

    def read_cspPstHealthState(self):
        """
        Class method.

        Returns: 
            Return the Pst Sub-element HealthState.           
        """
        # PROTECTED REGION ID(CspMaster.cspPstHealthState_read) ENABLED START #
        return self._pst_health_state
        # PROTECTED REGION END #    //  CspMaster.cspPstHealthState_read

    def read_cbfMasterAddress(self):
        """
        Class method.

        Returns: 
            Return the CbfMaster TANGO Device address.
        """
        # PROTECTED REGION ID(CspMaster.cbfMasterAddress_read) ENABLED START #
        return self.CspMidCbf
        # PROTECTED REGION END #    //  CspMaster.cbfMasterAddress_read

    def read_pssMasterAddress(self):
        """
        Class method.

        Returns: 
            Return the PssMaster TANGO Device address.
        """
        # PROTECTED REGION ID(CspMaster.pssMasterAddress_read) ENABLED START #
        return self.CspMidPss
        # PROTECTED REGION END #    //  CspMaster.pssMasterAddress_read

    def read_pstMasterAddress(self):
        """
        Class method.

        Returns: 
            Return the PstMaster TANGO Device address.
        """
        # PROTECTED REGION ID(CspMaster.pstMasterAddress_read) ENABLED START #
        return self.CspMidPst
        # PROTECTED REGION END #    //  CspMaster.pstMasterAddress_read

    def read_cbfAdminMode(self):
        """
        Class method.

        Returns: 
            Return the CbfMaster administration mode.
        """
        # PROTECTED REGION ID(CspMaster.pssAdminMode_read) ENABLED START #
        return self._cbf_admin_mode
        # PROTECTED REGION END #    //  CspMaster.cbfAdminMode_read

    def write_cbfAdminMode(self, value):
        # PROTECTED REGION ID(CspMaster.cbfAdminMode_write) ENABLED START #
        """
        Class method.
        Set the CBF sub-element administration mode.

        Args:  
            value: one of the administration mode value (ON-LINE,\
            OFF-LInE, MAINTENANCE, NOT-FITTED).

        Returns: 
            None
        """
        try:
            cbf_proxy = self._se_proxies[self.CspMidCbf]
            cbf_proxy.adminMode = value
        except KeyError as key_err:
            err_msg = "No proxy for device" + str(key_err)
            self.dev_logging(err_msg, int(tango.LogLevel.LOG_ERROR))
            tango.Except.throw_exception("Command failed", err_msg,
                                         "Set cbf admin mode", tango.ErrSeverity.ERR)
        except tango.DevFailed as df: 
            tango.Except.throw_exception("Command failed", str(df.args[0].desc),
                                         "Set cbf admin mode", tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CspMaster.cbfAdminMode_write

    def read_pssAdminMode(self):
        """
        Class method.

        Returns: 
            Return the PssMaster administration mode.
        """
        # PROTECTED REGION ID(CspMaster.pssAdminMode_read) ENABLED START #
        return self._pss_admin_mode
        # PROTECTED REGION END #    //  CspMaster.pssAdminMode_read

    def write_pssAdminMode(self, value):
        """
        Class method.
        Set the PSS sub-element administration mode.

        Args:  
            value: one of the administration mode value (ON-LINE,\
            OFF-LInE, MAINTENANCE, NOT-FITTED).

        Returns: 
            None
        """
        # PROTECTED REGION ID(CspMaster.pssAdminMode_write) ENABLED START #
        try:
            pss_proxy = self._se_proxies[self.CspMidPss]
            pss_proxy.adminMode = value
        except KeyError as key_err:
            err_msg = "No proxy for device" + str(key_err)
            self.dev_logging(err_msg, int(tango.LogLevel.LOG_ERROR))
            tango.Except.throw_exception("Command failed", err_msg,
                                         "Set pss admin mode", tango.ErrSeverity.ERR)
        except tango.DevFailed as df: 
            tango.Except.throw_exception("Command failed", str(df.args[0].desc),
                                         "Set pss admin mode", tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CspMaster.pssAdminMode_write

    def read_pstAdminMode(self):
        """
        Class method.

        Returns: 
            Return the PstMaster administration mode.
        """
        # PROTECTED REGION ID(CspMaster.pstAdminMode_read) ENABLED START #
        return self._pst_admin_mode
        # PROTECTED REGION END #    //  CspMaster.pstAdminMode_read

    def write_pstAdminMode(self, value):
        """
        Class method.
        Set the PST sub-element administration mode.

        Args:  
            value: one of the administration mode value (ON-LINE,\
            OFF-LInE, MAINTENANCE, NOT-FITTED).

        Returns: 
            None
        """
        # PROTECTED REGION ID(CspMaster.pstAdminMode_write) ENABLED START #
        try:
            pst_proxy = self._se_proxies[self.CspMidPst]
            pst_proxy.adminMode = value
        except KeyError as key_err:
            err_msg = "No proxy for device" + str(key_err)
            self.dev_logging(err_msg, int(tango.LogLevel.LOG_ERROR))
            tango.Except.throw_exception("Command failed", err_msg,
                                         "Set pst admin mode", tango.ErrSeverity.ERR)
        except tango.DevFailed as df: 
            tango.Except.throw_exception("Command failed", str(df.args[0].desc),
                                         "Set pst admin mode", tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CspMaster.pstAdminMode_write
        
    def read_availableCapabilities(self):
        """
        Override method.

        Argin: None
        Returns:
            A list of strings with the number of available resources for each
            capability/resource type.
            Es: ["Receptors:95","SearchBeam:1000", "TimingBeam:16", "VlbiBeam:20"]
        """
        # PROTECTED REGION ID(CspMaster.availableCapabilities_read) ENABLED START #
        self._available_capabilities = {}
        try:
            proxy = tango.DeviceProxy(self.get_name())
            available_receptors = proxy.availableReceptorIDs
            self._available_capabilities["Receptors"] = len(available_receptors)
            #TODO: update when also PSS and PST will be available
            self._available_capabilities["SearchBeam"] = const.NUM_OF_SEARCH_BEAMS
            self._available_capabilities["TimingBeam"] = const.NUM_OF_TIMING_BEAMS
            self._available_capabilities["VlbiBeam"] = const.NUM_OF_VLBI_BEAMS
        except tango.DevFailed as df:
            print(df.args[0].desc)
        return utils.convert_dict_to_list(self._available_capabilities)
        # PROTECTED REGION END #    //  CspMaster.availableCapabilities_read

    def read_reportSearchBeamState(self):
        """
        Class method.

        Argin: None  
        Returns: 
            Return the State of the CSP SearchBeam Capabilities as an array of DevState.
        """
        # PROTECTED REGION ID(CspMaster.reportSearchBeamState_read) ENABLED START #
        return self._search_beams_state
        # PROTECTED REGION END #    //  CspMaster.reportSearchBeamState_read

    def read_reportSearchBeamHealthState(self):
        """
        Class method.

        Argin: None  
        Returns: 
            Return the healthState of the CSP SearchBeam Capabilities as an array of UShort.
            (It's not possible to allocate an array of DevEnum)
        """
        # PROTECTED REGION ID(CspMaster.reportSearchBeamHealthState_read) ENABLED START #
        return self._search_beams_health_state
        # PROTECTED REGION END #    //  CspMaster.reportSearchBeamHealthState_read

    def read_reportSearchBeamAdminMode(self):
        """
        Class method.

        Argin: None  
        Returns: 
            Return the adminMode of the CSP SearchBeam Capabilities as an array of UShort.
            (It's not possible to allocate an array of DevEnum)
        """
        # PROTECTED REGION ID(CspMaster.reportSearchBeamAdminMode_read) ENABLED START #
        return self._search_beams_admin
        # PROTECTED REGION END #    //  CspMaster.reportSearchBeamAdminMode_read

    def read_reportTimingBeamState(self):
        # PROTECTED REGION ID(CspMaster.reportTimingBeamState_read) ENABLED START #
        return self._timing_beams_state
        # PROTECTED REGION END #    //  CspMaster.reportTimingBeamState_read

    def read_reportTimingBeamHealthState(self):
        """
        Class method

        Argin: None  
        Returns:
            The healthState of the CSP TimingBeam Capabilities as an array \
             of UShort.
        """
        # PROTECTED REGION ID(CspMaster.reportTimingBeamHealthState_read) ENABLED START #
        return self._timing_beams_health_state
        # PROTECTED REGION END #    //  CspMaster.reportTimingBeamHealthState_read

    def read_reportTimingBeamAdminMode(self):
        """
        Class method

        Argin: None  
        Returns:
            The adminMode of the CSP TimingBeam Capabilities as an array \
             of UShort.
        """
        # PROTECTED REGION ID(CspMaster.reportTimingBeamAdminMode_read) ENABLED START #
        return self._timing_beams_admin 
        # PROTECTED REGION END #    //  CspMaster.reportTimingBeamAdminMode_read

    def read_reportVlbiBeamState(self):
        """
        Class method

        Argin: None  
        Returns:
            The State of the CSP VlbiBeam Capabilities as an array 
            of DevState.
        """
        # PROTECTED REGION ID(CspMaster.reportVlbiBeamState_read) ENABLED START #
        return self._vlbi_beams_state
        # PROTECTED REGION END #    //  CspMaster.reportVlbiBeamState_read

    def read_reportVlbiBeamHealthState(self):
        """
        Class method

        Argin: None  
        Returns:
            The healthState of the CSP VlbiBeam Capabilities as an array 
            of UShort.
        """
        # PROTECTED REGION ID(CspMaster.reportVlbiBeamHealthState_read) ENABLED START #
        return self._vlbi_beams_health_state
        # PROTECTED REGION END #    //  CspMaster.reportVlbiBeamHealthState_read

    def read_reportVlbiBeamAdminMode(self):
        """
        Class method

        Argin: None  
        Returns:
            The adminMode of the CSP VlbiBeam Capabilities as an array \
             of UShort.
        """
        # PROTECTED REGION ID(CspMaster.reportVlbiBeamAdminMode_read) ENABLED START #
        return self._vlbi_beams_admin
        # PROTECTED REGION END #    //  CspMaster.reportVlbiBeamAdminMode_read
    
    def read_cspSubarrayAddress(self):
        # PROTECTED REGION ID(CspMaster.cspSubarrayAddress_read) ENABLED START #
        if self.CspSubarrays:
            return self.CspSubarrays
        else:
            self.dev_logging("CspSubarrays device property not assigned",
                              int(tango.LogLevel.LOG_WARN))
        # PROTECTED REGION END #    //  CspMaster.cspSubarrayAddress_read

    def read_searchBeamCapAddress(self):
        # PROTECTED REGION ID(CspMaster.searchBeamCapAddress_read) ENABLED START #
        if self.SearchBeams: 
            return self.SearchBeams
        else :
            self.dev_logging("SearchBeams device property not assigned", 
                              int(tango.LogLevel.LOG_WARN))
            return ' '

        # PROTECTED REGION END #    //  CspMaster.searchBeamCapAddress_read

    def read_timingBeamCapAddress(self):
        # PROTECTED REGION ID(CspMaster.timingBeamCapAddress_read) ENABLED START #
        if self.TimingBeams: 
            return self.TimingBeams
        else :
            self.dev_logging("TimingBeams device property not assigned", 
                              int(tango.LogLevel.LOG_WARN))
            return ' '
        # PROTECTED REGION END #    //  CspMaster.timingBeamCapAddress_read

    def read_vlbiCapAddress(self):
        # PROTECTED REGION ID(CspMaster.vlbiCapAddress_read) ENABLED START #
        if self.VlbiBeams: 
            return self.VlbiBeams
        else :
            self.dev_logging("VlbiBeams device property not assigned", 
                              int(tango.LogLevel.LOG_WARN))
            return ' '
        # PROTECTED REGION END #    //  CspMaster.vlbiCapAddress_read

    def read_receptorMembership(self):
        # PROTECTED REGION ID(CspMaster.receptorMembership_read) ENABLED START #
        try:
           proxy = self._se_proxies[self.CspMidCbf]
           proxy.ping()
           vcc_membership = proxy.reportVccSubarrayMembership
           for vcc_id in range(len(vcc_membership)):
               receptorID = self._vcc_to_receptor_map[vcc_id + 1]
               self._receptorsMembership[receptorID - 1] = vcc_membership[vcc_id]
        except tango.DevFailed as df:
            tango.Except.re_throw_exception(df, "CommandFailed",
                                                "read_receptorsMembership failed", 
                                                "Command()")
        return self._receptorsMembership
        # PROTECTED REGION END #    //  CspMaster.receptorMembership_read

    def read_searchBeamMembership(self):
        # PROTECTED REGION ID(CspMaster.searchBeamMembership_read) ENABLED START #
        return self._searchBeamsMembership
        # PROTECTED REGION END #    //  CspMaster.searchBeamMembership_read

    def read_timingBeamMembership(self):
        # PROTECTED REGION ID(CspMaster.timingBeamMembership_read) ENABLED START #
        return self._timingBeamsMembership
        # PROTECTED REGION END #    //  CspMaster.timingBeamMembership_read

    def read_vlbiBeamMembership(self):
        # PROTECTED REGION ID(CspMaster.vlbiBeamMembership_read) ENABLED START #
        return self._vlbiBeamsMembership
        # PROTECTED REGION END #    //  CspMaster.vlbiBeamMembership_read

    def read_availableReceptorIDs(self):
        # PROTECTED REGION ID(CspMaster.availableReceptorIDs_read) ENABLED START #
        self._available_receptorIDs = []
        try:
            proxy = self._se_proxies[self.CspMidCbf]
            proxy.ping()
            vcc_state = proxy.reportVCCState
            # TODO: get the state of the receptor-vcc link!
            #receptor_link_state = proxy.receptorLinkState
            for vcc_id in range(self._receptors_maxnum):
                if vcc_state[vcc_id] not in [tango.DevState.UNKNOWN]:
                    #OSS: receptorID is in [1,197] range
                    #index of receptor_link_state is in [0,196]
                    receptorID = self._vcc_to_receptor_map[vcc_id + 1]
                    # TODO: check the receptor_link_state of the receptor
                    #if receptor_link_state[receptorID - 1] not in [tango.DevState.UNKNOWN]: 
                    self._available_receptorIDs.append(receptorID)
        except tango.DevFailed as df:
            log_msg = "Error in read_availableReceptorIDs: " + df.args[0].reason
            self.dev_logging(log_msg, int(tango.LogLevel.LOG_ERROR))
        return self._available_receptorIDs
        # PROTECTED REGION END #    //  CspMaster.vlbiBeamMembership_read

    # --------
    # Commands
    # --------

    def is_On_allowed(self):
        """
        Command On is allowed when:
        - state is STANDBY and adminMode = MAINTENACE or ONLINE (end state = ON)
        - state is STANDBY and adminMode = OFFLINE, NOTFITTED   (end state = DISABLE)
        - state is DISABLE and adminMode = MAINTENACE or ONLINE (end state = ON)
        """
        # PROTECTED REGION ID(CspMaster.is_On_allowed) ENABLED START #
        if self.get_state() not in [tango.DevState.STANDBY, tango.DevState.DISABLE]:
            return False
        if self._admin_mode in [AdminMode.OFFLINE.value, AdminMode.NOTFITTED.value]:
            if self.get_state() == tango.DevState.DISABLE: 
                return False
            if self.get_state() == tango.DevState.STANDBY: 
                return True
        return True
        # PROTECTED REGION END #    //  CspMaster.is_On_allowed
    @command(
        dtype_in=('str',), 
        doc_in="If the array length is 0, the command applies to the whole CSP Element.\
                If the array length is > 1, each array element specifies the FQDN of the\
                CSP SubElement to switch ON.", 
    )
    @DebugIt()
    def On(self, argin):
        # PROTECTED REGION ID(CspMaster.On) ENABLED START #
        device_list = []    
        num_of_devices = len(argin) 
        if num_of_devices == 0:      # no input argument -> switch on all sub-elements
            num_of_devices = len(self._se_fqdn)
            device_list = self._se_fqdn
        else:
            if num_of_devices > len(self._se_fqdn):
                # too many devices specified-> log the warning but go on
                # with command execution
                self.dev_logging("Too many input parameters", int(tango.LogLevel.LOG_WARN))
            device_list = argin
        nkey_err = 0            
        for device_name in device_list:
            try:
                device_proxy = self._se_proxies[device_name]
                device_proxy.command_inout("On", "")
            except KeyError as error:
                # throw an exception only if:
                # - no proxy found for the only specified input device
                # - or no proxy found for CBF.
                # In all other cases log the error message
                err_msg = "No proxy for device: " + str(error)
                self.dev_logging(err_msg, int(tango.LogLevel.LOG_ERROR))
                nkey_err += 1
            except tango.DevFailed as df:
                # the command fails if:
                # - cbf command fails
                # - or the only specified device fails executing the command.
                # In all other cases the error messages are logged.
                if ("cbf" in device_name) or num_of_devices == 1:
                   tango.Except.throw_exception("Command failed", str(df.args[0].desc),
                                         "On command execution", tango.ErrSeverity.ERR)
                else:
                   self.dev_logging(str(df.args[0].desc), int(tango.LogLevel.LOG_ERROR))

        # throw an exception if ALL the specified devices have no associated proxy
        if nkey_err == num_of_devices:
            err_msg = 'No proxy found for devices:'
            for item in device_list:
                err_msg += item + ' '
            tango.Except.throw_exception("Command failed", err_msg,
                                         "On command execution", tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CspMaster.On

    def is_Off_allowed(self):
        """
        Command Off is allowed when state is STANDBY
        """
        # PROTECTED REGION ID(CspMaster.is_On_allowed) ENABLED START #
        if self.get_state() not in [tango.DevState.STANDBY]:
            return False
        return True

    @command(
        dtype_in=('str',), 
        doc_in="If the array length is 0, the command applies to the whole\ CSP Element.\
If the array length is > 1, each array element specifies the FQDN of the\
 CSP SubElement to switch OFF."

    )
    @DebugIt()
    def Off(self, argin):
        """
        Switch off the CSP Element or a single CSP Sub-element.\n
        :param argin: The list of sub-elements to switch-off. If the array\
        length is 0, the command applies to the whole CSP Element.\
        If the array length is > 1, each array element specifies the FQDN of the\
        CSP SubElement to switch OFF \n

        :return: None

        """
        # PROTECTED REGION ID(CspMaster.Off) ENABLED START #
        device_list = []    
        num_of_devices = len(argin) 
        if num_of_devices == 0:      # no input argument -> switch on all sub-elements
            num_of_devices = len(self._se_fqdn)
            device_list = self._se_fqdn
        else:
            if num_of_devices > len(self._se_fqdn):
                # too many devices specified-> log the warning but go on
                # with command execution
                self.dev_logging("Too many input parameters", int(tango.LogLevel.LOG_WARN))
            device_list = argin
        for device_name in device_list:
            try:
                device_proxy = self._se_proxies[device_name]
                device_proxy.command_inout("Off", "")
                self._se_to_switch_off[device_name] = True
            except KeyError as error:
                err_msg = "No proxy for device" + str(error)
                self.dev_logging(err_msg, int(tango.LogLevel.LOG_ERROR))
            except tango.DevFailed as df:
                self.dev_logging(str(df.args[0].desc), int(tango.LogLevel.LOG_ERROR))

        # PROTECTED REGION END #    //  CspMaster.Off

    def is_Standby_allowed(self):
        """
        Command Standby is allowed when state is ON, DISABLE, ALARM
        """
        # PROTECTED REGION ID(CspMaster.is_On_allowed) ENABLED START #
        if self.get_state() not in [tango.DevState.ON, tango.DevState.DISABLE, 
                                    tango.DevState.ALARM]:
            return False
        return True

    @command(
        dtype_in=('str',), 
        doc_in="If the array length is 0, the command applies to the whole\nCSP Element.\n\
                If the array length is > 1, each array element specifies the FQDN of the\n\
                CSP SubElement to switch OFF.", 
    )
    @DebugIt()
    def Standby(self,argin):
        # PROTECTED REGION ID(CspMaster.Standby) ENABLED START #
        """
        :param argin: listof devices
        :return: None
        """
        device_list = []    
        num_of_devices = len(argin) 
        if num_of_devices == 0:      # no input argument -> switch on all sub-elements
            num_of_devices = len(self._se_fqdn)
            device_list = self._se_fqdn
        else:
            if num_of_devices > len(self._se_fqdn):
                # too many devices specified-> log the warning but go on
                # with command execution
                self.dev_logging("Too many input parameters", int(tango.LogLevel.LOG_WARN))
            device_list = argin
        nkey_err = 0            
        for device_name in device_list:
            try:
                device_proxy = self._se_proxies[device_name]
                device_proxy.command_inout("Standby", "")
            except KeyError as error:
                # throw an exception only if:
                # - no proxy found for the only specified input device
                # - or no proxy found for CBF.
                # In all other cases log the error message
                err_msg = "No proxy for device" + str(error)
                self.dev_logging(err_msg, int(tango.LogLevel.LOG_ERROR))
                nkey_err += 1
            except tango.DevFailed as df:
                # the command fails if:
                # - cbf command fails
                # - or the only specified device fails executing the command.
                # In all other cases the error messages are logged.
                if ("cbf" in device_name) or num_of_devices == 1:
                   tango.Except.throw_exception("Command failed", str(df.args[0].desc),
                                    "Standby command execution", tango.ErrSeverity.ERR)
                else:
                   self.dev_logging(str(df.args[0].desc), int(tango.LogLevel.LOG_ERROR))

        # throw an exception if ALL the specified devices have no associated proxy
        if nkey_err == num_of_devices:
            err_msg = 'No proxy found for devices:'
            for item in device_list:
                err_msg += item + ' '
            tango.Except.throw_exception("Command failed", err_msg,
                                         "Standby command execution", tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CspMaster.Standby

# ----------
# Run server
# ----------

def main(args=None, **kwargs):
    # PROTECTED REGION ID(CspMaster.main) ENABLED START #
    return run((CspMaster,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CspMaster.main

if __name__ == '__main__':
    main()
