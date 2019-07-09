#!/usr/bin/env python
from tango import AttributeProxy, ChangeEventInfo, AttributeInfoEx
import json

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
            if(attributeProperty["pollingPeriod"] != ""):
                attributeProxy.poll(attributeProperty["pollingPeriod"])

            if(attributeProperty["changeEventAbs"] != ""):
                attrInfoEx = attributeProxy.get_config()
                absChange = ChangeEventInfo()
                absChange.abs_change = attributeProperty["changeEventAbs"]
                attrInfoEx.events.ch_event = absChange
                attributeProxy.set_config(attrInfoEx)
