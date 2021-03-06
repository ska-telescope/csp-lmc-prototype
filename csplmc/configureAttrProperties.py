# This script is used only when the CSP.LMC devices are run via
# the start_prototype script.
# Docker containers rely on dsconfig device to configure the TANGO Attribute properties.
#!/usr/bin/env python
import json
from tango import AttributeProxy, ChangeEventInfo

# Update file path to devices.json in order to test locally

with open('./csplmc/devices.json', 'r') as file:
    jsonDevices = file.read().replace('\n', '')

# Loading devices.json file and creating an object
json_devices = json.loads(jsonDevices)

for device in json_devices:
    deviceName = device["devName"]

    for attributeProperty in device["attributeProperties"]:
        if attributeProperty["attrPropName"] == "__root_att":
            continue
        attributeProxy = AttributeProxy(deviceName + "/" + attributeProperty["attributeName"])
        if attributeProperty["pollingPeriod"] != "":
            attributeProxy.poll(attributeProperty["pollingPeriod"])
            if attributeProperty["changeEventAbs"] != "":
                attrInfoEx = attributeProxy.get_config()
                absChange = ChangeEventInfo()
                absChange.abs_change = attributeProperty["changeEventAbs"]
                attrInfoEx.events.ch_event = absChange
                attributeProxy.set_config(attrInfoEx)
