#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the csp-lmc-prototype project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the CspMaster."""

# Standard imports
import sys
import os
import time

# Path
file_path = os.path.dirname(os.path.abspath(__file__))
# insert base package directory to import global_enum 
# module in commons folder
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

path = os.path.join(os.path.dirname(__file__), os.pardir)
sys.path.insert(0, os.path.abspath(path))

# Tango imports
import tango
from tango import DevState
#from tango.test_context import DeviceTestContext
import pytest

#Local imports
from CspMaster.CspMaster import CspMaster
#from global_enum import HealthState, AdminMode
from global_enum import AdminMode

# Device test case
@pytest.mark.usefixtures("cbf_master", "csp_master", "cbf_subarray01", "csp_subarray01")

class TestCspMaster(object):

    def test_State(self, csp_master, cbf_master):
        """Test for State after initialization """
        # reinitalize Csp Master and CbfMaster devices
        cbf_master.Init()
        time.sleep(3)
        csp_state = csp_master.state()
        assert csp_state in [DevState.STANDBY, DevState.INIT, DevState.DISABLE]

    def test_adminMode(self, csp_master):
        """ Test the adminMode attribute w/r"""
        csp_master.adminMode = AdminMode.OFFLINE.value
        time.sleep(3)
        assert csp_master.adminMode.value == AdminMode.OFFLINE.value

    def test_cbfAdminMode(self, csp_master):
        """ Test the CBF adminMode attribute w/r"""
        csp_master.cbfAdminMode = AdminMode.ONLINE.value
        time.sleep(3)
        assert csp_master.cbfAdminMode.value == AdminMode.ONLINE.value

    def test_pssAdminMode(self, csp_master):
        """ Test the PSS adminMode attribute w/r"""
        try:
            csp_master.pssAdminMode = AdminMode.ONLINE.value
            assert csp_master.pssAdminMode.value == AdminMode.ONLINE.value
        except tango.DevFailed as df:
            assert "No proxy for device" in df.args[0].desc

    def test_pstAdminMode(self, csp_master):
        """ Test the PST adminMode attribute w/r"""
        try:
            csp_master.pstAdminMode = AdminMode.ONLINE.value
            assert csp_master.pstAdminMode.value == AdminMode.ONLINE.value
        except tango.DevFailed as df:
            assert "No proxy for device" in df.args[0].desc

    def test_subelement_address(self, csp_master):
        """Test for report state of SearchBeam Capabilitities"""
        cbf_addr = csp_master.cbfMasterAddress
        cbf_addr_property = csp_master.get_property("CspMidCbf")["CspMidCbf"][0]
        assert cbf_addr == cbf_addr_property
        pss_addr = csp_master.pssMasterAddress
        pss_addr_property = csp_master.get_property("CspMidPss")["CspMidPss"][0]
        assert pss_addr == pss_addr_property
        pst_addr = csp_master.pstMasterAddress
        pst_addr_property = csp_master.get_property("CspMidPst")["CspMidPst"][0]
        assert pst_addr == pst_addr_property

    def test_properties(self, csp_master):
        capability_list = ['SearchBeam:1500', 'TimingBeam:16', 'VlbiBeam:20','Subarray:16']
        capability_list.sort()
        #Oss: maxCapability returns a tuple
        assert csp_master.maxCapabilities == tuple(capability_list)

    def test_forwarded_attributes(self, csp_master, cbf_master):
        vcc_state = csp_master.reportVCCState
        vcc_state_cbf = cbf_master.reportVCCState
        assert vcc_state == vcc_state_cbf

    def test_search_beams_states_at_init(self, csp_master):
        """ 
        Test for the SearchBeam Capabilities State after initialization
        """
        num_of_search_beam = 0
        max_capabilities = csp_master.maxCapabilities
        for max_capability in max_capabilities: 
            capability_type, max_capability_instances = max_capability.split(":")
            if capability_type == 'SearchBeam':
                num_of_search_beam = int(max_capability_instances)
                break
        search_beam_state = csp_master.reportSearchBeamState 
        assert  num_of_search_beam == len(search_beam_state)
        expected_search_beam = [tango.DevState.UNKNOWN for i in range(num_of_search_beam)]
        assert tuple(expected_search_beam) == search_beam_state

    def test_timing_beams_states_at_init(self, csp_master):
        """ 
        Test for the TimingBeam Capabilities State after initialization
        """
        num_of_beam = 0
        max_capabilities = csp_master.maxCapabilities
        for max_capability in max_capabilities: 
            capability_type, max_capability_instances = max_capability.split(":")
            if capability_type == 'TimingBeam':
                num_of_beam = int(max_capability_instances)
                break
        timing_beam_state = csp_master.reportTimingBeamState 
        assert  num_of_beam == len(timing_beam_state)
        expected_search_beam = [tango.DevState.UNKNOWN for i in range(num_of_beam)]
        assert tuple(expected_search_beam) == timing_beam_state

    def test_vlbi_beams_states_at_init(self, csp_master):
        """ 
        Test for the VlbiBeam Capabilities State after initialization
        """
        num_of_beam = 0
        max_capabilities = csp_master.maxCapabilities
        for max_capability in max_capabilities: 
            capability_type, max_capability_instances = max_capability.split(":")
            if capability_type == 'VlbiBeam':
                num_of_beam = int(max_capability_instances)
                break
        vlbi_beam_state = csp_master.reportVlbiBeamState 
        assert  num_of_beam == len(vlbi_beam_state)
        expected_search_beam = [tango.DevState.UNKNOWN for i in range(num_of_beam)]
        assert tuple(expected_search_beam) == vlbi_beam_state

    def test_receptors_available_ids(self, csp_master):
        list_of_receptors = csp_master.availableReceptorIDs
        assert len(list_of_receptors) > 0 

    def test_available_capabilities(self, csp_master):
        available_cap = csp_master.availableCapabilities
        assert len(available_cap) > 0 

    def test_On_invalid_argument(self, csp_master):
        """Test for the execution of the On command with a wrong input argument"""
        with pytest.raises(tango.DevFailed) as df:
            argin = ["cbf", ]
            csp_master.On(argin)
        assert "No proxy found for device" in str(df.value)

    def test_On_valid_state(self, csp_master, cbf_master):
        """
        Test for execution of On command when the CbfTestMaster is in the right state
        """
        #reinit CSP and CBFTest master devices
        cbf_master.Init()
        time.sleep(2)
        # sleep for a while to wait state transition
        # check CspMaster state
        csp_master.Init()
        assert csp_master.State() == DevState.STANDBY
        # issue the "On" command on CbfMaster device
        argin = ["mid_csp_cbf/sub_elt/master",]
        csp_master.On(argin)
        time.sleep(3)
        assert csp_master.state() == DevState.ON

    def test_On_invalid_state(self, csp_master, cbf_master):
        """
        Test for the execution of the On command when the CbfMaster 
        is in an invalid state
        """
        #reinit CSP and CBF master devices
        cbf_master.Init()
        csp_master.Init()
        # sleep for a while to wait for state transitions
        time.sleep(3)
        assert csp_master.cspCbfState == DevState.STANDBY
        # issue the command to switch off the CbfMaster
        #argin=["",]
        argin = ["mid_csp_cbf/sub_elt/master",]
        csp_master.Off(argin)
        # wait for the state transition from STANDBY to OFF
        time.sleep(3)
        assert csp_master.cspCbfState == DevState.OFF
        # issue the command to switch on the CbfMaster device
        with pytest.raises(tango.DevFailed) as df:
            argin = ["mid_csp_cbf/sub_elt/master", ]
            csp_master.On(argin)
        assert "Command On not allowed" in str(df.value.args[0].desc)

    def test_Standby_invalid_argument(self, csp_master, cbf_master):
        """Test for the execution of the Standby command with a wrong input argument"""
        #reinit CSP and CBF master devices
        cbf_master.Init()
        #csp_master.Init()
        # sleep for a while to wait for state transitions
        time.sleep(3)
        csp_master.On("")
        time.sleep(3)
        with pytest.raises(tango.DevFailed) as df:
            argin = ["cbf", ]
            csp_master.Standby(argin)
        assert "No proxy found for device" in str(df.value)

    def test_Standby_valid_state(self, csp_master, cbf_master):
        """
        Test for execution of On command when the CbfTestMaster is in the right state
        """
        assert csp_master.State() == DevState.ON
        # issue the "Standby" command on CbfMaster device
        argin = ["mid_csp_cbf/sub_elt/master",]
        csp_master.Standby(argin)
        time.sleep(3)
        assert csp_master.state() == DevState.STANDBY

    def test_Off_invalid_argument(self, csp_master):
        """Test for the execution of the Off command with a wrong input argument"""
        csp_state = csp_master.State()
        argin = ["cbf", ]
        csp_master.Off(argin)
        #at present time the code does not raise any exception
        assert csp_state == csp_master.State()

    def test_Off_invalid_state(self, csp_master, cbf_master):
        """
        Test for the execution of the Off command when the CbfMaster 
        is in an invalid state
        """
        cbf_master.Init()
        #csp_master.Init()
        # sleep for a while to wait for state transitions
        time.sleep(3)
        assert csp_master.State() == DevState.STANDBY
        csp_master.On("")
        time.sleep(3)
        assert csp_master.State() == DevState.ON
        # issue the command to switch off the CSP
        with pytest.raises(tango.DevFailed) as df:
            csp_master.Off("")
        assert "Command Off not allowed" in str(df.value.args[0].desc)

    def test_Off_valid_state(self, csp_master, cbf_master):
        """
        Test for execution of On command when the CbfTestMaster is in the right state
        """
        #reinit CSP and CBFTest master devices
        cbf_master.Init()
        #csp_master.Init()
        time.sleep(2)
        assert csp_master.State() == DevState.STANDBY
        # issue the "Off" command on CbfMaster device
        csp_master.Off("")
        time.sleep(3)
        assert csp_master.state() == DevState.OFF
    
    def test_reinit_csp_master(self, csp_master, cbf_master):
        #reinit CSP and CBFTest master devices
        cbf_master.Init()
        #csp_master.Init()
        time.sleep(2)
        assert csp_master.State() == DevState.STANDBY 


