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
#add the paht to import release file (!!)
csplmc_path = os.path.abspath(os.path.join(file_path, "../../"))
sys.path.insert(0, csplmc_path)

# Additional import
# PROTECTED REGION ID(CspMaster.additionnal_import) ENABLED START #
#
import global_enum as const
from global_enum import HealthState, AdminMode
from skabase.SKAMaster import SKAMaster
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
        """
        Get the maximum number of receptors that can be used for observations.
        This number can be less than 197.
        """

        self._receptors_maxnum = const.NUM_OF_RECEPTORS
        capability_dict = {}
        try:
            proxy = self._se_proxies[self.CspMidCbf]
            proxy.ping()
            vcc_to_receptor = proxy.vccToReceptor
            self._vcc_to_receptor_map = dict([int(ID) for ID in pair.split(":")] for pair in vcc_to_receptor)
            # get the number of each Capability type allocated by CBF
            cbf_max_capabilities = proxy.maxCapabilities
            for capability in cbf_max_capabilities:
                cap_type, cap_num = capability.split(':')
                capability_dict[cap_type] = int(cap_num)
            self._receptors_maxnum = capability_dict["VCC"]
            self._receptorsMembership = [0]* self._receptors_maxnum
        except KeyError as key_err:
            log_msg = "Error: no key found for " + str(key_err)
            self.dev_logging(log_msg, int(tango.LogLevel.LOG_ERROR))

        except AttributeError as attr_err:
            log_msg = "Error reading{}: {}".format(str(attr_err.args[0]), attr_err.__doc__)
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
                #for item in df.args:
                log_msg = "Failure in connection to " + str(fqdn) + \
                          " device: " + str(df.args[0].desc)
                self.dev_logging(log_msg, tango.LogLevel.LOG_ERROR)

    def __is_subelement_available(self, subelement_name):
        """
        *Class private method.*

        Check if the sub-element is exported in the TANGO DB. 
        If the device is not present in the list of the connected sub-elements, a 
        connection with the device is performed.

        Args:
            subelement_name : the FQDN of the sub-element
        Returns:
            True if the connection with the subarray is established, False otherwise
        """
        try:
            proxy = self._se_proxies[subelement_name]
            proxy.ping()
        except KeyError as key_err: 
            # Raised when a mapping (dictionary) key is not found in the set of existing keys.
            # no proxy registered for the suelement device
            proxy = tango.DeviceProxy(subelement_name)
            proxy.ping()
            self._se_proxies[subelement_name] = proxy
        except tango.DevFailed as df:
            return False
        return True

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
    """
    *Device property*

    The CspMidCbf FQDN.

    *Type*: DevString
    """

    CspMidPss = device_property(
        dtype='str', default_value="mid_csp_pss/sub_elt/master",
        doc="TANGO Device property.\n\n The Mid Pss sub-element address\n\n *type*: string",
    )
    """
    *Device property*

    The CspMidPss FQDN.

    *Type*: DevString
    """

    CspMidPst = device_property(
        dtype='str', default_value="mid_csp_pst/sub_elt/master",
        doc="TANGO Device property.\n\n The Mid Pst sub-element address\n\n *type*: string",
    )
    """
    *Device property*

    The CspMidPst FQDN.

    *Type*: DevString
    """

    CspSubarrays = device_property(
        dtype=('str',),
        doc="TANGO Device property.\n\n The Mid Subarrays addresses\n\n *type*: array of string",
    )
    """
    *Device property*

    The CspSubarrays FQDN.

    *Type*: array of DevString
    """

    SearchBeams = device_property(
        dtype=('str',),
        doc="TANGO Device property.\n\n The Mid SearchBeams Capabilities addresses\n\n *type*: array of string",
    )
    """
    *Device property*

    The CSP Search Beam Capabilities FQDNs.

    *Type*: array of DevString
    """

    TimingBeams = device_property(
        dtype=('str',),
        doc="TANGO Device property.\n\n The Mid TiminingBeam Capabilities addresses\n\n *type*: array of string",
    )
    """
    *Device property*

    The CSP Timing Beam Capabilities FQDNs.

    *Type*: array DevString
    """

    VlbiBeams = device_property(
        dtype=('str',),
        doc="TANGO Device property.\n\n The Mid VlbiBeam Capabilities addresses\n\n *type*: array of string",
    )
    """
    *Device property*

    The CSP Vlbi Beam Capabilities FQDNs.

    *Type*: array of DevString
    """

    CspTelState = device_property(
        dtype='str', default_value="mid_csp/elt/telstate"
    )
    """
    *Device property*

    The CSP TelStatem FQDN.

    *Type*: DevString
    """

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
    """
    *Class attribute* 

    The device admininistrative mode.

    Note:
        This attribute is defined in SKABaseDevice Class from which CspMaster class inherits.\
        To override the attribute *write* method, the *adminMode* attribute is added again\
        ("overload" button enabled in POGO).
    """

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
    """
    *Class attribute*

    Percentage progress implemented for commands that result in state/mode transitions for\
            a large number of components and/or are executed in stages (e.g power up, power down)\n
    *Type*: DevUShort
    """

    cspCbfState = attribute(
        dtype='DevState',
        label="CBF status",
        polling_period=3000,
        doc="The CBF sub-element State.",
    )
    """
    *Class attribute*

    The CbfMaster *State* attribute value.\n
    *Type*: DevState
    """

    cspPssState = attribute(
        dtype='DevState',
        label="PSS status",
        polling_period=3000,
        doc="The PSS sub-element State.",
    )
    """
    *Class attribute*

    The PssMaster *State* attribute value.\n
    *Type*: DevState
    """

    cspPstState = attribute(
        dtype='DevState',
        label="PST status",
        polling_period=3000,
        doc="The PST sub-element State",
    )
    """
    *Class attribute*

    The PstMaster *State* attribute value.\n
    *Type*: DevState
    """

    cspCbfHealthState = attribute(
        dtype='DevEnum',
        label="CBF Health status",
        enum_labels=["OK", "DEGRADED", "FAILED", "UNKNOWN",],
        polling_period=3000,
        abs_change=1,
        doc="The CBF sub-element health status.",
    )
    """
    *Class attribute*

    The CbfMaster *healthState* attribute value.\n
    *Type*: DevUShort
    """

    cspPssHealthState = attribute(
        dtype='DevEnum',
        label="PSS Health status",
        enum_labels=["OK", "DEGRADED", "FAILED", "UNKNOWN",],
        polling_period=3000,
        abs_change=1,
        doc="The PSS sub-element health status",
    )
    """
    *Class attribute*

    The PssMaster *healthState* attribute value.\n
    *Type*: DevUShort
    """

    cspPstHealthState = attribute(
        dtype='DevEnum',
        label="PST health status",
        enum_labels=["OK", "DEGRADED", "FAILED", "UNKNOWN",],
        polling_period=3000,
        abs_change=1,
        doc="The PST sub-element health status.",
    )
    """
    *Class attribute*

    The PstMaster *healthState* attribute value.\n
    *Type*: DevUShort
    """

    cbfMasterAddress = attribute(
        dtype='str',
        doc="The Mid CbfMaster TANGO device FQDN",
    )
    """
    *Class attribute*

    The CbfMaster FQDN.\n
    *Type*: DevString
    """

    pssMasterAddress = attribute(
        dtype='str',
        doc="The Mid PssMaster TANGO device FQDN",
    )
    """
    *Class attribute*

    The PssMaster FQDN.\n
    *Type*: DevString
    """

    pstMasterAddress = attribute(
        dtype='str',
        doc="The Mid PstMaster TANGO device FQDN",
    )
    """
    *Class attribute*

    The PstMaster FQDN.\n
    *Type*: DevString
    """

    cbfAdminMode = attribute(
        dtype='DevEnum',
        access=AttrWriteType.READ_WRITE,
        label="CBF administrative Mode",
        polling_period=3000,
        abs_change=1,
        enum_labels=["ON-LINE", "OFF-LINE", "MAINTENANCE", "NOT-FITTED", "RESERVED", ],
        doc="The CbfMaster TANGO Device administration mode",
    )
    """
    *Class attribute*

    The CbfMaster *adminMode* attribute value.\n
    *Type*: DevUShort
    """

    pssAdminMode = attribute(
        dtype='DevEnum',
        access=AttrWriteType.READ_WRITE,
        label="PSS administrative mode",
        polling_period=3000,
        abs_change=1,
        enum_labels=["ON-LINE", "OFF-LINE", "MAINTENANCE", "NOT-FITTED", "RESERVED", ],
        doc="The PssMaster TANGO Device administration mode",
    )
    """
    *Class attribute*

    The PssMaster *adminMode* attribute value.\n
    *Type*: DevUShort
    """

    pstAdminMode = attribute(
        dtype='DevEnum',
        access=AttrWriteType.READ_WRITE,
        label="PST administrative mode",
        polling_period=3000,
        abs_change=1,
        enum_labels=["ON-LINE", "OFF-LINE", "MAINTENANCE", "NOT-FITTED", "RESERVED", ],
        doc="The PstMaster TANGO Device administration mode",
    )
    """
    *Class attribute*

    The PstMaster *adminMode* attribute value.\n
    *Type*: DevUShort
    """

    availableCapabilities = attribute(
        dtype=('str',),
        max_dim_x=20,
        doc="A list of available number of instances of each capability type, e.g. `CORRELATOR:512`, `PSS-BEAMS:4`.",
    )
    """
    *Class attribute* 

    The list of available instances of each capability type.

    Note:
        This attribute is defined in SKAMaster Class from which CspMaster class inherits.\
        To override the attribute *read* method, the *availableCapabilities* attribute is added again\
        ("overload" button enabled in POGO).
    """

    reportSearchBeamState = attribute(
        dtype=('DevState',),
        max_dim_x=1500,
        label="Search Beams state",
        doc="The State value of CSP SearchBeam Capabilities. Reported as an array of DevState.",
    )
    """
    *Class attribute*

    The *State* attribute value of the CSP SearchBeam Capabilities.\n
    *Type*: array of DevState.
    """

    reportSearchBeamHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=1500,
        label="Search Beams health status",
        doc="The healthState of the CSP SearchBeam Capabilities. Reported as an array \
             of ushort. For ex:\n[0,0,...,1..]",
    )
    """
    *Class attribute*

    The *healthState* attribute value of the CSP SearchBeam Capabilities.\n
    *Type*: array of DevUShort.
    """

    reportSearchBeamAdminMode = attribute(
        dtype=('uint16',),
        max_dim_x=1500,
        label="Search beams admin mode",
        doc="Report the administration mode of the search beams as an array \
             of unisgned short. Fo ex:\n[0,0,0,...2..]",
    )
    """
    *Class attribute*

    The *adminMode* attribute value of the CSP SearchBeam Capabilities.\n
    *Type*: array of DevUShort.
    """

    reportTimingBeamState = attribute(
        dtype=('DevState',),
        max_dim_x=16,
        label="Timing Beams state",
        doc="Report the state of the timing beams as an array of DevState.",
    )
    """
    *Class attribute*

    The *State* attribute value of the CSP TimingBeam Capabilities.\n
    *Type*: array of DevState.
    """

    reportTimingBeamHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=16,
        label="Timing Beams health status",
        doc="*TANGO Attribute*: healhState of the TimingBeam Capabilities as an array \
             of UShort.",
    )
    """
    *Class attribute*

    The *healthState* attribute value of the CSP TimingBeam Capabilities.\n
    *Type*: array of DevUShort.
    """

    reportTimingBeamAdminMode = attribute(
        dtype=('uint16',),
        max_dim_x=16,
        label="Timing beams admin mode",
        doc="Report the administration mode of the timing beams as an array \
             of unisgned short. For ex:\n[0,0,0,...2..]",
    )
    """
    *Class attribute*

    The *adminMode* attribute value of the CSP TimingBeam Capabilities.\n
    *Type*: array of DevUShort.
    """

    reportVlbiBeamState = attribute(
        dtype=('DevState',),
        max_dim_x=20,
        label="VLBI Beams state",
        doc="Report the state of the VLBI beams as an array of DevState.",
    )
    """
    *Class attribute*

    The *State* attribute value of the CSP VlbiBeam Capabilities.\n
    *Type*: array of DevState.
    """

    reportVlbiBeamHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=20,
        label="VLBI Beams health status",
        doc="Report the health status of the VLBI beams as an array \
             of unsigned short. For ex:\n[0,0,...,1..]",
    )
    """
    *Class attribute*

    The *healthState* attribute value of the CSP VlbiBeam Capabilities.\n
    *Type*: array of DevUShort.
    """

    reportVlbiBeamAdminMode = attribute(
        dtype=('uint16',),
        max_dim_x=20,
        label="VLBI beams admin mode",
        doc="Report the administration mode of the VLBI beams as an array \
             of unisgned short. For ex:\n[0,0,0,...2..]",
    )
    """
    *Class attribute*

    The *adminMode* attribute value of the CSP VlbiBeam Capabilities.\n
    *Type*: array of DevUShort.
    """

    cspSubarrayAddress = attribute(
        dtype=('str',),
        max_dim_x=16,
        doc="CSPSubarrays FQDN",
    )
    """
    *Class attribute*

    The CSPSubarray FQDNs.\n
    *Type*: Array of DevString
    """

    searchBeamCapAddress = attribute(
        dtype=('str',),
        max_dim_x=1500,
        label="SearchBeamCapabilities FQDNs",
        doc="SearchBeam Capabilities FQDNs",
    )
    """
    *Class attribute*

    The CSP SearchBeam Cpabailities FQDNs.\n
    *Type*: Array of DevString
    """

    timingBeamCapAddress = attribute(
        dtype=('str',),
        max_dim_x=16,
        label="TimingBeam Caapbilities FQDN",
        doc="TimingBeam Capabilities FQDNs.",
    )
    """
    *Class attribute*

    The CSP TimingBeam Cpabailities FQDNs.\n
    *Type*: Array of DevString
    """

    vlbiCapAddress = attribute(
        dtype=('str',),
        max_dim_x=20,
        label="VLBIBeam Capabilities FQDNs",
        doc="VLBIBeam Capablities FQDNs",
    )
    """
    *Class attribute*

    The CSP VlbiBeam Cpabailities FQDNs.\n
    *Type*: Array of DevString
    """

    receptorMembership = attribute(
        dtype=('uint16',),
        max_dim_x=197,
        label="Receptor Memebership",
        doc="The receptors affiliation to CSPsub-arrays.",
    )
    """
    *Class attribute*
    
    The receptors subarray affiliation.\n
    *Type*: array of DevUShort.
    """

    searchBeamMembership = attribute(
        dtype=('uint16',),
        max_dim_x=1500,
        label="SearchBeam Memebership",
        doc="The CSP sub-array affiliation of earch beams",
    )
    """
    *Class attribute*
    
    The SearchBeam Capabilities subarray affiliation.\n
    *Type*: array of DevUShort.
    """

    timingBeamMembership = attribute(
        dtype=('uint16',),
        max_dim_x=16,
        label="TimingBeam Membership",
        doc="The CSPSubarray affiliation of timing beams.",
    )
    """
    *Class attribute*
    
    The TimingBeam Capabilities subarray affiliation.\n
    *Type*: array of DevUShort.
    """

    vlbiBeamMembership = attribute(
        dtype=('uint16',),
        max_dim_x=20,
        label="VLBI Beam membership",
        doc="The CSPsub-rray affiliation of VLBI beams.",
    )
    """
    *Class attribute*
    
    The VlbiBeam Capabilities subarray affiliation.\n
    *Type*: array of DevUShort.
    """

    availableReceptorIDs = attribute(
        dtype=('uint16',),
        max_dim_x=197,
        label="Available receptors IDs",
        doc="The list of available receptors IDs.",
    )
    """
    *Class attribute*
    
    The available receptor IDs.\n
    *Type*: array of DevUShort.
    """

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

    The *State* attribute value of the Mid CBF Very Coarse Channel TANGO Devices.\n
    *Type*: array of DevState.

    *__root_att*: /mid_csp_cbf/sub_elt/master/reportVCCState

    Note: 
        If the *__root_att* attribute property is not  specified in the TANGO DB or the value doesn't\
            correspond to a valid attribute FQDN, the CspMaster *State* transits to ALARM.
    """

    reportVCCHealthState = attribute(name="reportVCCHealthState", label="reportVCCHealthState",
        forwarded=True
    )
    """
    *TANGO Forwarded attribute*.

    The *healthState* attribute value of the Mid CBF Very Coarse Channel TANGO Devices.\n
    *Type*:  an array of DevUShort.

    *__root_att*: /mid_csp_cbf/sub_elt/master/reportVCCHealthState
    """

    reportVCCAdminMode = attribute(name="reportVCCAdminMode", label="reportVCCAdminMode",
        forwarded=True
    )
    """
    *TANGO Forwarded attribute*.

    The *adminMode* attribute value of the Mid CBF Very Coarse Channel TANGO devices.\n
    *Type*: array of DevUShort.

    *__root_att*: /mid_csp_cbf/sub_elt/master/reportVccAdminMode  
    """

    reportFSPState = attribute(name="reportFSPState", label="reportFSPState",
        forwarded=True
    )
    """
    *TANGO Forwarded attribute*.

    The *State* attribute value of the Mid CBF Frequency Slice Processor TANGO devices.\n
    *Type*: array of DevState.

    *__root_att*: /mid_csp_cbf/sub_elt/master/reportFSPHealthState
    """

    reportFSPHealthState = attribute(name="reportFSPHealthState", label="reportFSPHealthState",
        forwarded=True
    )
    """
    *TANGO Forwarded attribute*.

    The *healthState* attribute value of the Mid CBF Frequency SLice Processor  TANGO Devices.\n
    *Type*:  an array of DevUShort.

    *__root_att*: /mid_csp_cbf/sub_elt/master/reportFSPHealthState
    """

    reportFSPAdminMode = attribute(name="reportFSPAdminMode", label="reportFSPAdminMode",
        forwarded=True
    )
    """
    *TANGO Forwarded attribute*.

    The *adminMode* attribute value of the Mid CBF Frequency SLice Processor  TANGO Devices.\n
    *Type*:  an array of DevUShort.

    *__root_att*: /mid_csp_cbf/sub_elt/master/reportFSPAdminMode
    """

    fspMembership = attribute(name="fspMembership", label="fspMembership",
        forwarded=True
    )
    """
    *TANGO Forwarded attribute*.

    The subarray affiliation of the Mid CBF Frequency SLice Processor  TANGO Devices.\n
    *Type*:  an array of DevUShort.

    *__root_att*: /mid_csp_cbf/sub_elt/master/fspMembership
    """

    vccMembership = attribute(name="vccMembership", label="vccMembership",
        forwarded=True
    )
    """
    *TANGO Forwarded attribute*.

    The subarray affiliation of the Mid CBF VCC TANGO Devices.\n
    *Type*:  an array of DevUShort.

    *__root_att*: /mid_csp_cbf/sub_elt/master/reportVCCSubarrayMembership
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
        self._available_receptorIDs = []

        # initialize attribute values
        self._progress_command = 0
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
        #self._se_fqdn.append(self.CspMidPss)
        #self._se_fqdn.append(self.CspMidPst)

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
        # initialize class attributes related to CBF receptors capabilities
        self._vcc_to_receptor_map = {}
        self._receptorsMembership = []
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
        """
        Method called on stop/reinit of the device.
        Release all the allocated resources.
        """
        # PROTECTED REGION ID(CspMaster.delete_device) ENABLED START #
        for fqdn in self._se_fqdn:
            try:
                event_to_remove = []
                for event_id in self._se_event_id[fqdn]:
                    try: 
                        self._se_proxies[fqdn].unsubscribe_event(event_id)
                        event_to_remove.append(event_id)
                    # NOTE: in PyTango unsubscription of not-existing event id raises a KeyError 
                    # exception not a DevFailed !!
                    except KeyError as key_err:
                        msg = "Can't retrieve the information of key {}".format(key_err)
                        self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
                    except tango.DevFailed as df:
                        msg = "Failure reason:" + str(df.args[0].reason) + " Desc:" + str(df.args[0].desc)
                        self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
                # remove the events id from the list
                for k in event_to_remove: 
                    self._se_event_id[fqdn].remove(k)
                # check if there are still some registered events. What to do in this case??
                if self._se_event_id[fqdn]:
                    msg = "Still subscribed events: {}".format(self._se_event_id)
                    self.dev_logging(msg, tango.LogLevel.LOG_WARN)
                else:
                    # remove the dictionary element
                    self._se_event_id.pop(fqdn)
            except KeyError as key_err:
                msg = " Can't retrieve the information of key {}".format(key_err)
                self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
        # clear any list and dict 
        self._se_fqdn.clear()
        self._se_proxies.clear()
        self._vcc_to_receptor_map.clear()
        self._receptorsMembership.clear()
        self._searchBeamsMembership.clear()
        self._timingBeamsMembership.clear()
        self._vlbiBeamsMembership.clear()
        self._se_to_switch_off.clear()
        # PROTECTED REGION END #    //  CspMaster.delete_device

    # PROTECTED REGION ID#    //  CspMaster private methods
    # PROTECTED REGION END #    //CspMaster private methods 

    # ------------------
    # Attributes methods
    # ------------------

    def write_adminMode(self, value):
        """
        Write attribute method.

        Set the administration mode for the whole CSP element.

        Args:  
            value: one of the administration mode value (ON-LINE,\
            OFF-LINE, MAINTENANCE, NOT-FITTED).
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
        Read attribute method.

        Returns: 
            The commandProgress attribute value.           
        """
        # PROTECTED REGION ID(CspMaster.commandProgress_read) ENABLED START #
        return self._progress_command
        # PROTECTED REGION END #    //  CspMaster.commandProgress_read

    def read_cspCbfState(self):
        """
        Read attribute method.

        Returns: 
            The CBF Sub-element *State* attribute value.           
        """
        # PROTECTED REGION ID(CspMaster.cspCbfState_read) ENABLED START #
        return self._cbf_state
        # PROTECTED REGION END #    //  CspMaster.cspCbfState_read

    def read_cspPssState(self):
        """
        Read attribute method.

        Returns: 
            The PSS Sub-element *State* attribute value.           
        """
        # PROTECTED REGION ID(CspMaster.cspPssState_read) ENABLED START #
        return self._pss_state
        # PROTECTED REGION END #    //  CspMaster.cspPssState_read

    def read_cspPstState(self):
        """
        Read attribute method.

        Returns: 
            The PST Sub-element *State* attribute value.           
        """
        # PROTECTED REGION ID(CspMaster.cspPstState_read) ENABLED START #
        return self._pst_state
        # PROTECTED REGION END #    //  CspMaster.cspPstState_read

    def read_cspCbfHealthState(self):
        """
        Read attribute method.

        Returns: 
            The CBF Sub-element *healthState* attribute value.           
        """
        # PROTECTED REGION ID(CspMaster.cspCbfHealthState_read) ENABLED START #
        return self._cbf_health_state
        # PROTECTED REGION END #    //  CspMaster.cspCbfHealthState_read

    def read_cspPssHealthState(self):
        """
        Read attribute method.

        Returns: 
            The PSS Sub-element *healthState* attribute value.           
        """
        # PROTECTED REGION ID(CspMaster.cspPssHealthState_read) ENABLED START #
        return self._pss_health_state
        # PROTECTED REGION END #    //  CspMaster.cspPssHealthState_read

    def read_cspPstHealthState(self):
        """
        Read attribute method.

        Returns: 
            The PST Sub-element *healthState* attribute value.           
        """
        # PROTECTED REGION ID(CspMaster.cspPstHealthState_read) ENABLED START #
        return self._pst_health_state
        # PROTECTED REGION END #    //  CspMaster.cspPstHealthState_read

    def read_cbfMasterAddress(self):
        """
        Read attribute method.

        Returns: 
            Return the CBS sub-element Master TANGO Device address.
        """
        # PROTECTED REGION ID(CspMaster.cbfMasterAddress_read) ENABLED START #
        return self.CspMidCbf
        # PROTECTED REGION END #    //  CspMaster.cbfMasterAddress_read

    def read_pssMasterAddress(self):
        """
        Read attribute method.

        Returns: 
            The PSS sub-element Master TANGO Device address.
        """
        # PROTECTED REGION ID(CspMaster.pssMasterAddress_read) ENABLED START #
        return self.CspMidPss
        # PROTECTED REGION END #    //  CspMaster.pssMasterAddress_read

    def read_pstMasterAddress(self):
        """
        Read attribute method.

        Returns: 
           The PST sub-element Master TANGO Device address.
        """
        # PROTECTED REGION ID(CspMaster.pstMasterAddress_read) ENABLED START #
        return self.CspMidPst
        # PROTECTED REGION END #    //  CspMaster.pstMasterAddress_read

    def read_cbfAdminMode(self):
        """
        Read attribute method.

        Returns: 
            The CBF sub-element *adminMode* attribute value.
        """
        # PROTECTED REGION ID(CspMaster.pssAdminMode_read) ENABLED START #
        return self._cbf_admin_mode
        # PROTECTED REGION END #    //  CspMaster.cbfAdminMode_read

    def write_cbfAdminMode(self, value):
        # PROTECTED REGION ID(CspMaster.cbfAdminMode_write) ENABLED START #
        """
        Write attribute method.

        Set the CBF sub-element *adminMode* attribute value.

        Args:  
            value: one of the administration mode value (ON-LINE,\
            OFF-LINE, MAINTENANCE, NOT-FITTED).
        Returns: 
            None
        Raises:
            tango.DevFailed: raised when there is no DeviceProxy providing interface to the CBF sub-element\
            Master, or an exception is caught in command execution.
        """
        if self.__is_subelement_available(self.CspMidCbf):
            try:
                cbf_proxy = self._se_proxies[self.CspMidCbf]
                cbf_proxy.adminMode = value
            except tango.DevFailed as df: 
                tango.Except.throw_exception("Command failed", str(df.args[0].desc),
                                             "Set cbf admin mode", tango.ErrSeverity.ERR)
            except KeyError as key_err:
                msg = "Can't retrieve the information of key {}".format(key_err)
                self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
                tango.Except.throw_exception("Command failed", msg,
                                             "Set cbf admin mode", tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CspMaster.cbfAdminMode_write

    def read_pssAdminMode(self):
        """
        Read attribute method.

        Returns: 
            The PSS sub-element *adminMode* attribute value.
        """
        # PROTECTED REGION ID(CspMaster.pssAdminMode_read) ENABLED START #
        return self._pss_admin_mode
        # PROTECTED REGION END #    //  CspMaster.pssAdminMode_read

    def write_pssAdminMode(self, value):
        """
        Write attribute method.

        Set the PSS sub-element *adminMode* attribute value.

        Args:  
            value: one of the administration mode value (ON-LINE,\
            OFF-LINE, MAINTENANCE, NOT-FITTED).
        Returns: 
            None
        Raises:
            tango.DevFailed: raised when there is no DeviceProxy providing interface to the PSS sub-element\
            Master, or an exception is caught in command execution.
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
        Read attribute method.

        Returns: 
            The PST sub-element *adminMode* attribute value.
        """
        # PROTECTED REGION ID(CspMaster.pstAdminMode_read) ENABLED START #
        return self._pst_admin_mode
        # PROTECTED REGION END #    //  CspMaster.pstAdminMode_read

    def write_pstAdminMode(self, value):
        """
        Write attribute method.

        Set the PST sub-element *adminMode* attribute value.

        Args:  
            value: one of the administration mode value (ON-LINE,\
            OFF-LINE, MAINTENANCE, NOT-FITTED).
        Returns: 
            None
        Raises:
            tango.DevFailed: raised when there is no DeviceProxy providing interface to the PST sub-element\
            Master, or an exception is caught in command execution.
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
        Override read attribute method.

        Returns:
            A list of strings with the number of available resources for each
            capability/resource type.
        Example: 
            ["Receptors:95", "SearchBeam:1000", "TimingBeam:16", "VlbiBeam:20"]
        Raises:
            tango.DevFailed: raised when information can't be retrieved
        """
        # PROTECTED REGION ID(CspMaster.availableCapabilities_read) ENABLED START #
        self._available_capabilities = {}
        try:
            proxy = tango.DeviceProxy(self.get_name())
            available_receptors = proxy.availableReceptorIDs
            #oss: if there is no available receptor, this call returns an array
            # [0] whose length is 1 (not 0)
            if len(available_receptors) >= 1:
                if available_receptors[0] == 0:
                    self._available_capabilities["Receptors"] = 0
                else:    
                    self._available_capabilities["Receptors"] = len(available_receptors)
            #TODO: update when also PSS and PST will be available
            self._available_capabilities["SearchBeam"] = const.NUM_OF_SEARCH_BEAMS
            self._available_capabilities["TimingBeam"] = const.NUM_OF_TIMING_BEAMS
            self._available_capabilities["VlbiBeam"] = const.NUM_OF_VLBI_BEAMS
        except tango.DevFailed as df:
            #TODO: add message logging
            tango.Except.throw_exception("Attribute reading failure", df.args[0].desc,
                                         "read_availableCapabilities", tango.ErrSeverity.ERR)
        except AttributeError as attr_err: 
            msg = "Error in reading {}: {} ".format(str(attr_err.args[0]), attr_err.__doc__)
            tango.Except.throw_exception("Attribute reading failure", msg,
                                         "read_availableCapabilities", 
                                         tango.ErrSeverity.ERR)
        return utils.convert_dict_to_list(self._available_capabilities)
        # PROTECTED REGION END #    //  CspMaster.availableCapabilities_read

    def read_reportSearchBeamState(self):
        """
        Read attribute method.

        Returns: 
            The *State* value of the CSP SearchBeam Capabilities.\n
            *Type*: array of DevState.
        """
        # PROTECTED REGION ID(CspMaster.reportSearchBeamState_read) ENABLED START #
        return self._search_beams_state
        # PROTECTED REGION END #    //  CspMaster.reportSearchBeamState_read

    def read_reportSearchBeamHealthState(self):
        """
        Read atttribute method.

        Returns: 
            The *healthState* attribute value of the CSP SearchBeam Capabilities.\n
            *Type*: array of DevUShort
        """
        # PROTECTED REGION ID(CspMaster.reportSearchBeamHealthState_read) ENABLED START #
        return self._search_beams_health_state
        # PROTECTED REGION END #    //  CspMaster.reportSearchBeamHealthState_read

    def read_reportSearchBeamAdminMode(self):
        """
        Read attribute method.

        Returns: 
            The *adminMode* of the CSP SearchBeam Capabilities.\n
            *Type*: array of DevUShort
        """
        # PROTECTED REGION ID(CspMaster.reportSearchBeamAdminMode_read) ENABLED START #
        return self._search_beams_admin
        # PROTECTED REGION END #    //  CspMaster.reportSearchBeamAdminMode_read

    def read_reportTimingBeamState(self):
        """
        Read attribute method.

        Returns: 
            The *State* value of the CSP TimingBeam Capabilities.\n
            *Type*: array of DevState.
        """
        # PROTECTED REGION ID(CspMaster.reportTimingBeamState_read) ENABLED START #
        return self._timing_beams_state
        # PROTECTED REGION END #    //  CspMaster.reportTimingBeamState_read

    def read_reportTimingBeamHealthState(self):
        """
        Read attribute method.

        Returns: 
            The *healthState* value of the CSP TimingBeam Capabilities.\n
            *Type*: array of DevUShort.
        """
        # PROTECTED REGION ID(CspMaster.reportTimingBeamHealthState_read) ENABLED START #
        return self._timing_beams_health_state
        # PROTECTED REGION END #    //  CspMaster.reportTimingBeamHealthState_read

    def read_reportTimingBeamAdminMode(self):
        """
        Read attribute method.

        Returns: 
            The *adminMode* value of the CSP TimingBeam Capabilities.\n
            *Type*: array of DevUShort.
        """
        # PROTECTED REGION ID(CspMaster.reportTimingBeamAdminMode_read) ENABLED START #
        return self._timing_beams_admin 
        # PROTECTED REGION END #    //  CspMaster.reportTimingBeamAdminMode_read

    def read_reportVlbiBeamState(self):
        """
        Read attribute method.

        Returns: 
            The *State* value of the CSP VlbiBeam Capabilities.\n
            *Type*: array of DevState.
        """
        # PROTECTED REGION ID(CspMaster.reportVlbiBeamState_read) ENABLED START #
        return self._vlbi_beams_state
        # PROTECTED REGION END #    //  CspMaster.reportVlbiBeamState_read

    def read_reportVlbiBeamHealthState(self):
        """
        Read attribute method.

        Returns: 
            The *healthState* value of the CSP VlbiBeam Capabilities.\n
            *Type*: array of DevUShort.
        """
        # PROTECTED REGION ID(CspMaster.reportVlbiBeamHealthState_read) ENABLED START #
        return self._vlbi_beams_health_state
        # PROTECTED REGION END #    //  CspMaster.reportVlbiBeamHealthState_read

    def read_reportVlbiBeamAdminMode(self):
        """
        Read attribute method.

        Returns: 
            The *adminMode* value of the CSP VlbiBeam Capabilities.\n
            *Type*: array of DevUShort.
        """
        # PROTECTED REGION ID(CspMaster.reportVlbiBeamAdminMode_read) ENABLED START #
        return self._vlbi_beams_admin
        # PROTECTED REGION END #    //  CspMaster.reportVlbiBeamAdminMode_read
    
    def read_cspSubarrayAddress(self):
        """
        Read attribute method.

        Returns:
            The CSP Subarrays FQDNs.\n
            *Type*: array of DevString
        Raises:
            tango.DevFailed: raised if the CspSubarray Device Property is not defined into the TANGO DB\
                    or no default value is assigned.
        """
        # PROTECTED REGION ID(CspMaster.cspSubarrayAddress_read) ENABLED START #
        if self.CspSubarrays:
            return self.CspSubarrays
        else:
            log_msg = "CspSubarrays device property not defined"
            self.dev_logging(log_msg, tango.LogLevel.LOG_WARN)
            tango.Except.throw_exception("Attribute reading failure", log_msg,
                                     "read_cspSubarrayAddress", tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CspMaster.cspSubarrayAddress_read

    def read_searchBeamCapAddress(self):
        """
        Read attribute method.

        Returns:
            The CSP SearchBeam Capabilities FQDNs.\n
            *Type*: array of DevString
        Raises:
            tango.DevFailed: raised if the SearchBeams Device Property is not defined into the TANGO DB\
                    or no default value is assigned.
        """
        # PROTECTED REGION ID(CspMaster.searchBeamCapAddress_read) ENABLED START #
        if self.SearchBeams: 
            return self.SearchBeams
        else :
            log_msg = "SearchBeams device property not assigned"
            self.dev_logging(log_msg, tango.LogLevel.LOG_WARN)
            tango.Except.throw_exception("Attribute reading failure", log_msg,
                                         "read_searchBeamCapAddress", tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CspMaster.searchBeamCapAddress_read

    def read_timingBeamCapAddress(self):
        # PROTECTED REGION ID(CspMaster.timingBeamCapAddress_read) ENABLED START #
        if self.TimingBeams: 
            return self.TimingBeams
        else :
            log_msg = "TimingBeams device property not assigned"
            self.dev_logging(log_msg, tango.LogLevel.LOG_WARN)
            tango.Except.throw_exception("Attribute reading failure", log_msg,
                                         "read_timingBeamCapAddress", tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CspMaster.timingBeamCapAddress_read

    def read_vlbiCapAddress(self):
        """
        Class attribute method.
        """

        # PROTECTED REGION ID(CspMaster.vlbiCapAddress_read) ENABLED START #
        if self.VlbiBeams: 
            return self.VlbiBeams
        else :
            log_msg = "VlbiBeams device property not assigned" 
            self.dev_logging(log_msg, tango.LogLevel.LOG_WARN)
            tango.Except.throw_exception("Attribute reading failure", log_msg,
                                         "read_vlbiBeamCapAddress", tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CspMaster.vlbiCapAddress_read

    def read_receptorMembership(self):
        """
        Class attribute method.

        Returns:
           The subarray affilitiaion of the receptors.
        """
        # PROTECTED REGION ID(CspMaster.receptorMembership_read) ENABLED START #
        if self.__is_subelement_available(self.CspMidCbf):
            try: 
                proxy = self._se_proxies[self.CspMidCbf]
                proxy.ping()
                vcc_membership = proxy.reportVccSubarrayMembership
                vcc_id_list = list(self._vcc_to_receptor_map.keys())
                for vcc_id in vcc_id_list:
                    receptorID = self._vcc_to_receptor_map[vcc_id]
                    self._receptorsMembership[receptorID - 1] = vcc_membership[vcc_id - 1]
            except tango.DevFailed as df: 
                tango.Except.re_throw_exception(df, "CommandFailed",
                                                    "read_receptorsMembership failed", 
                                                    "Command()")
            except KeyError as key_err: 
                msg = "Can't retrieve the information of key {}".format(key_err)
                self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
                tango.Except.throw_exception("Attribute reading failure", msg,
                                             "read_receptorMembership", tango.ErrSeverity.ERR)
            except AttributeError as attr_err: 
                msg = "Error in reading {}: {} ".format(str(attr_err.args[0]), attr_err.__doc__)
                tango.Except.throw_exception("Attribute reading failure", msg,
                                             "read_receptorMembership", 
                                             tango.ErrSeverity.ERR)
        return self._receptorsMembership
        # PROTECTED REGION END #    //  CspMaster.receptorMembership_read

    def read_searchBeamMembership(self):
        """
        Class attribute method.

        Returns:
           The subarray affilitiaion of the Search Beams.
        """
        # PROTECTED REGION ID(CspMaster.searchBeamMembership_read) ENABLED START #
        return self._searchBeamsMembership
        # PROTECTED REGION END #    //  CspMaster.searchBeamMembership_read

    def read_timingBeamMembership(self):
        """
        Class attribute method.

        Returns:
           The subarray affilitiaion of the Timing Beams.
        """
        # PROTECTED REGION ID(CspMaster.timingBeamMembership_read) ENABLED START #
        return self._timingBeamsMembership
        # PROTECTED REGION END #    //  CspMaster.timingBeamMembership_read

    def read_vlbiBeamMembership(self):
        """
        Class attribute method.

        Returns:
           The subarray affilitiaion of the Vlbi Beams.
        """
        # PROTECTED REGION ID(CspMaster.vlbiBeamMembership_read) ENABLED START #
        return self._vlbiBeamsMembership
        # PROTECTED REGION END #    //  CspMaster.vlbiBeamMembership_read

    def read_availableReceptorIDs(self):
        """
        Read attribute method.

        Returns:
            The list of the available receptors IDs.
            The list includes all the receptors that are not assigned to any subarray and, 
            from the side of CSP, are considered "full working". This means:\n
            * a valid link connection receptor-VCC\n 
            * the connected VCC healthState OK

            *Type*: array of DevUShort
        Raises:
            tango.DevFailed: if there is no DeviceProxy providing interface to the\
                    CBF sub-element Master Device or an error is caught during\
                    command execution.
        """
        # PROTECTED REGION ID(CspMaster.availableReceptorIDs_read) ENABLED START #
        self._available_receptorIDs = []
        try:
            proxy = self._se_proxies[self.CspMidCbf]
            proxy.ping()
            vcc_state = proxy.reportVCCState
            vcc_membership = proxy.reportVccSubarrayMembership
            # get the list with the IDs of the available VCC
            for vcc_id in list(self._vcc_to_receptor_map.keys()):
                try:
                    if vcc_state[vcc_id - 1] not in [tango.DevState.UNKNOWN]:
                        # skip the vcc already assigned to a sub-array
                        if vcc_membership[vcc_id - 1] != 0:
                            continue
                        # OSS: valid receptorIDs are in [1,197] range
                        # receptorID = 0 means the link connection between 
                        # the receptor and the VCC is off
                        receptorID = self._vcc_to_receptor_map[vcc_id]
                        if receptorID > 0:
                            self._available_receptorIDs.append(receptorID)
                        else:
                            log_msg = "Link problem with receptor connected\
                                    to Vcc {}".format(vcc_id + 1)
                            self.dev_logging(log_msg, tango.LogLevel.LOG_WARN)
                except KeyError as key_err:
                    log_msg = "No key {} found while accessing VCC {}".format(str(key_err), vcc_id)
                    self.dev_logging(log_msg, tango.LogLevel.LOG_WARN)
                except IndexError as idx_error:
                    log_msg = "Error accessing VCC element {}: {}".format(vcc_id, str(idx_error))
                    self.dev_logging(log_msg, tango.LogLevel.LOG_WARN)
        except KeyError as key_err:
            log_msg = "Can't retrieve the information of key {}".format(key_err)
            tango.Except.throw_exception("Attribute reading failure", log_msg,
                                         "read_availableReceptorIDs", tango.ErrSeverity.ERR)
        except tango.DevFailed as df:
            log_msg = "Error in read_availableReceptorIDs: " + df.args[0].reason
            self.dev_logging(log_msg, int(tango.LogLevel.LOG_ERROR))
            tango.Except.throw_exception("Attribute reading failure", log_msg,
                                         "read_availableReceptorIDs", tango.ErrSeverity.ERR)
        except AttributeError as attr_err: 
            msg = "Error in reading {}: {} ".format(str(attr_err.args[0]), attr_err.__doc__)
            tango.Except.throw_exception("Attribute reading failure", msg,
                                         "read_availableReceptorIDs", 
                                         tango.ErrSeverity.ERR)
        # !!!
        # 2019-10-18
        # NOTE: with the new TANGO/PyTango images release (PyTango 9.3.1, TANGO 9.3.3, numpy 1.17.2)
        # the issue of "DeviceAttribute object has no attribute 'value'" has been resolved. Now
        # a TANGO RO attribute initializaed to an empty list (see self._available_receptorIDs), 
        # returns a NoneType object, as happed before with PyTango 9.2.5, TANGO 9.2.5 images.
        # The beaviour now is coherent, but I don't revert to the old code: this methods keep returning
        # an array with one element = 0 when no receptors are available.
        if len(self._available_receptorIDs) == 0:
            return [0]
        return self._available_receptorIDs
        # PROTECTED REGION END #    //  CspMaster.vlbiBeamMembership_read

    # --------
    # Commands
    # --------

    def is_On_allowed(self):
        """
        *TANGO is_allowed method*

        Command *On* is allowed when:\n
        * state is STANDBY and adminMode = MAINTENACE or ONLINE (end state = ON)\n
        * state is STANDBY and adminMode = OFFLINE, NOTFITTED   (end state = DISABLE)\n
        * state is DISABLE and adminMode = MAINTENACE or ONLINE (end state = ON)

        Returns:
            True if the method is allowed, otherwise False.
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
        """
        *Class method*

        Switch-on the CSP sub-elements specified by the input argument. If no argument is\
                specified, the command is issued to all the CSP sub-elements.

        Args:
            argin: the list of sub-element FQDNs to switch-on or an empty list to switch-on\
                    the whole CSP Element.
            Type: DevVarStringArray
        Returns:
            None
        Raises:
            tango.DevFailed: if an exception is caught processing the On command for\
                    the CBF sub-element or there are no DeviceProxy providing interface\
                    to the CSP sub-elements.
        """
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
                device_proxy.command_inout("On")
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
        *TANGO is_allowed method*

        Command *Off* is allowed when the device *State* is STANDBY.

        Returns:
            True if the method is allowed, otherwise False.
        """
        # PROTECTED REGION ID(CspMaster.is_On_allowed) ENABLED START #
        if self.get_state() not in [tango.DevState.STANDBY]:
            return False
        return True

    @command(
        dtype_in=('str',), 
        doc_in="If the array length is 0, the command applies to the whole CSP Element.\
If the array length is > 1, each array element specifies the FQDN of the\
 CSP SubElement to switch OFF."

    )
    @DebugIt()
    def Off(self, argin):
        """
        Switch-off the CSP sub-elements specified by the input argument. If no argument is\
                specified, the command is issued to all the CSP sub-elements.

        Args:
            The list of sub-elements to switch-off. If the array\
            length is 0, the command applies to the whole CSP Element.\
            If the array length is > 1, each array element specifies the FQDN of the\
            CSP SubElement to switch OFF \n

        Returns: 
            None

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
                device_proxy.command_inout("Off")
                self._se_to_switch_off[device_name] = True
            except KeyError as error:
                err_msg = "No proxy for device" + str(error)
                self.dev_logging(err_msg, int(tango.LogLevel.LOG_ERROR))
            except tango.DevFailed as df:
                self.dev_logging(str(df.args[0].desc), int(tango.LogLevel.LOG_ERROR))

        # PROTECTED REGION END #    //  CspMaster.Off

    def is_Standby_allowed(self):
        """
        *TANGO is_allowed method*

        Command *Standby* is allowed when the device *State* is ON, DISABLE or ALARM.

        Returns:
            True if the method is allowed, otherwise False.
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
        Transit to STANDBY the CSP sub-elements specified by the input argument. If no argument is\
                specified, the command is issued to all the CSP sub-elements.

        Args: 
            argin: The list of the Sub-element devices FQDNs 
            Type: DevVarStringArray
        Returns: 
            None
        Raises:
            tango.DevFailed: if command fails or if no DeviceProxy associated to the FQDNs.
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
                device_proxy.command_inout("Standby")
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
