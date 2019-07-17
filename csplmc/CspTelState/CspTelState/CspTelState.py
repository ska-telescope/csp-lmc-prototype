# -*- coding: utf-8 -*-
#
# This file is part of the CspTelState project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" 

The CspTelState device expose CSP parameters used by other Elements, also used 
for information exchange between CSP Sub-elements.
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
from tango import DebugIt, DeviceProxy, EventType
from tango.server import run, Device, DeviceMeta, attribute, command, device_property

# PROTECTED REGION ID(CspTelState.additional_import) ENABLED START #
# add the path to import global_enum package.
file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

# Additional import
import global_enum as const
from global_enum import HealthState, AdminMode
from skabase.SKATelState import SKATelState
# PROTECTED REGION END #    //  CspTelState.additionnal_import

__all__ = ["CspTelState", "main"]


class CspTelState(with_metaclass(DeviceMeta, SKATelState)):
    """
    The CspTelState device expose CSP parameters used by other Elements, also used 
    for information exchange between CSP Sub-elements.
    """
    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(CspTelState.class_variable) ENABLED START #

    #Class private methods

    def csp_subarray_change_callback(self, evt):
        """
        *Class private method.*

        Retrieve the values of the sub-element sub-arrays SCM attributes subscribed for change
        event at device initialization.

        Args: 
            evt: The event data

        Returns:
            None
        """
        if evt.err is False:
            try:
                print("err:", evt.err)
                print(evt.attr_name)
                if "cbfoutputlink" in evt.attr_name:
                    attr_name = evt.attr_name
                    # get the number of the subarray
                    pos = attr_name.find("subarray_")
                    # pos+9 is the starting position of the subarray Id 
                    subarray_id = int(attr_name[pos + 9:pos + 11])
                    # store the new output link value
                    self._cbf_output_links[subarray_id - 1] = evt.attr_value.value
                    print(self._cbf_output_links[subarray_id - 1])
                    # get the subarray ID value to build the name of the CspTelState outputlink 
                    # attribute. This has the form "cbfOutputLinkN"  where N is the subarray ID
                    attr_name = "cbfOutputLinks" + str(subarray_id)
                    # publish the outputlink
                    self.push_change_event(attr_name, self._cbf_output_links[subarray_id - 1])
                else:
                    self.dev_logging("Attribute {} not yet handled".format(evt.attr_name), 
                                     tango.LogLevel.LOG_ERROR)
                    
            except tango.DevFailed as df:
                #self.dev_logging(str(df.args[0].desc), tango.LogLevel.LOG_ERROR)
                print(df)
        else: 
            for item in evt.errors: 
                # TODO handle API_EventTimeout
                #
                log_msg = item.reason + ": on attribute " + str(evt.attr_name)
                print(log_msg)
                #self.dev_logging(log_msg, tango.LogLevel.LOG_WARN)

    def __connect_to_master(self):
        """
        *Class private method.*

        Establish connection with the CSP Element Master devices to get information about
        the CSP Subarray devices FQDNs.

        Returns:
            None
        Raises: 
            DevFailed: when connection to the CspMaster device fails.
        """
        try:
            self.dev_logging("Trying connection to {}".format(self.CspMaster), int(tango.LogLevel.LOG_INFO))
            self._csp_master_proxy = tango.DeviceProxy(self.CspMaster)
            self._csp_master_proxy.ping()
            # get the list of CSP Subarray FQDNs
            self._csp_subarrays_fqdn = list(self._csp_master_proxy.cspSubarrayAddress)
            print(self._csp_subarrays_fqdn)
        except tango.DevFailed as df:
            tango.Except.throw_exception("Connection Failed", df.args[0].desc,
                                         "connect_to_master ", tango.ErrSeverity.ERR)

    def __connect_to_subarrays(self):
        """
        *Class private method.*

        Establish connection with each CSP sub-array.
        If connection succeeds, the CspTelState device subscribes attributes it has to publish 
        for that subarray
        Returns:
            None
        Raises:
            tango.DevFailed: raises an execption if connection with a CSP Subarray fails
        """

        err_msg = ''
        for fqdn in self._csp_subarrays_fqdn:
            # initialize the list for each dictionary key-name
            self._csp_subarray_event_id[fqdn] = []
            try:
                log_msg = "Trying connection to" + str(fqdn) + " device"
                self.dev_logging(log_msg, int(tango.LogLevel.LOG_INFO))
                device_proxy = tango.DeviceProxy(fqdn)
                device_proxy.ping()
                # add to the list of subarray FQDNS only registered subarrays
                self._csp_subarrays_fqdn.append(fqdn)  
                # store the sub-element proxies 
                self._csp_subarray_proxies[fqdn] = device_proxy

                # Subscription of the sub-element State,healthState and adminMode
                ev_id = device_proxy.subscribe_event("cbfOutputLink", EventType.CHANGE_EVENT,
                        self.csp_subarray_change_callback, stateless=True)
                self._csp_subarray_event_id[fqdn].append(ev_id)

            except tango.DevFailed as df:
                for item in df.args: 
                    err_msg += "Failure in connection to " + str(fqdn) + \
                                " device: " + str(item.reason) + " "

            if not err_msg == False:
                self.dev_logging(err_msg, int(tango.LogLevel.LOG_ERROR))
                tango.Except.throw_exception("Connection failed", err_msg,
                                             "Connect to subarrays", tango.ErrSeverity.ERR)
    # PROTECTED REGION END #    //  CspTelState.class_variable


    # -----------------
    # Device Properties
    # -----------------

    CspMaster = device_property(
        dtype='str', default_value="mid_csp/elt/master"
    )


    # ----------
    # Attributes
    # ----------

    cbfOutputLinks1 = attribute(
        dtype='str',
        label="Cbf Subarray-01 output links",
        doc="The output links distribution for Cbf Subarray-01.",
    )

    cbfOutputLinks2 = attribute(
        dtype='str',
        label="Cbf Subarray-02 output links",
        doc="The output links distribution for Cbf Subarray-02.",
    )

    cbfOutputLinks3 = attribute(
        dtype='str',
        label="Cbf Subarray-03 output links",
        doc="The output links distribution for Cbf Subarray-03.",
    )

    cbfOutputLinks4 = attribute(
        dtype='str',
        label="Cbf Subarray-04 output links",
        doc="The output links distribution for Cbf Subarray-04.",
    )

    cbfOutputLinks5 = attribute(
        dtype='str',
        label="Cbf Subarray-05 output links",
        doc="The output links distribution for Cbf Subarray-05.",
    )

    cbfOutputLinks6 = attribute(
        dtype='str',
        label="Cbf Subarray-06 output links",
        doc="The output links distribution for Cbf Subarray-06.",
    )

    cbfOutputLinks7 = attribute(
        dtype='str',
        label="Cbf Subarray-07 output links",
        doc="The output links distribution for Cbf Subarray-07.",
    )

    cbfOutputLinks8 = attribute(
        dtype='str',
        label="Cbf Subarray-08 output links",
        doc="The output links distribution for Cbf Subarray-08.",
    )

    cbfOutputLinks9 = attribute(
        dtype='str',
        label="Cbf Subarray-09 output links",
        doc="The output links distribution for Cbf Subarray-09.",
    )

    cbfOutputLinks10 = attribute(
        dtype='str',
        label="Cbf Subarray-10 output links",
        doc="The output links distribution for Cbf Subarray-10.",
    )

    cbfOutputLinks11 = attribute(
        dtype='str',
        label="Cbf Subarray-11 output links",
        doc="The output links distribution for Cbf Subarray-11.",
    )

    cbfOutputLinks12 = attribute(
        dtype='str',
        label="Cbf Subarray-12 output links",
        doc="The output links distribution for Cbf Subarray-12.",
    )

    cbfOutputLinks13 = attribute(
        dtype='str',
        label="Cbf Subarray-13 output links",
        doc="The output links distribution for Cbf Subarray-13.",
    )

    cbfOutputLinks14 = attribute(
        dtype='str',
        label="Cbf Subarray-14 output links",
        doc="The output links distribution for Cbf Subarray-14.",
    )

    cbfOutputLinks15 = attribute(
        dtype='str',
        label="Cbf Subarray-15 output links",
        doc="The output links distribution for Cbf Subarray-15.",
    )

    cbfOutputLinks16 = attribute(
        dtype='str',
        label="Cbf Subarray-16 output links",
        doc="The output links distribution for Cbf Subarray-16.",
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKATelState.init_device(self)
        # PROTECTED REGION ID(CspTelState.init_device) ENABLED START #
        # connect to CspMaster to get the list of CspSubarray FQDNs

        # initialize the private class attributes
        self._csp_master_proxy = 0          # CspMaster DeviceProxy
        self._csp_subarrays_fqdn = 0        # list of CspSubarray FQDNs
        # NOTE: the dict keys are the CspSubarrays FQDNs
        self._csp_subarray_event_id = {}    # dict of the events subscribed for each CspSubarray
        self._csp_subarray_proxies = {}     # dict of CspSubarrays DeviceProxy
        self._cbf_output_links = ['']*16         # list with Cbf outputlinks  values
        try: 
            self.__connect_to_master()
            self.__connect_to_subarrays()
            self.set_state(tango.DevState.ON)
            self._health_state = HealthState.OK.value
        except tango.DevFailed as df:
            print(df)
            msg = "Failure in connection:" + str(df.args[0].reason)
            self.dev_logging(msg, tango.LogLevel.LOG_ERROR)
            print(msg)
            self._health_state = HealthState.DEGRADED.value

        # PROTECTED REGION END #    //  CspTelState.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(CspTelState.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CspTelState.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(CspTelState.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CspTelState.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_cbfOutputLinks1(self):
        # PROTECTED REGION ID(CspTelState.cbfOutputLinks1_read) ENABLED START #
        print(self._cbf_output_links[0])
        print(self._cbf_output_links[1])
        print(self._cbf_output_links[2])
        return self._cbf_output_links[0]
        # PROTECTED REGION END #    //  CspTelState.cbfOutputLinks1_read

    def read_cbfOutputLinks2(self):
        # PROTECTED REGION ID(CspTelState.cbfOutputLinks2_read) ENABLED START #
        return self._cbf_output_links[1]
        # PROTECTED REGION END #    //  CspTelState.cbfOutputLinks2_read

    def read_cbfOutputLinks3(self):
        # PROTECTED REGION ID(CspTelState.cbfOutputLinks3_read) ENABLED START #
        return self._cbf_output_links[2]
        # PROTECTED REGION END #    //  CspTelState.cbfOutputLinks3_read

    def read_cbfOutputLinks4(self):
        # PROTECTED REGION ID(CspTelState.cbfOutputLinks4_read) ENABLED START #
        return self._cbf_output_links[3]
        # PROTECTED REGION END #    //  CspTelState.cbfOutputLinks4_read

    def read_cbfOutputLinks5(self):
        # PROTECTED REGION ID(CspTelState.cbfOutputLinks5_read) ENABLED START #
        return self._cbf_output_links[4]
        # PROTECTED REGION END #    //  CspTelState.cbfOutputLinks5_read

    def read_cbfOutputLinks6(self):
        # PROTECTED REGION ID(CspTelState.cbfOutputLinks6_read) ENABLED START #
        return self._cbf_output_links[5]
        # PROTECTED REGION END #    //  CspTelState.cbfOutputLinks6_read

    def read_cbfOutputLinks7(self):
        # PROTECTED REGION ID(CspTelState.cbfOutputLinks7_read) ENABLED START #
        return self._cbf_output_links[6]
        # PROTECTED REGION END #    //  CspTelState.cbfOutputLinks7_read

    def read_cbfOutputLinks8(self):
        # PROTECTED REGION ID(CspTelState.cbfOutputLinks8_read) ENABLED START #
        return self._cbf_output_links[7]
        # PROTECTED REGION END #    //  CspTelState.cbfOutputLinks8_read

    def read_cbfOutputLinks9(self):
        # PROTECTED REGION ID(CspTelState.cbfOutputLinks9_read) ENABLED START #
        return self._cbf_output_links[8]
        # PROTECTED REGION END #    //  CspTelState.cbfOutputLinks9_read

    def read_cbfOutputLinks10(self):
        # PROTECTED REGION ID(CspTelState.cbfOutputLinks10_read) ENABLED START #
        return self._cbf_output_links[9]
        # PROTECTED REGION END #    //  CspTelState.cbfOutputLinks10_read

    def read_cbfOutputLinks11(self):
        # PROTECTED REGION ID(CspTelState.cbfOutputLinks11_read) ENABLED START #
        return self._cbf_output_links[10]
        # PROTECTED REGION END #    //  CspTelState.cbfOutputLinks11_read

    def read_cbfOutputLinks12(self):
        # PROTECTED REGION ID(CspTelState.cbfOutputLinks12_read) ENABLED START #
        return self._cbf_output_links[11]
        # PROTECTED REGION END #    //  CspTelState.cbfOutputLinks12_read

    def read_cbfOutputLinks13(self):
        # PROTECTED REGION ID(CspTelState.cbfOutputLinks13_read) ENABLED START #
        return self._cbf_output_links[12]
        # PROTECTED REGION END #    //  CspTelState.cbfOutputLinks13_read

    def read_cbfOutputLinks14(self):
        # PROTECTED REGION ID(CspTelState.cbfOutputLinks14_read) ENABLED START #
        return self._cbf_output_links[13]
        # PROTECTED REGION END #    //  CspTelState.cbfOutputLinks14_read

    def read_cbfOutputLinks15(self):
        # PROTECTED REGION ID(CspTelState.cbfOutputLinks15_read) ENABLED START #
        return self._cbf_output_links[14]
        # PROTECTED REGION END #    //  CspTelState.cbfOutputLinks15_read

    def read_cbfOutputLinks16(self):
        # PROTECTED REGION ID(CspTelState.cbfOutputLinks16_read) ENABLED START #
        return self._cbf_output_links[15]
        # PROTECTED REGION END #    //  CspTelState.cbfOutputLinks16_read


    # --------
    # Commands
    # --------

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(CspTelState.main) ENABLED START #
    return run((CspTelState,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CspTelState.main

if __name__ == '__main__':
    main()
