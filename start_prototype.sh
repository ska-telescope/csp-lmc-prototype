#!/bin/bash
#
# Script to start CSP.LMC prototype TANGO devices.
# The script:
# - checks if the TANGO DB is running
# - if the devices are already registered with the TANGO DB, otherwise it adds
#   them using the tango_admin command
# - start the devices
# - check if the jive tool is installed in the system
# - starts jive if it's not already running  
#

FILE=jive
#check if TANGO DB is up
tango_admin --ping-database	
if [ $? -eq 0 ]; then 
        # configure device properties 
        sleep 2
        echo "Configuring Class/Device properties"
        python csplmc/configureDevices.py
        sleep 2
        # TANGO DB is running -> check for CbfTestMaster device existence
        tango_admin --check-device mid_csp_cbf/sub_elt/master  >> /dev/null
        if [ $? -eq 0 ]; then
           echo "CbfTestMaster device already register in the TANGO DB"
        else
           echo  "Adding CbfTestMaster device to DB"
           tango_admin --add-server CbfTestMaster/test CbfTestMaster mid_csp_cbf/sub_elt/master
        fi
        echo "Starting the CbfTestMaster device"
        python csplmc/CbfTestMaster/CbfTestMaster.py test >/dev/null 2>&1 &
        sleep 1 # need to wait long enough for the above to return a fail error code
        ps $! > /dev/null
        if [ $? -ne 0 ]; then
            echo "CbfTestMaster device failure"
        else
            sleep 1
        fi
        # TANGO DB is running -> check for CspMaster device existence
        tango_admin --check-device mid_csp/elt/master
        if [ $? -eq 0 ]; then
           echo "CspMaster device already register in the TANGO DB"
        else
           echo  "Adding the CspMaster device to DB"
           tango_admin --add-server CspMaster/csp CspMaster mid_csp/elt/master
        fi
        echo "Starting the CspMaster device"
        python csplmc/CspMaster/CspMaster/CspMaster.py csp >/dev/null 2>&1 &
        sleep 1 # need to wait long enough for the above to return a fail error code
        ps $! > /dev/null
        if [ $? -ne 0 ]; then
            echo "CspMaster device failure"
        fi
        # check for CspSubarray1 device existence
        tango_admin --check-device mid_csp/elt/subarray_01
        if [ $? -eq 0 ]; then
           echo "CspSubarray1 device already register in the TANGO DB"
        else
           echo  "Adding the CspSubarray1 device to DB"
           tango_admin --add-server CspSubarray/sub1 CspSubarray mid_csp/elt/subarray_01
        fi
        echo "Starting the CspSubarray1 device"
        python csplmc/CspSubarray/CspSubarray/CspSubarray.py sub1 >/dev/null 2>&1 &
        sleep 1 # need to wait long enough for the above to return a fail error code
        ps $! > /dev/null
        if [ $? -ne 0 ]; then
            echo "CspSubarray1 device failure"
        fi
        # check for jive tool 
        command_line="which $FILE"
        return=`$command_line`
        echo $return
        if [ $? -gt 0 ]; then
            echo "Jive tool not found"  
            # jive tool found. Go to run it
        else
            # check if jive is already running
            jive=$(pgrep -a $FILE| awk '{print $3}')
            len=${#jive}
            if [ $len -eq 0 ]; then
                #no jive running, start it
                echo "Starting jive..." 
                $return &
            fi
        fi
else 
   echo "TANGO DB not running"	
fi


