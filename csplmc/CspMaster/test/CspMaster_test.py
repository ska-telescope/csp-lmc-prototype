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
from tango.test_context import DeviceTestContext
import pytest

#Local imports
from CspMaster.CspMaster import CspMaster
from global_enum import HealthState, AdminMode

# Device test case
@pytest.mark.usefixtures("tango_context", "initialize_device", "cbfmaster_proxy", "csp_master")

class TestCspMaster(object):
    @classmethod
    def mocking(cls):
        """Mock external libraries."""
        # Example : Mock numpy
        # cls.numpy = CspMaster.numpy = MagicMock()


    def test_State(self, csp_master, cbfmaster_proxy):
        """Test for State after initialization """
        # reinitalize Csp Master and CbfMaster devices
        csp_master.Init()
        cbfmaster_proxy.Init()
        # seleep for a while to wait for state transition
        time.sleep(2)
        csp_state = csp_master.state()
        assert csp_state in [DevState.STANDBY, DevState.INIT]

    def test_adminMode(self, tango_context):
        """ Test the adminMode attribute w/r"""
        tango_context.device.adminMode = AdminMode.OFFLINE.value
        assert tango_context.device.adminMode.value == AdminMode.OFFLINE.value

    def test_cbfAdminMode(selfs,tango_context):
        """ Test the CBF adminMode attribute w/r"""
        tango_context.device.cbfAdminMode = AdminMode.ONLINE.value
        assert tango_context.device.cbfAdminMode.value == AdminMode.ONLINE.value

    def test_pssAdminMode(self, tango_context):
        """ Test the PSS adminMode attribute w/r"""
        try:
            tango_context.device.pssAdminMode = AdminMode.ONLINE.value
            assert tango_context.device.pssAdminMode.value == AdminMode.ONLINE.value
        except tango.DevFailed as df:
            assert "No proxy for device" in df.args[0].desc

    def test_pstAdminMode(self,tango_context):
        """ Test the PST adminMode attribute w/r"""
        try:
            tango_context.device.pstAdminMode = AdminMode.ONLINE.value
            assert tango_context.device.pstAdminMode.value == AdminMode.ONLINE.value
        except tango.DevFailed as df:
            assert "No proxy for device" in df.args[0].desc

    def test_subelement_address(self, tango_context):
        """Test for report state of SearchBeam Capabilitities"""
        cbf_addr = tango_context.device.cbfMasterAddress
        assert cbf_addr == "mid_csp_cbf/sub_elt/master"
        pss_addr = tango_context.device.pssMasterAddress
        assert pss_addr == "mid_csp_pss/sub_elt/master"
        pst_addr = tango_context.device.pstMasterAddress
        assert pst_addr == "mid_csp_pst/sub_elt/master"

    def test_On_invalid_argument(self, csp_master):
        """Test for the execution of the On command with a wrong input argument"""
        with pytest.raises(tango.DevFailed) as df:
            argin = ["cbf", ]
            csp_master.On(argin)
        assert "No proxy found for device" in str(df.value)

    def test_On_valid_state(self, csp_master, cbfmaster_proxy):
        """
        Test for execution of On command when the CbfTestMaster is in the right state
        """
        #reinit CSP and CBFTest master devices
        cbfmaster_proxy.Init()
        time.sleep(2)
        # sleep for a while to wait state transition
        # check CspMaster state
        csp_master.Init()
        assert csp_master.State() == DevState.STANDBY
        # issue the "On" command on CbfTestMaster device
        argin = ["mid_csp_cbf/sub_elt/master",]
        csp_master.On(argin)
        time.sleep(3)
        assert csp_master.state() == DevState.ON

    def test_On_invalid_state(self, csp_master, cbfmaster_proxy):
        """
        Test for the execution of the On command when the CbfMaster 
        is in an invalid state
        """
        #reinit CSP and CBF master devices
        cbfmaster_proxy.Init()
        csp_master.Init()
        # sleep for a while to wait for state transitions
        time.sleep(3)
        assert csp_master.cspCbfState == DevState.STANDBY
        # issue the command to switch off the CbfMaster
        argin=["",]
        cbfmaster_proxy.Off(argin)
        # wait for the state transition from STANDBY to OFF
        time.sleep(3)
        assert csp_master.cspCbfState == DevState.OFF
        # issue the command to switch on the CbfMaster device
        with pytest.raises(tango.DevFailed) as df:
            argin = ["mid_csp_cbf/sub_elt/master", ]
            csp_master.On(argin)
        assert "Command On not allowed" in str(df.value.args[0].desc)

    def test_properties(self, csp_master):
        capability_list = ['SearchBeam:1500', 'TimingBeam:16', 'VlbiBeam:20','Subarray:16']
        capability_list.sort()
        #Oss: maxCapability returns a tuple
        assert csp_master.maxCapabilities == tuple(capability_list)

    def test_forwarded_attributes(self, csp_master, cbfmaster_proxy):
        vcc_state = csp_master.reportVCCState
        vcc_state_cbf = cbfmaster_proxy.reportVCCState
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
