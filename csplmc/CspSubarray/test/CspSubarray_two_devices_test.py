#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the csp-lmc-prototype project
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the CspSubarray."""

# Standard imports
import sys
import os
import time

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
@pytest.mark.usefixtures("csp_master", "csp_subarray01", "cbf_subarray01",
                         "csp_subarray02", "tm_leafnode1")

class TestCspSubarray_two_devices(object):

    def test_add_receptors_to_sub1_and_sub2(self, csp_subarray01, csp_subarray02,
                                            csp_master, tm_leafnode1):
        """
        Test allocation of receptors with two subarrays.
        Both subarrays move to State ON after assignment.
        """
        csp_subarray01.Init()
        time.sleep(2)
        tm_leafnode1.Init()
        if csp_master.state() == DevState.STANDBY:
            csp_master.On("")
            time.sleep(2)
        assert (csp_subarray01.state() == DevState.OFF and
                csp_subarray02.state() == DevState.OFF and
                csp_subarray01.obsState == ObsState.IDLE and
                csp_subarray02.obsState == ObsState.IDLE)
        # add receptors 1,4 to subarray 01
        receptor_to_assign = [1, 4]
        csp_subarray01.AddReceptors(receptor_to_assign)
        time.sleep(2)
        # add receptors 2,3 to subarray 02
        receptor_to_assign = [2, 3]
        csp_subarray02.AddReceptors(receptor_to_assign)
        time.sleep(2)
        assert (csp_subarray01.obsState == ObsState.IDLE and
                csp_subarray02.obsState == ObsState.IDLE and
                csp_subarray01.state() == tango.DevState.ON and
                csp_subarray02.state() == tango.DevState.ON)

    def test_configureScan_sub1_and_sub2(self, csp_subarray01, csp_subarray02):
        """
        Test scan configuration with two subarrays.
        """
        assert (csp_subarray01.state() == tango.DevState.ON and
                csp_subarray02.state() == tango.DevState.ON)
        filename1 = os.path.join(commons_pkg_path, "test_ConfigureScan_basic.json")
        filename2 = os.path.join(commons_pkg_path, "test_ConfigureScan_band1_sub2.json")
        config_file1 = open(filename1)
        config_file2 = open(filename2)
        csp_subarray01.ConfigureScan(config_file1.read().replace("\n", ""))
        csp_subarray02.ConfigureScan(config_file2.read().replace("\n", ""))
        time.sleep(4)
        assert (csp_subarray01.obsState == ObsState.READY and
                csp_subarray02.obsState == ObsState.READY)
        config_file1.close()
        config_file2.close()

    def test_start_scan_sub1_and_sub2(self, csp_subarray01, csp_subarray02):
        """
        Test Scan method with two subarrays.
        """
        assert (csp_subarray01.obsState == ObsState.READY and
                csp_subarray02.obsState == ObsState.READY)
        csp_subarray01.Scan(" ")
        csp_subarray02.Scan(" ")
        time.sleep(2)
        assert (csp_subarray01.obsState == ObsState.SCANNING and
                csp_subarray02.obsState == ObsState.SCANNING)

    def test_end_scan(self, csp_subarray01, csp_subarray02):
        """
        Test EndScan method with two subarrays.
        """
        assert (csp_subarray01.obsState == ObsState.SCANNING and
                csp_subarray02.obsState == ObsState.SCANNING)
        csp_subarray01.EndScan()
        csp_subarray02.EndScan()
        time.sleep(2)
        assert (csp_subarray01.obsState == ObsState.READY and
                csp_subarray02.obsState == ObsState.READY)
