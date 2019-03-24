# sim7000-tools
A few scripts for testing the SIM7000E cellular module.

## Installation

  * Install python3

  * Install pyserial package i.e. ```pip3 install pyserial```

  * Set the port and baud rate variable near the start of sim7000.py.

## Usage

  * Change to the directory were the sim7000.py file lives.

  * Run the script with a command option.
    * i.e. ```python3 sim7000.py ping```


  * Use --reboot option to reboot before running the command (resets connections etc., gives you a clean run)
    * i.e. ```python3 sim7000.py ping --reboot```

## Commands

  * ```python3 sim7000.py ping```
    * Check we can ping google


  * ```python3 sim7000.py ntp```
    * Get the time from an NTP server


  * ```python3 sim7000.py http1```
    * Simple HTTP GET using HTTPREAD


  * ```python3 sim7000.py http2```
    * Simple HTTP GET using SHREQ


  * ```python3 sim7000.py mqtt-nossl```
      * Simple mqtt pub (no-encryption)to test.mosquitto.org
      * Use another mqtt tool (such as mosquitto_sub) to sub to the same topic and see if it is appearing.


  * ```python3 sim7000.py check-certs```
      * Check if the 3 certs (defined by variables at near the top of the script) are present on the device.
      * It will report the size in bytes if it is present, or an error if it isn't there.
      * Doesn't seem to be a list files function on the sim7000 :-(.


  * ```python3 sim7000.py certs-delete```
      * Delete the 3 certs (defined by variables at near the top of the script) from the device.


  * ```python3 sim7000.py certs-load```
    * Load the 3 certs (defined by variables at near the top of the script) from the folder (specified by variable) to the correct location on the device.


  * ```python3 sim7000.py mqtt-cacert```
    * Use the ca cert to make a encrypted connection to test.mosquitto.org. **Not working**


  * ```python3 sim7000.py mqtt-bothcerts```
    * Use the 3 certs to make a encrypted connection to test.mosquitto.org and authenticate using client cert and key.
