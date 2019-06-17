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
                #ev_id = device_proxy.subscribe_event("State", EventType.CHANGE_EVENT,
                #        self.seSCMCallback, stateless=True)
                #self._se_subarray_event_id[fqdn].append(ev_id)

                #ev_id = device_proxy.subscribe_event("healthState", EventType.CHANGE_EVENT,
                #        self.seSCMCallback, stateless=True)
                #self._se_subarray_event_id[fqdn].append(ev_id)

                #ev_id = device_proxy.subscribe_event("adminMode", EventType.CHANGE_EVENT,
                #        self.seSCMCallback, stateless=True)
                #self._se_subarray_event_id[fqdn].append(ev_id)
            except tango.DevFailed as df:
                for item in df.args:
                    log_msg = "Failure in connection to " + str(fqdn) + \
                            " device: " + str(item.reason)
                    self.dev_logging(log_msg, int(tango.LogLevel.LOG_ERROR))

    def __is_subarray_available(self, subarray_name):
            try:
                print(subarray_name)
                proxy = self._se_subarrays_proxies[subarray_name]
                print(proxy.State())
            except KeyErr as key_err: 
                # no proxy registered for the subarray device
                proxy = tango.DeviceProxy(subarray_name)
                proxy.ping()
                self._se_subarrays_proxies[subarray_name] = proxy
            except tangoDevFailed as df:
                return False
            return True
    # PROTECTED REGION END #    //  CspSubarray.class_variable

    # -----------------
    # Device Properties
    # -----------------

    CbfSubarray = device_property(
        dtype='str', default_value="mid_csp_cbf/sub_elt/subarray_01"
    )

    PssSubarray = device_property(
        dtype='str', default_value="mid_csp_pss/sub_elt/subarray_01"
    )

    PstSubarray = device_property(
        dtype='str', default_value="mid_csp_pst/sub_elt/subarray_01"
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
    fspState = attribute(name="fspState", label="fspState",
        forwarded=True
    )
    fspHealthState = attribute(name="fspHealthState",label="fspHealthState",
        forwarded=True
    )
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
        self._cbf_subarray_obsState     = ObsState.IDLE.value   
        self._pss_subarray_state        = tango.DevState.UNKNOWN
        self._pss_subarray_health_state = HealthState.UNKNOWN.value
        self._pss_subarray_obsState     = ObsState.IDLE.value   
        self._pst_subarray_state        = tango.DevState.UNKNOWN
        self._pst_subarray_health_state = HealthState.UNKNOWN.value
        self._pst_subarray_obsState     = ObsState.IDLE.value   

        # initialize the list with the capabilities belonging to the sub-array
        # Do we need to know the max number of capabilities for each type?
        self._search_beams = []
        self._timing_beams = []
        self._vlbi_beams = []
        self._vcc = []
        self._receptors = []
        self._fsp = []

        self.set_state(tango.DevState.OFF)
        #initialize the list with sub-element sub-arrays addresses
        self._se_subarrays_fqdn = []
        self._se_subarrays_fqdn.append(self.CbfSubarray)
        self._se_subarrays_fqdn.append(self.PssSubarray)
        self._se_subarrays_fqdn.append(self.PstSubarray)
        self._se_subarrays_proxies = {}
        self._se_subarray_event_id = {}
        # try connection to sub-element sub-arrays
        self.__connect_to_subarrays()

        # initialize proxy to CBFMaster device
        self._cbfMasterProxy = 0
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
        return tango.DevState.UNKNOWN
        # PROTECTED REGION END #    //  CspSubarray.cbfSubarrayState_read

    def read_pssSubarrayState(self):
        # PROTECTED REGION ID(CspSubarray.pssSubarrayState_read) ENABLED START #
        return tango.DevState.UNKNOWN
        # PROTECTED REGION END #    //  CspSubarray.pssSubarrayState_read

    def read_pstSubarrayState(self):
        # PROTECTED REGION ID(CspSubarray.pstSubarrayState_read) ENABLED START #
        return tango.DevState.UNKNOWN
        # PROTECTED REGION END #    //  CspSubarray.pstSubarrayState_read

    def read_cbfSubarrayHealthState(self):
        # PROTECTED REGION ID(CspSubarray.cbfSubarrayHealthState_read) ENABLED START #
        return 0
        # PROTECTED REGION END #    //  CspSubarray.cbfSubarrayHealthState_read

    def read_pssSubarrayHealthState(self):
        # PROTECTED REGION ID(CspSubarray.pssSubarrayHealthState_read) ENABLED START #
        return 0
        # PROTECTED REGION END #    //  CspSubarray.pssSubarrayHealthState_read

    def read_pstSubarrayHealthState(self):
        # PROTECTED REGION ID(CspSubarray.pstSubarrayHealthState_read) ENABLED START #
        return 0
        # PROTECTED REGION END #    //  CspSubarray.pstSubarrayHealthState_read

    def read_cbfSubarrayObsState(self):
        # PROTECTED REGION ID(CspSubarray.cbfSubarrayObsState_read) ENABLED START #
        return 0
        # PROTECTED REGION END #    //  CspSubarray.cbfSubarrayObsState_read

    def read_pssSubarrayObsState(self):
        # PROTECTED REGION ID(CspSubarray.pssSubarrayObsState_read) ENABLED START #
        return 0
        # PROTECTED REGION END #    //  CspSubarray.pssSubarrayObsState_read

    def read_pstSubarrayObsState(self):
        # PROTECTED REGION ID(CspSubarray.pstSubarrayObsState_read) ENABLED START #
        return 0
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
        print("read_receptors: ", self._receptors)
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
        receptor_membership = []
        # the list of receptor to assign to the subarray
        receptor_to_assign = []
        # get the list of all receptor affilitiation
        try:
            if not self._cbfMasterProxy:
                self._cbfMasterProxy = tango.DeviceProxy("mid_csp_cbf/master/main")
                # check if device is available    
            self._cbfMasterProxy.ping()
            vcc_membership = self._cbfMasterProxy.reportVCCSubarrayMembership
            num_of_vcc = len(vcc_membership)
            num_of_vcc = 3
            receptor_membership = [0]*num_of_vcc
            vcc_to_receptor = self._cbfMasterProxy.vccToReceptor
            vcc_to_receptor_map = dict([int(ID) for ID in pair.split(":")] for pair in vcc_to_receptor)
            #print("vcc_to_receptor_map:", vcc_to_receptor_map)
            for vcc_id in range(num_of_vcc):
                receptorID = vcc_to_receptor_map[vcc_id + 1]
                #print("receptorID:", receptorID)
                receptor_membership[receptorID - 1] = vcc_membership[vcc_id]
            print("receptor_membership:", receptor_membership)
        except tango.DevFailed as df:
            for item in df.args:
                if "Failed to connect to device" in item.desc:
                    self._cbfMasterProxy = 0
            tango.Except.throw_exception("Command failed", df.args[0].desc,
                                         "AddReceptors", tango.ErrSeverity.ERR)
        # check if the required receptor is already assigned
        for receptorId in argin:
            if receptor_membership[receptorId] in range(1,16):
                print("Receptor already assigned to subarray..")
            else :
                receptor_to_assign.append(receptorId)
            # check if the list of receptors to assign is empy
            if not receptor_to_assign:
                log_msg = "The required receptors are already assigned to the subarray"
                self.dev_logging(log_msg, tango.LogLevel.LOG_INFO)
                return  
        #check if the device is already connected to the CbfSubarray
        proxy = 0
        if self.__is_subarray_available(self.CbfSubarray):
            try:     
                print("Sono qui")
                proxy = self._se_subarrays_proxies[self.CbfSubarray]
                proxy.command_inout("AddReceptors", receptor_to_assign)
                print("ok")
                # read the updated list of the assigned receptors
                self._receptors = proxy.receptors
                # build the list with the VCCs assigned to the sub-array
                receptor_to_vcc_dict = self._cbfMasterProxy.receptorToVcc
                receptor_to_vccId = ([int(ID) for ID in pair.split(":")] for pair in receptor_to_vcc_dict)
                print("receptors:" , self._receptors)
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
            self._receptors = self.cbfSubarrayProxy.receptors
            # build the list with the VCCs assigned to the sub-array
            for receptor_id in self._receptors:
                vcc_id = receptor_to_vccId[receptor_id]
                self._vcc.append(vcc_id) 
        except KeyErr as key_err: 
            proxy = tango.DeviceProxy(self.CbfSubarray)
            self._se_subarrays_proxies[self.CbfSubarray] = proxy
        except tangoDevFailed as df:
            print(df.args[0].desc)
        # PROTECTED REGION END #    //  CspSubarray.RemoveReceptors

    @command(
    )
    @DebugIt()
    def RemoveAllReceptors(self):
        # PROTECTED REGION ID(CspSubarray.RemoveAllReceptors) ENABLED START #
        try:
            print("x1\n");
            proxy = self._se_subarrays_proxies[self.CbfSubarray]
            print("x2\n");
            proxy.command_inout("RemoveAllReceptors")
            print("x3\n");
            # re-read the list of assigned receptors
            self._receptors = proxy.receptors
            if not self._receptors:
                print("x4\n")
                self._vcc = []
        except KeyError as key_err: 
            proxy = tango.DeviceProxy(self.CbfSubarray)
            self._se_subarrays_proxies[self.CbfSubarray] = proxy
        except tango.DevFailed as df:
            print(df.args[0].desc)
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
