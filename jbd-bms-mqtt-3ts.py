#!/usr/bin/env python3
# This is the 3 temperature sensor version of the code.
#
# This code should be run as SUDO as it does low level BLE scanning.
#
# Run it as follows:
#
#   sudo python jbd-bms-mqtt.py -n "Cabin 580ah" -i 0 -t solar
#   or
#   sudo python jbd-bms-mqtt.py -a "a4:c1:38:30:c2:8e" -i 0 -t solar
#
# This will scan for a bluetooth device called "Cabin 580ah" and extract its
# bluetooth address, or, use the passed address if provided, then try and attach
# to the BMS and read a set if variables, one time, and then publish a MQTT
# message with those variables to the Topic "solar".
#
# USAGE NOTE
# If you use a value other than 0 for the -i parm the program will loop forever
# and read the BMS values every X minutes based on the value you passed. This is
# not recommended as a long term method to run the script, as it could cause
# resource issues in the python environment. For an ongoing run please use a
# cron job to control run times and pass a 0 for the -i argument...
#
# In addition, if you run this program via a manual shell loop instead of using
# cron, and someone attached to the BMS using a bluetooth app (like XiaoxiangBMS
# or SmartBMSUtility) the code will fail when it attempts to connect (as the other
# app has the connection) and will throw an exception. If you started it intending
# it to run "forever" in a terminal window you will not realize it's failed.
#
# If cron is used, at least the process will be kicked off again based on the cron
# process and try to reconnect again, automatically...
#
# You've been warned!

from bluepy.btle import Peripheral, DefaultDelegate, BTLEException
from bluepy.btle import Scanner, DefaultDelegate
import sys
import struct
import argparse
import json
import time
import binascii
import atexit
import paho.mqtt.client as paho


def disconnect():
    mqtt.disconnect()
    print("broker disconnected")


def cellinfo1(data):  # process battery info
    print("Processing (dd03) battery info 1...")
    infodata = data
    print("Raw infodata1 ", infodata)
    # Unpack into variables, skipping header bytes 0-3
    volts, amps, remain, capacity, cycles, mdate, balance1, balance2 = struct.unpack_from('>HhHHHHHH', infodata, 4)
    volts = volts / 100
    amps = amps / 100
    capacity = capacity / 100
    remain = remain / 100
    global ginfo
    ginfo.append(volts)
    ginfo.append(amps)
    ginfo.append(capacity)
    ginfo.append(remain)
    print(ginfo)
    time.sleep(timeSleep)


def cellinfo2(data):  # process battery info
    print("Processing (dd03) battery info 2...")
    infodata = data
    print("Raw infodata2 ", infodata)
    # Unpack into variables, no header as this is the 2nd part message
    protect, vers, percent, fet, cells, sensors, temp1, temp2, temp3, b77 = struct.unpack_from('>HBBBBBHHHB', infodata, 0)
    temp1 = (temp1-2731)/10
    temp2 = (temp2-2731)/10
    prt = (format(protect, "b").zfill(16))		# protect trigger (0,1)(off,on)
    global ginfo
    ginfo.append(percent)
    ginfo.append(temp1)
    ginfo.append(temp2)
    print(ginfo)
    time.sleep(timeSleep)


def cellvolts1(data):  # process cell voltages
    print("Processing (dd04) cell volts message...")
    celldata = data
    print("Raw celldata ", celldata)
    # Unpack into variables, skipping header bytes 0-3
    cell1, cell2, cell3, cell4 = struct.unpack_from('>HHHH', celldata, 4)
    global ginfo
    ginfo.append(cell1)
    ginfo.append(cell2)
    ginfo.append(cell3)
    ginfo.append(cell4)
    print(ginfo)
    time.sleep(timeSleep)


class MyDelegate(DefaultDelegate):  # When the device replies this code is invoked to deal with it
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleNotification(self, cHandle, data):
        hex_data = binascii.hexlify(data)  # Given raw bytes, get an ASCII string representing the hex values
        text_string = hex_data.decode('utf-8')  # Check incoming data for routing to decoding routines
        if text_string.find('dd03') != -1:  # x03
            cellinfo1(data)  # Decode and process BMS info1
        elif text_string.find('77') != -1 and len(text_string) == 32 or len(text_string) == 36:  # x03
            cellinfo2(data)  # Decode and process BMS info2
        elif text_string.find('dd04') != -1:  # x04
            cellvolts1(data)  # Decode and process cell info
        else:
            print("Why Am I Here? What is this data", text_string)


# Mainline Code

# Process command line arguments and set up variables
parser = argparse.ArgumentParser(description='Fetches and outputs JBD bms data')
parser.add_argument("-n", "--name", help="BLE Device Name", required=False)
parser.add_argument("-a", "--address", help="BLE Device Address", required=False)
parser.add_argument("-i", "--interval", type=int, help="Read interval in minutes, 0=One & Done", required=True)
parser.add_argument("-t", "--topic", help="MQTT Topic name", required=True)
args = parser.parse_args()
loopMinutes = args.interval * 60  # Takes the input value and turns it into minutes
topic = args.topic  # Topic to use when posting to MQTT
bleName = args.name  # BLE device Name that will be scanned for to get address
bleAddrP = args.address  # BLE address that will be used rather than a BLE name
timeSleep = 1  # Used to slow things down a bit in case of timing issues
ginfo = list()  # Global list to hold elements from the various requests
broker = "192.168.1.98"  # Change this to your MQTT broker address
port = 1883  # Default port that MQTT is listening on

# Resolve the BLE device address using a name or a provided address
if not bleAddrP and not bleName:
    sys.exit("Process needs either a ble Name or ble Address...Halting!")
elif bleName:
    print("Searching for ble Name = '%s'" % bleName)
    scanner = Scanner()
    devices = scanner.scan(5)  # Scan for 5 seconds
    print("============ Scanning Results  ==============")
    for dev in devices:
        for (adtype, desc, value) in dev.getScanData():
            print("Device = '%s'   Name = '%s'" % (dev.addr, value))
            if value == bleName:
                print("=========== Found It ==============")
                print("Name = %s" % value)
                print("Device = %s" % dev.addr)
                print("RSSI = %d dB" % dev.rssi)
                print("===================================")
                bleAddr = dev.addr
else:
    bleAddr = bleAddrP  # Use the command line parm address

try:  # If the variable was created above the BLE device was found
    bleAddr
except NameError:
    sys.exit("Do not have a usable BLE device address...Halting!")

# Main Loop Logic Begins Here
while True:

    try:  # Attempt a connection with the BMS via BLE
        print('Attempting to connect...')
        bms = Peripheral(bleAddr, addrType="public")
    except BTLEException as ex:
        time.sleep(30)  # timeSleep not used here, this waits 30 seconds between attempts
        print('1st attempt failed, trying 2nd time to connect...')
        bms = Peripheral(bleAddr, addrType="public")
    except NameError:
        sys.exit("Can not connect to the BLE device...Halting!")
        # This means something went wrong as there is a ble address to use but it could not
        # be connected. Maybe some other application has the connection already and someone
        # forgot to disconnect when they were done configuring the BMS.
    else:
        print('Connected...', bleAddr)

    atexit.register(disconnect)  # run the disconnect function when with the loop
    mqtt = paho.Client("control3")  # create and connect mqtt client
    mqtt.connect(broker, port)
    bms.setDelegate(MyDelegate())  # setup BlueTooth process delegate to get returned notifications

    # write x03 record to request battery info
    resultx03 = bms.writeCharacteristic(0x15, b'\xdd\xa5\x03\x00\xff\xfd\x77', False)
    bms.waitForNotifications(5)  # wait up to 5 seconds for response message
    bms.waitForNotifications(5)  # There are 2 replies for the X03 request

    # write x04 record to request cell volts info
    resultx04 = bms.writeCharacteristic(0x15, b'\xdd\xa5\x04\x00\xff\xfc\x77', False)
    bms.waitForNotifications(5)  # wait up to 5 seconds for response message

    # Disconnect from BMS BLE connection. This allows other applications and tools the chance
    # to connect to the BMS via Bluetooth.
    bms.disconnect()

    try:    # Do this try in case there is a short ginfo list count
        # Load the JSON message with the merged BMS data and send it via MQTT
        time.sleep(timeSleep)
        gvolts = ginfo[0]
        gamps = ginfo[1]
        gcapacity = ginfo[2]
        gremain = ginfo[3]
        gpercent = ginfo[4]
        gtemp1 = ginfo[5]
        gtemp2 = ginfo[6]
        gcellvolt1 = ginfo[7]
        gcellvolt2 = ginfo[8]
        gcellvolt3 = ginfo[9]
        gcellvolt4 = ginfo[10]
        message0 = {
            "topic": topic,
            "volts": gvolts,
            "amps": gamps,
            "capacity": gcapacity,
            "remain": gremain,
            "percent": gpercent,
            "temp1": gtemp1,
            "temp2": gtemp2,
            "cell1": gcellvolt1,
            "cell2": gcellvolt2,
            "cell3": gcellvolt3,
            "cell4": gcellvolt4
        }
        ret = mqtt.publish(topic, payload=json.dumps(message0), qos=0, retain=False)
    except:
        print("There is a short ginfo list, apparently a response message was missed")

    if loopMinutes != 0:  # Loop unless interval is 0, otherwise one & done
        while len(ginfo) > 0:  # If looping the ginfo list needs to be cleaned or it just grows and grows
            del ginfo[0]
        time.sleep(loopMinutes)
    else:
        break
