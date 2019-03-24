import sys
import serial
import time
import os
from datetime import datetime

CMD_LINEBREAK = b'\r\n'

PORT = "/dev/ttyUSB0"
BAUD = 9600

# Mosquitto.org Settings
MQTT_URL="test.mosquitto.org"
CERTS_FOLDER = 'certs'
CA_NAME = 'mosquitto-ca.crt'
CERT_NAME = "mosquitto.crt"
KEY_NAME = "mosquitto.key"

def send(data):
    with serial.Serial(PORT, BAUD, timeout=1) as ser:
        ser.write(data)

def send_cmd(cmd):
    send(cmd.encode('utf-8') + CMD_LINEBREAK)

def watch(timeout=10, success=None, failure=None, echo_cmd=None):
    with serial.Serial(PORT, BAUD, timeout=1) as ser:
        t_start = time.time()
        reply = list()
        while True:
            if ser.in_waiting:
                line = ser.readline()
                echo = False
                if echo_cmd:
                    echo = line.decode('utf-8').strip().endswith(echo_cmd)
                if line != CMD_LINEBREAK and not echo:
                    line = line.decode('utf-8').strip()
                    reply.append('\t' + line)
                    if success and line.startswith(success):
                        return ("Success", reply, time.time()-t_start)
                    if failure and line.startswith(failure):
                        return ("Error", reply, time.time()-t_start)
            if (time.time()-t_start) > timeout:
                return ("Timeout", reply, time.time()-t_start)
            time.sleep(0.02)

def AT(cmd="", timeout=10, success="OK", failure="+CME ERROR"):
    cmd = 'AT' + cmd
    print("----------- ", cmd, " -----------")
    send_cmd(cmd)
    reply = watch(echo_cmd=cmd, timeout=timeout, success=success, failure=failure)
    print("{0} ({1:.2f}secs):".format(reply[0], reply[2]))
    print(*reply[1], sep='\n')
    print('')
    return reply

# Restart board
if "--reboot" in sys.argv:
    AT('+CFUN=1,1', timeout=30, success="*PSUTTZ")

# AT('+CMNB=3') # Set preference for nb-iot (doesn't work with nb-iot)
AT() # Check modem is responding
AT("+CMEE=2") # Set debug level
# Hardware Info
AT("+CPIN?") # Check sim card is present and active
AT("+CGMM") # Check module name
AT("+CGMR") # Firmware version
AT('+GSN') # Get IMEI number
AT('+CCLK?') # Get system time
# Signal info
AT("+COPS?") # Check opertaor info
AT("+CSQ") # Get signal strength
AT('+CPSI?') # Get more detailed signal info
AT('+CBAND?') # Get band
# GPRS info
AT("+CGREG?") # Get network registration status
AT("+CGACT?") # Show PDP context state
AT('+CGPADDR') # Show PDP address
cgcontrdp = AT("+CGCONTRDP") # Get APN and IP address
# Check nb-iot Status
AT('+CGNAPN')

APN = cgcontrdp[1][0].split(",")[2]
IP = cgcontrdp[1][0].split(",")[3]

############################### PING/NTP ##################################

# Ping - works :-)
if sys.argv[1] == "ping":
    print("++++++++++++++++++++ PING +++++++++++++++++++++\n")
    cstt = AT('+CSTT?')
    if APN not in cstt[1][0]:
        AT('+CSTT="{}"'.format(APN))
        AT('+CIICR')
    AT('+CIFSR', success=IP)
    AT('+CIPPING="www.google.com.au"')

# Get NTP time - working :-)
if sys.argv[1] == "ntp":
    print("++++++++++++++++++++ NTP +++++++++++++++++++++\n")
    AT('+SAPBR=3,1,"APN","{}"'.format(APN))
    AT('+SAPBR=1,1')
    AT('+SAPBR=2,1')
    AT('+CNTP="pool.ntp.org",0,1,1')
    AT('+CNTP', timeout=3, success="+CNTP")
    AT('+SAPBR=0,1')

############################### HTTP/MQTT ##################################

# HTTP Get example - working :-)
if sys.argv[1] == "http1":
    print("++++++++++++++++++++ HTTP1 +++++++++++++++++++++\n")
    AT('+SAPBR=3,1,"APN","{}"'.format(APN))
    AT('+SAPBR=1,1')
    AT('+SAPBR=2,1')
    AT('+HTTPINIT')
    AT('+HTTPPARA="CID",1')
    AT('+HTTPPARA="URL","http://minimi.ukfit.webfactional.com"')
    AT('+HTTPACTION=0', timeout=30, success="+HTTPACTION: 0,200")
    AT('+HTTPREAD')
    AT('+HTTPTERM')
    AT('+SAPBR=0,1')

# HTTP Get example - Working :-)
if sys.argv[1] == "http2":
    print("++++++++++++++++++++ HTTP2 +++++++++++++++++++++\n")
    AT('+CNACT=1')
    AT("+CNACT?")
    AT('+SHCONF="URL","http://minimi.ukfit.webfactional.com"')
    AT('+SHCONF="BODYLEN",350')
    AT('+SHCONF="HEADERLEN",350')
    AT('+SHCONN',timeout=30, success="OK")
    AT('+SHSTATE?')
    AT('+SHREQ="http://minimi.ukfit.webfactional.com",1', timeout=30, success="+SHREQ:")
    AT('+SHREAD=0,1199', timeout=30, success="</html>")
    AT('+SHDISC')

# MQTT (No SSL) - Working :-)
if sys.argv[1] == "mqtt-nossl":
    print("++++++++++++++++++++ MQTT - NO SSL +++++++++++++++++++++\n")
    AT("+CNACT=1") # Open wireless connection
    AT("+CNACT?") # Check connection open and have IP
    AT('+SMCONF="CLIENTID",1233')
    AT('+SMCONF="KEEPTIME",60') # Set the MQTT connection time (timeout?)
    AT('+SMCONF="CLEANSS",1')
    AT('+SMCONF="URL","{}","1883"'.format(MQTT_URL)) # Set MQTT address
    smstate = AT('+SMSTATE?') # Check MQTT connection state
    if smstate[1][0].split(":")[1].strip() == "0":
        AT('+SMCONN', timeout=30) # Connect to MQTT
    msg = "Hello Moto {}".format(datetime.now())
    AT('+SMPUB="test001","{}",1,1'.format(len(msg)), timeout=30, success=">") # Publish command
    send(msg.encode('utf-8'))
    watch(timeout=10)
    #AT('+SMSUB="test1234",1')
    AT('+SMDISC') # Disconnect MQTT
    AT("+CNACT=0") # Close wireless connection

############################### SSL/TLS ##################################

# Check certs on device - working :-)
if sys.argv[1] == "certs-check":
    print("++++++++++++++++++++ CERTS - CHECK +++++++++++++++++++++\n")
    AT('+CFSINIT')
    AT('+CFSGFIS=3,"{}"'.format(CA_NAME))
    AT('+CFSGFIS=3,"{}"'.format(CERT_NAME))
    AT('+CFSGFIS=3,"{}"'.format(KEY_NAME))
    AT('+CFSTERM')

# Delete certs on device - working :-)
if sys.argv[1] == "certs-delete":
    print("++++++++++++++++++++ CERTS - DELETE +++++++++++++++++++++\n")
    AT('+CFSINIT')
    AT('+CFSDFILE=3,"{}"'.format(CA_NAME))
    AT('+CFSDFILE=3,"{}"'.format(CERT_NAME))
    AT('+CFSDFILE=3,"{}"'.format(KEY_NAME))
    AT('+CFSTERM')

# Load a cert from a file on computer - working :-)
if sys.argv[1] == "certs-load":
    print("++++++++++++++++++++ CERTS - LOAD +++++++++++++++++++++\n")
    AT('+CFSINIT')
    with open(os.path.join(CERTS_FOLDER, CA_NAME),'rb') as f:
        data = f.read()
        AT('+CFSWFILE=3,"{}",0,{},5000'.format(CA_NAME, len(data)), success="DOWNLOAD")
        send(data)
    with open(os.path.join(CERTS_FOLDER, CERT_NAME),'rb') as f:
        data = f.read()
        AT('+CFSWFILE=3,"{}",0,{},5000'.format(CERT_NAME, len(data)), success="DOWNLOAD")
        send(data)
    with open(os.path.join(CERTS_FOLDER, KEY_NAME),'rb') as f:
        data = f.read()
        AT('+CFSWFILE=3,"{}",0,{},5000'.format(KEY_NAME, len(data)), success="DOWNLOAD")
        send(data)
    AT('+CFSTERM')

# MQTT (SSL) - No client cert, working for Mosquitto.org :-(
if sys.argv[1] == "mqtt-cacert":
    print("++++++++++++++++++++ MQTT - CA Cert Only +++++++++++++++++++++\n")
    AT("+CNACT=1") # Open wireless connection
    AT("+CNACT?") # Check connection open and have IP
    AT('+SMCONF="CLIENTID", "TOMTEST01"')
    AT('+SMCONF="KEEPTIME",60') # Set the MQTT connection time (timeout?)
    AT('+SMCONF="CLEANSS",1')
    AT('+SMCONF="URL","{}","8883"'.format(MQTT_URL)) # Set MQTT address
    AT('+CSSLCFG="ctxindex", 0') # Use index 1
    AT('+CSSLCFG="sslversion",0,3') # TLS 1.2
    AT('+CSSLCFG="convert",2,"{}"'.format(CA_NAME))
    AT('+SMSSL=0, {}'.format(CA_NAME))
    AT('+SMSSL?')
    AT('+SMSTATE?') # Check MQTT connection state
    AT('+SMCONN', timeout=60, success="OK") # Connect to MQTT
    AT('+SMSTATE?', timeout=5) # Check MQTT connection state
    msg = "Hello Moto {}".format(datetime.now())
    AT('+SMPUB="test002","{}",1,1'.format(len(msg))) # Publish command
    send(msg.encode('utf-8'))
    #AT('+SMSUB="test1234",1')
    AT('+SMDISC') # Connect to MQTT

# MQTT (SSL) - CA and client certs, working for Mosquitto.org :-(
if sys.argv[1] == "mqtt-bothcerts":
    print("++++++++++++++++++++ MQTT - CA and Client Cert +++++++++++++++++++++\n")
    AT("+CNACT=1") # Open wireless connection
    AT("+CNACT?") # Check connection open and have IP
    AT('+SMCONF="CLIENTID", "TOMTEST01"')
    AT('+SMCONF="KEEPTIME",60') # Set the MQTT connection time (timeout?)
    AT('+SMCONF="CLEANSS",1')
    AT('+SMCONF="URL","{}","8884"'.format(MQTT_URL)) # Set MQTT address
    AT('+CSSLCFG="ctxindex", 0') # Use index 1
    AT('+CSSLCFG="sslversion",0,3') # TLS 1.2
    AT('+CSSLCFG="convert",2,"{}"'.format(CA_NAME))
    AT('+CSSLCFG="convert",1,"{}","{}"'.format(CERT_NAME, KEY_NAME))
    AT('+SMSSL=1, {}, {}'.format(CA_NAME, CERT_NAME))
    AT('+SMSSL?')
    AT('+SMSTATE?') # Check MQTT connection state
    AT('+SMCONN', timeout=60, success="OK") # Connect to MQTT, this can take a while
    AT('+SMSTATE?', timeout=5) # Check MQTT connection state
    msg = "Hello Moto {}".format(datetime.now())
    AT('+SMPUB="test001","{}",1,1'.format(len(msg)), success=">") # Publish command
    send(msg.encode('utf-8'))
    watch(timeout=10)
    #AT('+SMSUB="test1234",1')
    AT('+SMDISC') # Connect to MQTT
