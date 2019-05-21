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
from tango import DebugIt, EventType, DeviceProxy
from tango.server import run, DeviceMeta, attribute, command, device_property

# add the path to import global_enum package.
file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

# Additional import
# PROTECTED REGION ID(CspMaster.additionnal_import) ENABLED START #
#
from global_enum import HealthState, AdminMode
from skabase.SKAMaster.SKAMaster import SKAMaster
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
        Retrieve the values of the sub-element SCM attributes subscribed for change
        event at device initialization.
        :param evt: A TANGO_CHANGE event on Subarray healthState.
        :return: None
        """
        unknown_device = False
        if evt.err is False:
            try:
                if ("state" == evt.attr_value.name) or ("State" == evt.attr_value.name):
                    if self.CspMidCbf in evt.attr_name:
                        self._cbf_state = evt.attr_value.value
                    elif self.CspMidPss in evt.attr_name:
                        self._pss_state = evt.attr_value.value
                    elif self.CspMidPst in evt.attr_name:
                        self._pst_state = evt.attr_value.value
                    else:
                        # should NOT happen!
                        unknown_device = True    
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
                if "adminmode" in evt.attr_name: 
                    if self.CspMidCbf in evt.attr_name:
                        self._cbf_admin_mode = evt.attr_value.value
                    elif self.CspMidPss in evt.attr_name:
                        self._pss_admin_mode = evt.attr_value.value
                    elif self.CspMidPst in evt.attr_name:
                        self._pst_admin_mode = evt.attr_value.value
                    else:
                        # should NOT happen!
                        unknown_device = True    

                if unknown_device == True:
                    log_msg = "Unexpected change event for attribute: " + \
                                  str(evt.attr_name)
                    self.dev_logging(log_msg, tango.LogLevel.LOG_WARN)
                    return

                log_msg = "New value for " + str(evt.attr_name) + " is " + \
                          str(evt.attr_value.value) 
                self.dev_logging(log_msg, tango.LogLevel.LOG_INFO)
                # update CSP global state
                self.__set_csp_state()
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
                    # PSS sub-element
                    if self.CspMidPss in evt.attr_name:
                        self._pss_state = tango.DevState.UNKNOWN
                        self._pss_health_state = HealthState.UNKNOWN.value
                    # PST sub-element
                    if self.CspMidPst in evt.attr_name:
                        self._pst_state = tango.DevState.UNKNOWN
                        self._pst_health_state = HealthState.UNKNOWN.value
                    # update the State and healthState of the CSP Element
                    self.__set_csp_state()
                log_msg = item.reason + ": on attribute " + str(evt.attr_name)
                self.dev_logging(log_msg, tango.LogLevel.LOG_WARN)

    # ---------------
    # Class private methods
    # ---------------
    def __set_csp_state(self):
        """
        Retrieve the iState attribute of the CSP sub-element and aggregate them to build 
        up the CSP global state
        :param  None
        :return None
        """

        self.__set_csp_health_state()
        # CSP state reflects the status of CBF. Only if CBF is present CSP can work.
        # The state of PSS and PST sub-elements only contributes to determine the CSP
        # health state.
        self.set_state(self._cbf_state)

    def __set_csp_health_state(self):
        """
        Retrieve the healthState attribute of the CSP sub-elements and aggregate them
        to build up the CSP health state
        :param  None
        :return None
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
    # PROTECTED REGION END #    //  CspMaster.class_variable

    # -----------------
    # Device Properties
    # -----------------

    CspMidCbf = device_property(
        dtype='str', default_value="mid_csp_cbf/sub_elt/master"
    )

    CspMidPss = device_property(
        dtype='str', default_value="mid_csp_pss/sub_elt/master"
    )

    CspMidPst = device_property(
        dtype='str', default_value="mid_csp_pst/sub_elt/master"
    )

    # ----------
    # Attributes
    # ----------

    commandProgress = attribute(
        dtype='uint16',
        label="Command progress percentage",
        max_value=100,
        min_value=0,
        polling_period=3000,
        abs_change=5,
        rel_change=2,
        doc="Percentage progress implemented for commands that  result in state/mode \
             transitions for a large \nnumber of components and/or are executed in \
             stages (e.g power up, power down)",
    )

    cspCbfState = attribute(
        dtype='DevState',
        label="CBF status",
        polling_period=3000,
        doc="The CBF sub-element status.",
    )

    cspPssState = attribute(
        dtype='DevState',
        label="PSS status",
        polling_period=3000,
        doc="The PSS sub-element status.",
    )

    cspPstState = attribute(
        dtype='DevState',
        label="PST status",
        polling_period=3000,
        doc="The PST sub-element status",
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

    reportVCCState = attribute(
        dtype=('DevState',),
        max_dim_x=197,
        label="VCC state",
        polling_period=3000,
        doc="Report he state of the VCC capabilities as an array of DevState",
    )

    reportVCCHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=197,
        label="VCC health status",
        polling_period=3000,
        abs_change=1,
        doc="Report the health status of VCC capabilities as an array \
             of unsigned short.\nEx:\n[0,0,0,2,0...3]",
    )

    reportVCCAdminMode = attribute(
        dtype=('uint16',),
        max_dim_x=197,
        label="VCC admin mode",
        polling_period=3000,
        abs_change=1,
        doc="Report the administration mode of the VCC capabilities as an array \
             of unisgned short.\nFor ex.:\n[0,0,0,...1,2]",
    )

    reportFSPState = attribute(
        dtype=('DevState',),
        max_dim_x=27,
        label="FSP state",
        polling_period=3000,
        doc="Report the state of the FSP capabilities.",
    )

    reportFSPHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=27,
        label="FSP health status",
        polling_period=3000,
        abs_change=1,
        doc="Report the health status of the FSP capabilities.",
    )

    reportFSPAdminMode = attribute(
        dtype=('uint16',),
        max_dim_x=27,
        label="FSP admin mode",
        polling_period=3000,
        abs_change=1,
        doc="Report the administration mode of the FSP capabilities as an array \
             of unisgned short.\nfor ex:\n[0,0,2,..]",
    )

    reportSearchBeamState = attribute(
        dtype=('DevState',),
        max_dim_x=1500,
        label="Search Beams state",
        polling_period=3000,
        doc="Report the state of the search beams as an array of DevState.",
    )

    reportSearchBeamHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=1500,
        label="Search Beams health status",
        polling_period=3000,
        abs_change=1,
        doc="Report the health status of the search beams as an array \
             of unsigned short. For ex:\n[0,0,...,1..]",
    )

    reportSearchBeamAdminMode = attribute(
        dtype=('uint16',),
        max_dim_x=1500,
        label="Search beams admin mode",
        polling_period=3000,
        abs_change=1,
        doc="Report the administration mode of the search beams as an array \
             of unisgned short. Fo ex:\n[0,0,0,...2..]",
    )

    reportTimingBeamState = attribute(
        dtype=('DevState',),
        max_dim_x=16,
        label="Timing Beams state",
        polling_period=3000,
        doc="Report the state of the timing beams as an array of DevState.",
    )

    reportTimingBeamHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=16,
        label="Timing Beams health status",
        polling_period=3000,
        abs_change=1,
        doc="Report the health status of the timing beams as an array \
             of unsigned short. For ex:\n[0,0,...,1..]",
    )

    reportTimingBeamAdminMode = attribute(
        dtype=('uint16',),
        max_dim_x=16,
        label="Timing beams admin mode",
        polling_period=3000,
        abs_change=1,
        doc="Report the administration mode of the timing beams as an array \
             of unisgned short. For ex:\n[0,0,0,...2..]",
    )

    reportVLBIBeamState = attribute(
        dtype=('DevState',),
        max_dim_x=20,
        label="VLBI Beams state",
        polling_period=3000,
        doc="Report the state of the VLBI beams as an array of DevState.",
    )

    reportVLBIBeamHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=20,
        label="VLBI Beams health status",
        polling_period=3000,
        abs_change=1,
        doc="Report the health status of the VLBI beams as an array \
             of unsigned short. For ex:\n[0,0,...,1..]",
    )

    reportVLBIBeamAdminMode = attribute(
        dtype=('uint16',),
        max_dim_x=16,
        label="VLBI beams admin mode",
        polling_period=3000,
        abs_change=1,
        doc="Report the administration mode of the VLBI beams as an array \
             of unisgned short. For ex:\n[0,0,0,...2..]",
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKAMaster.init_device(self)
        # PROTECTED REGION ID(CspMaster.init_device) ENABLED START #
        self.set_state(tango.DevState.INIT)

        # initialize attribute values
        self._progress_command = 0;

        # sub-element State and healthState initialization
        self._cbf_state        = tango.DevState.UNKNOWN
        self._cbf_health_state = HealthState.UNKNOWN.value
        self._cbf_admin_mode   = AdminMode.ONLINE.value
        self._pss_state        = tango.DevState.UNKNOWN
        self._pss_health_state = HealthState.UNKNOWN.value 
        self._pss_admin_mode   = AdminMode.ONLINE.value
        self._pst_state        = tango.DevState.UNKNOWN
        self._pst_health_state = HealthState.UNKNOWN.value
        self._pst_admin_mode   = AdminMode.ONLINE.value

        # set storage logging level to INFO 
        self._storage_logging_level = int(tango.LogLevel.LOG_INFO)
        # set element logging level to INFO  
        self._element_logging_level = int(tango.LogLevel.LOG_INFO)

        # evaluate the CSP element global State and healthState
        self.__set_csp_state()

        # initialize list with CSP sub-element FQDNs
        self._se_fqdn = []
        # build the list with the CSP sub-element FQDN
        self._se_fqdn.append(self.CspMidCbf)
        self._se_fqdn.append(self.CspMidPss)
        self._se_fqdn.append(self.CspMidPst)

        # initialize the dictionary with sub-element proxies
        self._se_proxies = {}
        # dictionary with list of event ids/sub-element. Need to store the event
        # ids for each sub-element to un-subscribe them at sub-element disconnection.
        self._se_event_id = {}

        # Try connection with each sub-element
        for fqdn in self._se_fqdn:
            # initialize the list for each dictionary key-name
            self._se_event_id[fqdn] = []
            try:
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

    def read_commandProgress(self):
        # PROTECTED REGION ID(CspMaster.commandProgress_read) ENABLED START #
        return self._progress_command
        # PROTECTED REGION END #    //  CspMaster.commandProgress_read

    def read_cspCbfState(self):
        # PROTECTED REGION ID(CspMaster.cspCbfState_read) ENABLED START #
        return self._cbf_state
        # PROTECTED REGION END #    //  CspMaster.cspCbfState_read

    def read_cspPssState(self):
        # PROTECTED REGION ID(CspMaster.cspPssState_read) ENABLED START #
        return self._pss_state
        # PROTECTED REGION END #    //  CspMaster.cspPssState_read

    def read_cspPstState(self):
        # PROTECTED REGION ID(CspMaster.cspPstState_read) ENABLED START #
        return self._pst_state
        # PROTECTED REGION END #    //  CspMaster.cspPstState_read

    def read_cspCbfHealthState(self):
        # PROTECTED REGION ID(CspMaster.cspCbfHealthState_read) ENABLED START #
        return self._cbf_health_state
        # PROTECTED REGION END #    //  CspMaster.cspCbfHealthState_read

    def read_cspPssHealthState(self):
        # PROTECTED REGION ID(CspMaster.cspPssHealthState_read) ENABLED START #
        return self._pss_health_state
        # PROTECTED REGION END #    //  CspMaster.cspPssHealthState_read

    def read_cspPstHealthState(self):
        # PROTECTED REGION ID(CspMaster.cspPstHealthState_read) ENABLED START #
        return self._pst_health_state
        # PROTECTED REGION END #    //  CspMaster.cspPstHealthState_read

    def read_reportVCCState(self):
        # PROTECTED REGION ID(CspMaster.reportVCCState_read) ENABLED START #
        return [tango.DevState.UNKNOWN]
        # PROTECTED REGION END #    //  CspMaster.reportVCCState_read

    def read_reportVCCHealthState(self):
        # PROTECTED REGION ID(CspMaster.reportVCCHealthState_read) ENABLED START #
        return [0]
        # PROTECTED REGION END #    //  CspMaster.reportVCCHealthState_read

    def read_reportVCCAdminMode(self):
        # PROTECTED REGION ID(CspMaster.reportVCCAdminMode_read) ENABLED START #
        return [0]
        # PROTECTED REGION END #    //  CspMaster.reportVCCAdminMode_read

    def read_reportFSPState(self):
        # PROTECTED REGION ID(CspMaster.reportFSPState_read) ENABLED START #
        return [tango.DevState.UNKNOWN]
        # PROTECTED REGION END #    //  CspMaster.reportFSPState_read

    def read_reportFSPHealthState(self):
        # PROTECTED REGION ID(CspMaster.reportFSPHealthState_read) ENABLED START #
        return [0]
        # PROTECTED REGION END #    //  CspMaster.reportFSPHealthState_read

    def read_reportFSPAdminMode(self):
        # PROTECTED REGION ID(CspMaster.reportFSPAdminMode_read) ENABLED START #
        return [0]
        # PROTECTED REGION END #    //  CspMaster.reportFSPAdminMode_read

    def read_reportSearchBeamState(self):
        # PROTECTED REGION ID(CspMaster.reportSearchBeamState_read) ENABLED START #
        return [tango.DevState.UNKNOWN]
        # PROTECTED REGION END #    //  CspMaster.reportSearchBeamState_read

    def read_reportSearchBeamHealthState(self):
        # PROTECTED REGION ID(CspMaster.reportSearchBeamHealthState_read) ENABLED START #
        return [0]
        # PROTECTED REGION END #    //  CspMaster.reportSearchBeamHealthState_read

    def read_reportSearchBeamAdminMode(self):
        # PROTECTED REGION ID(CspMaster.reportSearchBeamAdminMode_read) ENABLED START #
        return [0]
        # PROTECTED REGION END #    //  CspMaster.reportSearchBeamAdminMode_read

    def read_reportTimingBeamState(self):
        # PROTECTED REGION ID(CspMaster.reportTimingBeamState_read) ENABLED START #
        return [tango.DevState.UNKNOWN]
        # PROTECTED REGION END #    //  CspMaster.reportTimingBeamState_read

    def read_reportTimingBeamHealthState(self):
        # PROTECTED REGION ID(CspMaster.reportTimingBeamHealthState_read) ENABLED START #
        return [0]
        # PROTECTED REGION END #    //  CspMaster.reportTimingBeamHealthState_read

    def read_reportTimingBeamAdminMode(self):
        # PROTECTED REGION ID(CspMaster.reportTimingBeamAdminMode_read) ENABLED START #
        return [0]
        # PROTECTED REGION END #    //  CspMaster.reportTimingBeamAdminMode_read

    def read_reportVLBIBeamState(self):
        # PROTECTED REGION ID(CspMaster.reportVLBIBeamState_read) ENABLED START #
        return [tango.DevState.UNKNOWN]
        # PROTECTED REGION END #    //  CspMaster.reportVLBIBeamState_read

    def read_reportVLBIBeamHealthState(self):
        # PROTECTED REGION ID(CspMaster.reportVLBIBeamHealthState_read) ENABLED START #
        return [0]
        # PROTECTED REGION END #    //  CspMaster.reportVLBIBeamHealthState_read

    def read_reportVLBIBeamAdminMode(self):
        # PROTECTED REGION ID(CspMaster.reportVLBIBeamAdminMode_read) ENABLED START #
        return [0]
        # PROTECTED REGION END #    //  CspMaster.reportVLBIBeamAdminMode_read


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
        if self.get_state() == tango.DevState.DISABLE:
            if self._admin_mode.name not in [AdminMode.OFFLINE.name, 
                                          AdminMode.NOTFITTED.name]:
                return False
        return True
        # PROTECTED REGION END #    //  CspMaster.is_On_allowed
    @command(
        dtype_in=('str',), 
        doc_in="If the array length is 0, the command applies to the whole\nCSP Element.\n\
                If the array length is > 1, each array element specifies the FQDN of the\n\
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

    @command(
        dtype_in=('str',), 
        doc_in="If the array length is 0, the command applies to the whole\nCSP Element.\n\
                If the array length is > 1, each array element specifies the FQDN of the\n\
                CSP SubElement to switch OFF.", 
    )
    @DebugIt()
    def Off(self, argin):
        # PROTECTED REGION ID(CspMaster.Off) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CspMaster.Off

    @command(
        dtype_in=('str',), 
        doc_in="If the array length is 0, the command applies to the whole\nCSP Element.\n\
                If the array length is > 1, each array element specifies the FQDN of the\n\
                CSP SubElement to switch OFF.", 
    )
    @DebugIt()
    def Standby(self,argin):
        # PROTECTED REGION ID(CspMaster.Standby) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CspMaster.Standby

    @command(
        dtype_in='DevEnum', 
        doc_in="adminMode", 
    )
    @DebugIt()
    def SetCbfAdminMode(self, argin):
        # PROTECTED REGION ID(CspMaster.SetCbfAdminMode) ENABLED START #
        try:
            cbf_proxy = self._se_proxies[self.CspMidCbf]
            cbf_proxy.adminMode = argin
        except KeyError as key_err:
            err_msg = "No proxy for device" + str(error)
            self.dev_logging(err_msg, int(tango.LogLevel.LOG_ERROR))
        except tango.DevFailed as df: 
            tango.Except.throw_exception("Command failed", str(df.args[0].desc),
                                         "Set cbf admin mode", tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CspMaster.SetCbfAdminMode

    @command(
        dtype_in='DevEnum', 
        doc_in="adminMode", 
    )
    @DebugIt()
    def SetPssAdminMode(self, argin):
        # PROTECTED REGION ID(CspMaster.SetPssAdminMode) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CspMaster.SetPssAdminMode

    @command(
        dtype_in='DevEnum', 
        doc_in="adminMode", 
    )
    @DebugIt()
    def SetPstAdminMode(self, argin):
        # PROTECTED REGION ID(CspMaster.SetPstAdminMode) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CspMaster.SetPstAdminMode

# ----------
# Run server
# ----------

def main(args=None, **kwargs):
    # PROTECTED REGION ID(CspMaster.main) ENABLED START #
    return run((CspMaster,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CspMaster.main

if __name__ == '__main__':
    main()
