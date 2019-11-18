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
import random
import numpy as np

# Tango imports
import tango
from tango import DevState
import pytest

# Path
file_path = os.path.dirname(os.path.abspath(__file__))
# insert base package directory to import global_enum
# module in commons folder
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

path = os.path.join(os.path.dirname(__file__), os.pardir)
sys.path.insert(0, os.path.abspath(path))

#Local imports
from CspSubarray import CspSubarray
from global_enum import ObsState

# Device test case
@pytest.mark.usefixtures("csp_master", "csp_subarray01", "cbf_subarray01", "csp_subarray02")

class TestCspSubarray(object):

    def test_State(self, csp_subarray01, csp_master):
        """
        Test for State after CSP startup.
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
        Test the assignment of a number of invalid receptor IDs to
        a CspSubarray.
        The AddReceptors method fails raising a tango.DevFailed exception.
        """
        receptors_list = csp_master.availableReceptorIDs
        # receptor_list is a numpy array
        # all(): test whether all array elements evaluate to True.
        assert receptors_list.all()
        invalid_receptor_to_assign = []
        # try to add 3 invalid receptors
        for id_num in range(1, 198):
            if id_num not in receptors_list:
                invalid_receptor_to_assign.append(id_num)
            if len(invalid_receptor_to_assign) > 3:
                break
        csp_subarray01.AddReceptors(invalid_receptor_to_assign)
        time.sleep(2)
        receptors = csp_subarray01.receptors
        # receptors is a numpy array. In this test the returned array has to be
        # empty (no receptor assigned)
        #
        # Note:
        # any returns True if any value is True. Otherwise False
        # all returns True if no value is False. Otherwise True
        # In the case of np.array([]).any() or any([]), there are no True values, because you have
        # a 0-dimensional array or a 0-length list. Therefore, the result is False.
        # In the case of np.array([]).all() or all([]), there are no False values, because you have
        # a 0-dimensional array or a 0-length list. Therefore, the result is True.
        assert not receptors.any()

    def test_add_valid_receptor_ids(self, csp_subarray01, csp_master):
        """
        Test the assignment of valid receptors to a CspSubarray
        """
        # get the list of available receptorIDs (the read operation
        # returns a numpy array)
        receptor_list = csp_master.availableReceptorIDs
        # assert the array is not empty
        assert receptor_list.any()
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
        # read the list of receptors allocated to the subarray
        assigned_receptors = csp_subarray01.receptors
        # assert the list of receptor is not empty
        assert assigned_receptors.any()
        # add to the subarray an already assigned receptor
        receptors_to_add = [assigned_receptors[0]]
        csp_subarray01.AddReceptors(receptors_to_add)
        time.sleep(2)
        receptors = csp_subarray01.receptors
        # check the array read first and the array read last are equal
        assert np.array_equal(receptors, assigned_receptors)

    def test_State_after_receptors_assignment(self, csp_subarray01):
        """
        Test the CspSubarray State after receptors assignment.
        After assignment State is ON
        """
        # read the list of assigned receptors and check it's not
        # empty
        assigned_receptors = csp_subarray01.receptors
        assert assigned_receptors.any()
        # read the CspSubarray State
        state = csp_subarray01.state()
        assert state == DevState.ON

    def test_remove_receptors(self, csp_subarray01):
        """
        Test the partial deallocation of receptors from a
        CspSubarray.
        """
        # read the list of assigned receptors and check it's not
        # empty
        assigned_receptors = csp_subarray01.receptors
        assert assigned_receptors.any()
        init_number_of_receptors = len(assigned_receptors)
        # check there is more than one receptor assigned to
        # the subarray
        assert init_number_of_receptors > 1
        i = random.randrange(1, 4, 1)
        receptor_to_remove = []
        receptor_to_remove.append(i)
        # remove only one receptor (with a random ID)
        csp_subarray01.RemoveReceptors(receptor_to_remove)
        time.sleep(4)
        assigned_receptors = csp_subarray01.receptors
        final_number_of_receptors = len(assigned_receptors)
        assert (init_number_of_receptors - final_number_of_receptors) == 1

    def test_assign_valid_and_invalid_receptors(self, csp_subarray01, csp_master):
        """
        Test the allocation of receptors when some receptor IDs are not
        valid.
        """
        # read the list of assigned receptors and check it's not
        # empty
        receptors_to_add = []
        assigned_receptors = csp_subarray01.receptors
        num_of_initial_receptors = len(assigned_receptors)
        assert assigned_receptors.any()
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
        assert assigned_receptors.any()
        csp_subarray01.RemoveAllReceptors()
        time.sleep(2)
        assigned_receptors = csp_subarray01.receptors
        # check the array is empty (any() in this case returns False)
        assert not assigned_receptors.any()
        time.sleep(2)
        assert csp_subarray01.state() == DevState.OFF

    def test_configureScan_invalid_state(self, csp_subarray01):
        """
        Test that the ConfigureScan() command fails if the Subarray
        state is  not ON
        """
        # check the subarray state is Off (the previous test has removed
        # all the receptors from the subarray, so its state should be OFF
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
        """
        Test that the ConfigureScan() command is issued when the Subarray
        state is ON and ObsState is IDLE or READY
        """
        obs_state = csp_subarray01.obsState
        assert obs_state in [ObsState.IDLE, ObsState.READY]
        receptor_list = csp_master.availableReceptorIDs
        time.sleep(2)
        # receptor_list is a numpy array. If there is no available receptor to assign,
        # receptor_list is a numpy array with only one element whose value is 0, that is:
        # receptor_list = [0] -> means no available receptor
        # To assert the list of receptor is not empty use the numpy any()
        # method
        # assert (receptor_list.size and (receptor_list[0] != 0))
        assert receptor_list.any()
        # assign only receptors [1,4] for which the configuration addresses are provided in
        # the configuration JSON file
        receptors_to_assign = [1, 4]
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
        assert obs_state == ObsState.READY

    def test_start_scan(self, csp_subarray01):
        """
        Test that a subarray is able to process the
        Scan command when its ObsState is READY
        """
        obs_state = csp_subarray01.obsState
        assert obs_state == ObsState.READY
        csp_subarray01.Scan(" ")
        time.sleep(2)
        obs_state = csp_subarray01.obsState
        assert obs_state == ObsState.SCANNING

    def test_end_scan(self, csp_subarray01):
        """
        Test that a subarray is able to process the
        EndScan command when its ObsState is SCANNING.
        """
        obs_state = csp_subarray01.obsState
        assert obs_state == ObsState.SCANNING
        csp_subarray01.EndScan()
        time.sleep(3)
        obs_state = csp_subarray01.obsState
        assert obs_state == ObsState.READY

    def test_remove_receptors_when_ready(self, csp_subarray01):
        """
        Test that the complete deallocation of receptors fails
        when the CspSubarray ObsMode is READY.
        Receptors can be removed only when the subarray
        ObsState is IDLE!
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
        CspSubarray when the subarray is IDLE.
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
