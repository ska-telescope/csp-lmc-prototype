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
def tango_context(request):
    """Creates and returns a TANGO DeviceTestContext object
       with process=False.

    Parameters
    ----------
    request: _pytest.fixtures.SubRequest
        A request object gives access to the requesting test context.
    """
    # TODO: package_name and class_name can be used in future
    # fq_test_class_name = request.cls.__module__
    # fq_test_class_name_details = fq_test_class_name.split(".")
    # package_name = fq_test_class_name_details[1]
    # class_name = module_name = fq_test_class_name_details[1]
    properties={'MaxCapabilities': ['SearchBeam:1500', 'TimingBeam:16']}
    module = importlib.import_module("{}.{}".format("CspMaster", "CspMaster"))
    klass = getattr(module, "CspMaster")
    tango_context = DeviceTestContext(klass, properties=properties)
    tango_context.start()
    klass.get_name = mock.Mock(side_effect=tango_context.get_device_access)
    yield tango_context
    tango_context.stop()

@pytest.fixture(scope="function")
def initialize_device(tango_context):
    """Re-initializes the device.

    Parameters
    ----------
    tango_context: tango.test_context.DeviceTestContext
        Context to run a device without a database.
    """
    print("Initialize device")
    yield tango_context.device.Init()

@pytest.fixture(scope="class")
def cbfmaster_proxy():
    """Create DeviceProxy for the CbfTestMaster
       to test commands forwarding.
    """
#    cbf_proxy = DeviceProxy("mid_csp_cbf/sub_elt/master")
#    return cbf_proxy
    database = tango.Database()
    instance_list = database.get_device_exported_for_class('CbfTestMaster')
    for instance in instance_list.value_string:
        try:
            return tango.DeviceProxy(instance)
        except tango.DevFailed:
            continue

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

