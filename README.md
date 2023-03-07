# JBD-BMS-Bluetooth

First, a big thank you to tgalarneau for creating his bms project, which I used as a base to
build this code. tgalarneau's bms project is a more general purpose project that uses socket or
mqtt connections. I needed a streamlined mqtt based code set that simply published a single
mqtt message to a broker, which I will process into a MariaDB database and then display using
Grafana. And I only need to process 4 cell (12v) batteries.

His project is more sophisticated by far, and you should check it out.

I've added several features to the python code. 

1) You can pass a BLE device name or address. If an address is passed the code simply uses it. 
If a name is passed the code will scan all localbluetooth devices to find a matching name, 
extract its address, and use it.

2) The code will query basic BMS data and cell voltage data, and then combine that data into a 
single mqtt messsage. 

3) The processing interval is changed to use minutes rather than seconds, and there is now an  
option to use a "one and done" process by passing in a zero (0) for the interval option.

4) The code has more comments explaining things, and was restructured for more clarity.

==================================================================================================

This code runs fine on the latest Rasperry Pi OS (Bullseye) and is being used on 3b+ and 4b 
models (1gb 3b+ and 8gb 4b). You will need Python3 installed. You will need bluepy installed.
And you will need paho installed. And of course you will need a MQTT package and a MQTT 
broker set up to send the messages to. Other than that, it's straight forward..

==================================================================================================

The code should be run as SUDO as it does low level BLE scanning.

Run it as follows:

   sudo python jbd-bms-mqtt.py -n "Cabin 580ah" -i 0 -t solar
   or
   sudo python jbd-bms-mqtt.py -a "a4:c1:38:30:c2:8e" -i 0 -t solar

This will scan for a bluetooth device called "Cabin 580ah" and extract its
bluetooth address, or, use the passed address if provided, then try and attach
to the BMS and read a set if variables, one time, and then publish a MQTT
message with those variables to the Topic "solar".

USAGE NOTE
If you use a value other than 0 for the -i parm the program will loop forever
and read the BMS values every X minutes based on the value you passed. This is
not recommended as a long term method to run the script, as it could cause
resource issues in the python environment. For an ongoing run please use a
cron job to control run times and pass a 0 for the -i argument...

In addition, if you run this program via a manual shell loop instead of using
cron, and someone attached to the BMS using a bluetooth app (like XiaoxiangBMS
or SmartBMSUtility) the code will fail when it attempts to connect (as the other
app has the connection) and will throw an exception. If you started it intending
it to run "forever" in a terminal window you will not realize it's failed.

If cron is used, at least the process will be kicked off again based on the cron
process and try to reconnect again, automatically...

You've been warned!
