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
from tango.test_context import DeviceTestContext
import pytest

#Local imports
from CspSubarray import CspSubarray
from global_enum import HealthState, AdminMode

# Device test case
@pytest.mark.usefixtures("csp_master", "csp_subarray01", "cbf_subarray01")

class TestCspSubarray(object):
    @classmethod

    def test_State(self, csp_subarray01):
        """
        Test for State after device startup.
        The CspSubarray State at start is OFF.  
        """
        csp_subarray01.Init()
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
        print(receptors_list)
        assert receptors_list
        random_list = []
        receptor_to_assign = []
        number_of_receptors = len(receptors_list)
        for i in range(1,198):
            if i not in receptors_list:
                random_list.append(i)
            if len(random_list) > 3:
                break
        print(random_list)
        for receptor_id in random_list:
            if receptor_id not in receptors_list:
                receptor_to_assign.append(receptor_id)
        print(receptor_to_assign)
        with pytest.raises(tango.DevFailed) as df:
            csp_subarray01.AddReceptors(receptor_to_assign)
        if df:
            err_msg = str(df.value.args[0].desc)
            #assert "AttributeError: subarrayMembership" in str(df.value.args[0].desc)
            #assert str(df.value.args[0].desc) in ["AttributeError: subarrayMembership", "IndexError: list index out of range"]
            assert err_msg.rstrip() in ["AttributeError: subarrayMembership", "IndexError: list index out of range"]
            #assert "AttributeError: subarrayMembership" in str(df.value.args[0].desc) or  assert "IndexError: list index out of range" in str(df.value.args[0].desc)
        else:    
            receptors = csp_subarray01.receptors     
            assert random_list == list(receptors)
             
    def test_add_valid_receptor_ids(self, csp_subarray01, csp_master):
        """
        Test the assignment of valid receptors to a CspSubarray
        """
        # read the list of available receptorIDs (the read operation
        # returns a tuple!)
        receptor_list = csp_master.availableReceptorIDs
        # assert the tuple is not empty
        assert receptor_list
        csp_subarray01.AddReceptors(receptor_list)
        # sleep a while to wait for attribute updated
        time.sleep(2)
        # read the list of assigned receptors
        receptors = csp_subarray01.receptors     
        assert receptor_list == receptors

    def test_add_already_assigned_receptor_ids(self, csp_subarray01, csp_master):
        """
        Test the assignment of already assigned receptors to a CspSubarray
        """
        # read the list of receptors allocated tothe subarray
        assigned_receptors = csp_subarray01.receptors     
        assert assigned_receptors
        receptors_to_add = [assigned_receptors[0], assigned_receptors[1]]
        csp_subarray01.AddReceptors(receptors_to_add)
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

    def test_remove_receptors(self, csp_subarray01):
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
        time.sleep(2)
        assigned_receptors = csp_subarray01.receptors
        final_number_of_receptors = len(assigned_receptors)
        assert (init_number_of_receptors - final_number_of_receptors) == 1

    def test_remove_all_receptors(self, csp_subarray01):
        """
        Test the complete deallocation of receptors from a
        CspSubarray.
        Final CspSubarray state is OFF
        """
        # read the list of assigned receptors and check it's not
        # empty
        assigned_receptors = csp_subarray01.receptors     
        print(assigned_receptors)
        assert assigned_receptors
        csp_subarray01.RemoveAllReceptors()
        time.sleep(2)
        assigned_receptors = csp_subarray01.receptors
        assert not assigned_receptors
        time.sleep(2)
        assert csp_subarray01.state() == DevState.OFF

