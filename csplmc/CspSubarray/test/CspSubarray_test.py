#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the csp-lmc-prototype project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the CspSubarray."""

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
import pytest

#Local imports
#from CspSubarray.CspSubarray import CspSubarray
from global_enum import ObsState

# Device test case
@pytest.mark.usefixtures("csp_master", "csp_subarray01", "cbf_subarray01")

class TestCspSubarray(object):

    def test_State(self, csp_subarray01, csp_master):
        """
        Test for State after device startup.
        The CspSubarray State at start is OFF.  
        """
        csp_subarray01.Init()
        time.sleep(2)
        state = csp_subarray01.state()
        assert state in [DevState.DISABLE]
        #switch-on the CspMaster 
        csp_master_state = csp_master.state()
        assert csp_master_state == DevState.STANDBY
        csp_master.On("")
        time.sleep(2)
        state = csp_subarray01.state()
        assert state in [DevState.OFF]
        

    def test_add_invalid_receptor_ids(self, csp_subarray01, csp_master):
        """
        Test the assignment of a number of invalid  receptor IDs to 
        a CspSubarray.
        The AddReceptors method fails raising a tango.DevFailed exception.
        """
        receptors_list = csp_master.availableReceptorIDs
        assert receptors_list
        invalid_receptor_to_assign = []
        # try to add 3 invalid receptors
        for id_num in range(1,198):
            if id_num not in receptors_list:
                invalid_receptor_to_assign.append(id_num)
            if len(invalid_receptor_to_assign) > 3:
                break
        csp_subarray01.AddReceptors(invalid_receptor_to_assign)
        time.sleep(2)
        receptors = csp_subarray01.receptors     
        assert not receptors
             
    def test_add_valid_receptor_ids(self, csp_subarray01, csp_master):
        """
        Test the assignment of valid receptors to a CspSubarray
        """
        # get the list of available receptorIDs (the read operation
        # returns a tuple!)
        receptor_list = csp_master.availableReceptorIDs
        # assert the tuple is not empty
        assert receptor_list
        csp_subarray01.AddReceptors(receptor_list)
        # sleep a while to wait for attribute updated
        time.sleep(2)
        # read the list of assigned receptors
        receptors = csp_subarray01.receptors     
        assert set(receptor_list) == set(receptors)

    def test_add_already_assigned_receptor_ids(self, csp_subarray01, csp_master):
        """
        Test the assignment of already assigned receptors to a CspSubarray
        """
        # read the list of receptors allocated tothe subarray
        assigned_receptors = csp_subarray01.receptors     
        assert assigned_receptors
        receptors_to_add = [assigned_receptors[0]]
        csp_subarray01.AddReceptors(receptors_to_add)
        time.sleep(2)
        receptors = csp_subarray01.receptors
        assert receptors == assigned_receptors

    def test_State_after_receptors_assignment(self, csp_subarray01):
        """
        Test the CspSubarray State after receptors assignment.
        After assignment State is ON
        """
        # read the list of assigned receptors and check it's not
        # empty
        assigned_receptors = csp_subarray01.receptors     
        assert assigned_receptors
        # read the CspSubarray State
        state = csp_subarray01.state()
        assert state == DevState.ON

    def test_remove_receptors(self, csp_subarray01, csp_master):
        """
        Test the partial deallocation of receptors from a
        CspSubarray.
        """
        # read the list of assigned receptors and check it's not
        # empty
        assigned_receptors = csp_subarray01.receptors     
        assert assigned_receptors 
        init_number_of_receptors = len(assigned_receptors)
        assert init_number_of_receptors > 1
        receptor_to_remove = []
        receptor_to_remove.append(assigned_receptors[0])
        csp_subarray01.RemoveReceptors(receptor_to_remove)
        time.sleep(5)
        assigned_receptors = csp_subarray01.receptors     
        final_number_of_receptors = len(assigned_receptors)
        assert (init_number_of_receptors - final_number_of_receptors) == 1

    def test_assign_valid_and_invalid_receptors(self, csp_subarray01, csp_master):
        """
        Test the partial deallocation of receptors from a
        CspSubarray.
        """
        # read the list of assigned receptors and check it's not
        # empty
        receptors_to_add = []
        assigned_receptors = csp_subarray01.receptors 
        num_of_initial_receptors = len(assigned_receptors)
        assert assigned_receptors 
        # add valid receptors to the list of resources to assign
        available_receptors = csp_master.availableReceptorIDs
        for id_num in available_receptors:
            receptors_to_add.append(id_num)
        num_of_valid_receptors = len(receptors_to_add)
        # add 3 invalid receptor
        iteration = 0
        for id_num in range(1, 198):
            #skip the assigned receptors
            if id_num in assigned_receptors:
                continue
            else:
                receptors_to_add.append(id_num)
                iteration += 1
                if iteration == 3: 
                    break
        assert receptors_to_add
        csp_subarray01.AddReceptors(receptors_to_add)
        time.sleep(2)
        assigned_receptors = csp_subarray01.receptors
        final_number_of_receptors = len(assigned_receptors)
        assert final_number_of_receptors == (num_of_initial_receptors + num_of_valid_receptors)

    def test_remove_all_receptors(self, csp_subarray01):
        """
        Test the complete deallocation of receptors from a
        CspSubarray.
        Final CspSubarray state is OFF
        """
        # read the list of assigned receptors and check it's not
        # empty
        assigned_receptors = csp_subarray01.receptors     
        assert assigned_receptors
        csp_subarray01.RemoveAllReceptors()
        time.sleep(2)
        assigned_receptors = csp_subarray01.receptors
        assert not assigned_receptors
        time.sleep(2)
        assert csp_subarray01.state() == DevState.OFF

    def test_configureScan_invalid_state(self, csp_subarray01, csp_master):
        subarray_state = csp_subarray01.State()
        assert subarray_state == tango.DevState.OFF
        filename = os.path.join(commons_pkg_path, "test_ConfigureScan_basic.json")
        f = open(filename)
        with pytest.raises(tango.DevFailed) as df:
            csp_subarray01.ConfigureScan(f.read().replace("\n", ""))
        if df:
            err_msg = str(df.value.args[0].desc)
            assert "Command ConfigureScan not allowed" in err_msg


    def test_configureScan(self, csp_subarray01, csp_master):
        obs_state = csp_subarray01.obsState
        assert obs_state in [ObsState.IDLE.value, ObsState.READY.value]
        receptor_list = csp_master.availableReceptorIDs
        time.sleep(2)
        # assert the tuple is not empty
        assert receptor_list
        # assign only receptors [1,4] for which the configuration addresses are provided in
        # the configuration JSON file
        receptors_to_assign = [1,4]
        csp_subarray01.AddReceptors(receptors_to_assign)
        time.sleep(2)
        subarray_state = csp_subarray01.State()
        assert subarray_state == tango.DevState.ON
        filename = os.path.join(commons_pkg_path, "test_ConfigureScan_basic.json")
        f = open(filename)
        csp_subarray01.ConfigureScan(f.read().replace("\n", ""))
        f.close()
        time.sleep(5)
        obs_state = csp_subarray01.obsState
        assert obs_state == ObsState.READY.value

    def test_start_scan(self, csp_subarray01):
        obs_state = csp_subarray01.obsState
        assert obs_state == ObsState.READY.value
        csp_subarray01.Scan(" ")
        time.sleep(2)
        obs_state = csp_subarray01.obsState
        assert obs_state == ObsState.SCANNING.value

    def test_end_scan(self, csp_subarray01):
        obs_state = csp_subarray01.obsState
        assert obs_state == ObsState.SCANNING.value
        csp_subarray01.EndScan()
        time.sleep(2)
        obs_state = csp_subarray01.obsState
        assert obs_state == ObsState.READY

    def test_remove_receptors_when_ready(self, csp_subarray01):
        """
        Test the complete deallocation of receptors from a
        CspSubarray when the subarray ObsMode is READY.
        """
        obs_state = csp_subarray01.obsState
        assert obs_state == ObsState.READY
        with pytest.raises(tango.DevFailed) as df:
            csp_subarray01.RemoveAllReceptors()
        if df:
            err_msg = str(df.value.args[0].desc)
            assert "Command RemoveAllReceptors not allowed" in err_msg
        
    def test_remove_receptors_when_idle(self, csp_subarray01):
        """
        Test the complete deallocation of receptors from a
        CspSubarray when the subarray from ObsMode READY transits to
        IDLE.
        """
        obs_state = csp_subarray01.obsState
        assert obs_state == ObsState.READY
        # command transition to IDLE
        csp_subarray01.EndSB()
        time.sleep(3)
        obs_state = csp_subarray01.obsState
        assert obs_state == ObsState.IDLE
        csp_subarray01.RemoveAllReceptors()
        time.sleep(3)
        subarray_state = csp_subarray01.state()
        assert subarray_state == tango.DevState.OFF
        assert obs_state == ObsState.IDLE


