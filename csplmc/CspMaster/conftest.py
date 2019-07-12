"""
A module defining a list of fixture functions that are shared across all the skabase
tests.
"""
#from __future__ import absolute_import
import mock
import pytest
import importlib
import sys
#sys.path.insert(0, "../commons")

import tango
from tango import DeviceProxy
from tango.test_context import DeviceTestContext

#import global_enum 

@pytest.fixture(scope="class")
def csp_master():
    """Create DeviceProxy for the CspMaster device
       to test the device with the TANGO DB
    """
    database = tango.Database()
    instance_list = database.get_device_exported_for_class('CspMaster')
    for instance in instance_list.value_string:
        try:
            return tango.DeviceProxy(instance)
        except tango.DevFailed:
            continue

@pytest.fixture(scope="class")
def csp_subarray01():
    """Create DeviceProxy for the CspMaster device
       to test the device with the TANGO DB
    """
    database = tango.Database()
    instance_list = database.get_device_exported_for_class('CspSubarray')
    for instance in instance_list.value_string:
        try:
            if "subarray_01" in instance:
                return tango.DeviceProxy(instance)
        except tango.DevFailed:
            continue

@pytest.fixture(scope="class")
def cbf_subarray01():
    """Create DeviceProxy for the CspMaster device
       to test the device with the TANGO DB
    """
    database = tango.Database()
    instance_list = database.get_device_exported_for_class('CbfSubarray')
    for instance in instance_list.value_string:
        try:
            if "subarray_01" in instance:
                return tango.DeviceProxy(instance)
        except tango.DevFailed:
            continue

@pytest.fixture(scope="class")
def cbf_master():
    """Create DeviceProxy for the CspMaster device
       to test the device with the TANGO DB
    """
    database = tango.Database()
    instance_list = database.get_device_exported_for_class('CbfMaster')
    for instance in instance_list.value_string:
        try:
            return tango.DeviceProxy(instance)
        except tango.DevFailed:
            continue

