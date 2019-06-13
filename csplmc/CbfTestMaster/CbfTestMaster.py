# -*- coding: utf-8 -*-
#
# This file is part of the CbfTestMaster project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" CSP.LMC subelement Test Master Tango device prototype

Test TANGO device class to test connection with the CSPMaster prototype.
It simulates the CbfMaster sub-element.
"""
from __future__ import absolute_import
import sys
import os
import time

file_path = os.path.dirname(os.path.abspath(__file__))
module_path = os.path.abspath(os.path.join(file_path, os.pardir))
sys.path.insert(0, module_path)

# Tango imports
import tango
from tango import DebugIt
from tango.server import run
from tango.server import Device, DeviceMeta
from tango.server import attribute, command
from tango.server import device_property
from tango import AttrQuality, DispLevel, DevState
from tango import AttrWriteType, PipeWriteType
# Additional import
# PROTECTED REGION ID(CbfTestMaster.additionnal_import) ENABLED START #
from future.utils import with_metaclass
import threading
from commons.global_enum import HealthState
from skabase.SKAMaster.SKAMaster import SKAMaster
# PROTECTED REGION END #    //  CbfTestMaster.additionnal_import

__all__ = ["CbfTestMaster", "main"]


class CbfTestMaster(with_metaclass(DeviceMeta,SKAMaster)):
    """
    CbfTestMaster TANGO device class to test connection with the CSPMaster prototype
    """
    # PROTECTED REGION ID(CbfTestMaster.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  CbfTestMaster.class_variable

    # -----------------
    # Device Properties
    # -----------------

    # ----------
    # Attributes
    # ----------

    commandProgress = attribute(
        dtype='uint16',
        label="Command progress percentage",
        max_value=100,
        min_value=0,
        polling_period=1000,
        abs_change=5,
        rel_change=2,
        doc="Percentage progress implemented for commands that  result in state/mode transitions for a large \nnumber of components and/or are executed in stages (e.g power up, power down)",
    )

    vccCapabilityAddress = attribute(
        dtype=('str',),
        max_dim_x=197,
    )

    fspCapabilityAddress = attribute(
        dtype=('str',),
        max_dim_x=27,
    )

    reportVCCState = attribute(
        dtype=('DevState',),
        max_dim_x=197,
    )

    reportVccHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=197,
    )

    reportVCCAdminMode = attribute(
        dtype=('uint16',),
        max_dim_x=197,
    )

    reportFSPState = attribute(
        dtype=('DevState',),
        max_dim_x=27,
    )

    reportFSPHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=27,
    )

    reportFSPAdminMode = attribute(
        dtype=('uint16',),
        max_dim_x=27,
    )

    fspMembership = attribute(
        dtype=('uint16',),
        max_dim_x=27,
    )

    vccMembership = attribute(
        dtype=('uint16',),
        max_dim_x=197,
    )

    # ---------------
    # General methods
    # ---------------

    def init_subelement(self):
        """
        Simulate the sub-element device initialization
        """
        self.set_state(tango.DevState.STANDBY)

    def on_subelement(self):
        """
        Simulate the sub-element transition from STANDBY to ON 
        """
        self.set_state(tango.DevState.ON)
        self._health_state = HealthState.DEGRADED.value

    def standby_subelement(self):
        """
        Simulate the sub-element transition from ON to STANDBY
        """
        self.set_state(tango.DevState.STANDBY)
        self._health_state = HealthState.DEGRADED.value

    def off_subelement(self):
        """
        Simulate the sub-element transition from STANDBY to OFF
        """
        self.set_state(tango.DevState.OFF)
        self._health_state = HealthState.UNKNOWN.value

    def init_device(self):
        SKAMaster.init_device(self)
        # PROTECTED REGION ID(CbfTestMaster.init_device) ENABLED START #
        
        self.set_state(tango.DevState.INIT)
        self._health_state = HealthState.UNKNOWN.value

        # start a timer to simulate device intialization
        thread = threading.Timer(1, self.init_subelement)
        thread.start()

        # PROTECTED REGION END #    //  CbfTestMaster.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(CbfTestMaster.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CbfTestMaster.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(CbfTestMaster.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CbfTestMaster.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_commandProgress(self):
        # PROTECTED REGION ID(CbfTestMaster.commandProgress_read) ENABLED START #
        return 0
        # PROTECTED REGION END #    //  CbfTestMaster.commandProgress_read

    def read_vccCapabilityAddress(self):
        # PROTECTED REGION ID(CbfTestMaster.vccCapabilityAddress_read) ENABLED START #
        return ['']
        # PROTECTED REGION END #    //  CbfTestMaster.vccCapabilityAddress_read

    def read_fspCapabilityAddress(self):
        # PROTECTED REGION ID(CbfTestMaster.fspCapabilityAddress_read) ENABLED START #
        return ['']
        # PROTECTED REGION END #    //  CbfTestMaster.fspCapabilityAddress_read

    def read_reportVCCState(self):
        # PROTECTED REGION ID(CbfTestMaster.reportVCCState_read) ENABLED START #
        return [tango.DevState.UNKNOWN]
        # PROTECTED REGION END #    //  CbfTestMaster.reportVCCState_read

    def read_reportVccHealthState(self):
        # PROTECTED REGION ID(CbfTestMaster.reportVccHealthState_read) ENABLED START #
        return [0]
        # PROTECTED REGION END #    //  CbfTestMaster.reportVccHealthState_read

    def read_reportVCCAdminMode(self):
        # PROTECTED REGION ID(CbfTestMaster.reportVCCAdminMode_read) ENABLED START #
        return [0]
        # PROTECTED REGION END #    //  CbfTestMaster.reportVCCAdminMode_read

    def read_reportFSPState(self):
        # PROTECTED REGION ID(CbfTestMaster.reportFSPState_read) ENABLED START #
        return [tango.DevState.UNKNOWN]
        # PROTECTED REGION END #    //  CbfTestMaster.reportFSPState_read

    def read_reportFSPHealthState(self):
        # PROTECTED REGION ID(CbfTestMaster.reportFSPHealthState_read) ENABLED START #
        return [0]
        # PROTECTED REGION END #    //  CbfTestMaster.reportFSPHealthState_read

    def read_reportFSPAdminMode(self):
        # PROTECTED REGION ID(CbfTestMaster.reportFSPAdminMode_read) ENABLED START #
        return [0]
        # PROTECTED REGION END #    //  CbfTestMaster.reportFSPAdminMode_read

    def read_fspMembership(self):
        # PROTECTED REGION ID(CbfTestMaster.fspMembership_read) ENABLED START #
        return [0]
        # PROTECTED REGION END #    //  CbfTestMaster.fspMembership_read

    def read_vccMembership(self):
        # PROTECTED REGION ID(CbfTestMaster.vccMembership_read) ENABLED START #
        return [0]
        # PROTECTED REGION END #    //  CbfTestMaster.vccMembership_read

    # --------
    # Commands
    # --------

    @command(
    dtype_in=('str',), 
    doc_in="If the array length is0, the command apllies to the whole\nCSP Element.\nIf the array length is > 1, each array element specifies the FQDN of the\nCSP SubElement to switch ON.", 
    )
    @DebugIt()
    def On(self, argin):
        # PROTECTED REGION ID(CbfTestMaster.On) ENABLED START #
        thread = threading.Timer(2, self.on_subelement)
        thread.start()
        # PROTECTED REGION END #    //  CbfTestMaster.On

    @command(
    dtype_in=('str',), 
    doc_in="If the array length is0, the command apllies to the whole\nCSP Element.\nIf the array length is > 1, each array element specifies the FQDN of the\nCSP SubElement to switch OFF.", 
    )
    @DebugIt()
    def Off(self, argin):
        # PROTECTED REGION ID(CbfTestMaster.Off) ENABLED START #
        thread = threading.Timer(1, self.off_subelement)
        thread.start()
        # PROTECTED REGION END #    //  CbfTestMaster.Off

    @command(
        dtype_in=('str',),
        doc_in="If the array length is0, the command apllies to the whole\nCSP Element.\n\
                If the array length is > 1, each array element specifies the FQDN of the\n\
                CSP SubElement to switch OFF.",
    )

    @DebugIt()
    def Standby(self, argin):
        # PROTECTED REGION ID(CbfTestMaster.Standby) ENABLED START #
        thread = threading.Timer(2, self.standby_subelement)
        thread.start()
        # PROTECTED REGION END #    //  CbfTestMaster.Standby

    def is_Off_allowed(self):
        # PROTECTED REGION ID(CbfTestMaster.is_Off_allowed) ENABLED START #
        if self.get_state() not in [DevState.STANDBY]:
            return False
        return True
        # PROTECTED REGION END #    //  CbfTestMaster.is_Off_allowed.

    def is_Standby_allowed(self):
        # PROTECTED REGION ID(CbfTestMaster.is_Standby_allowed) ENABLED START #
        if self.get_state() not in [DevState.ON, DevState.OFF]:
            return False
        return True
        # PROTECTED REGION END #    //  CbfTestMaster.is_Standby_allowed

    def is_On_allowed(self):
        # PROTECTED REGION ID(CbfTestMaster.is_On_allowed) ENABLED START #
        if self.get_state() not in [DevState.STANDBY]:
            return False
        return True
        # PROTECTED REGION END #    //  CbfTestMaster.is_On_allowed

# ----------
# Run server
# ----------

def main(args=None, **kwargs):
    # PROTECTED REGION ID(CbfTestMaster.main) ENABLED START #
    return run((CbfTestMaster,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CbfTestMaster.main

if __name__ == '__main__':
    main()
