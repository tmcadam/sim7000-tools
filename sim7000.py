import sys
import serial
import time
import os
from datetime import datetime

CMD_LINEBREAK = b'\r\n'

PORT = "COM4"
BAUD = 115200

# Azure Iot Hub Settings
# <hubname>.azure-devices.net/{CID}/{module_id}/?api-version=2018-06-30
CID = 1 # cid: TCP/UDP Indentifier, 1-24
MQTT_URL = "mojo-bike.azure-devices.net"
CERTS_FOLDER = 'certs'
CA_NAME = 'azure-ca.crt'
CERT_NAME = ""
KEY_NAME = ""
# CA_NAME = 'mosquitto-ca.crt'
# CERT_NAME = "mosquitto.crt"
# KEY_NAME = "mosquitto.key"

def main():
    global APN, IP
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
    APN = cgcontrdp[1][1].split(",")[2]
    IP = cgcontrdp[1][1].split(",")[3]

    if "--reboot" in sys.argv:
        reboot()
    if sys.argv[1] == "ping":
        ping()
    if sys.argv[1] == "ntp":
        ntp()
    if sys.argv[1] == "http1":
        http1()
    if sys.argv[1] == "http2":
        http2()
    if sys.argv[1] == "mqtt-nossl":
        mqtt_no_ssl()
    if sys.argv[1] == "certs-check":
        certs_check()
    if sys.argv[1] == "certs-delete":
        certs_delete()
    if sys.argv[1] == "certs-load":
        certs_load()
    if sys.argv[1] == "mqtt-cacert":
        mqtt_ca_cert()
    if sys.argv[1] == "mqtt-bothcerts":
        mqtt_both_certs()

def send(data):
    with serial.Serial(PORT, BAUD, timeout=1) as ser:
        ser.write(data)

def watch_and_send(cmd, timeout=10, success=None, failure=None, echo_cmd=None):
    with serial.Serial(PORT, BAUD, timeout=1) as ser:
        ser.write(cmd.encode('utf-8') + CMD_LINEBREAK)
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
    reply = watch_and_send(cmd, timeout=timeout, success=success, failure=failure)
    print("{0} ({1:.2f}secs):".format(reply[0], reply[2]))
    print(*reply[1], sep='\n')
    print('')
    return reply

# Restart board
def reboot():
    AT('+CFUN=1,1', timeout=30, success="*PSUTTZ")

############################### PING/NTP ##################################

# Ping - works :-)
def ping():
    print("++++++++++++++++++++ PING +++++++++++++++++++++\n")
    cstt = AT('+CSTT?')
    if APN not in cstt[1][0]:
        AT('+CSTT="{}"'.format(APN))
        AT('+CIICR')
    AT('+CIFSR', success=IP)
    AT('+CIPPING="www.google.com.au"')
    return True

# Get NTP time - working :-)
def ntp():
    print("++++++++++++++++++++ NTP +++++++++++++++++++++\n")
    AT('+SAPBR=3,1,"APN","{}"'.format(APN))
    AT('+SAPBR=1,1')
    AT('+SAPBR=2,1')
    AT('+CNTP="pool.ntp.org",0,1,1')
    AT('+CNTP', timeout=3, success="+CNTP")
    AT('+SAPBR=0,1')
    return True

############################### HTTP/MQTT ##################################

# HTTP Get example - working :-)
def http1():
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
    return True

# HTTP Get example - Working :-)
def http2():
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
    return True

# MQTT (No SSL) - Working :-)
def mqtt_no_ssl():
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
    return True

############################### SSL/TLS ##################################

# Check certs on device - working :-)
def certs_check():
    print("++++++++++++++++++++ CERTS - CHECK +++++++++++++++++++++\n")
    AT('+CFSTERM') # in case a session already existed
    AT('+CFSINIT')
    AT('+CFSGFIS=3,"{}"'.format(CA_NAME))
    AT('+CFSGFIS=3,"{}"'.format(CERT_NAME))
    AT('+CFSGFIS=3,"{}"'.format(KEY_NAME))
    AT('+CFSTERM')
    return True

# Delete certs on device - working :-)
def certs_delete():
    print("++++++++++++++++++++ CERTS - DELETE +++++++++++++++++++++\n")
    AT('+CFSTERM') # in case a session already existed
    AT('+CFSINIT')
    AT('+CFSDFILE=3,"{}"'.format(CA_NAME))
    AT('+CFSDFILE=3,"{}"'.format(CERT_NAME))
    AT('+CFSDFILE=3,"{}"'.format(KEY_NAME))
    AT('+CFSTERM')
    return True

# Load a cert from a file on computer - working :-)
def certs_load():
    print("++++++++++++++++++++ CERTS - LOAD +++++++++++++++++++++\n")
    AT('+CFSTERM') # in case a session already existed
    AT('+CFSINIT')
    with open(os.path.join(CERTS_FOLDER, CA_NAME),'rb') as f:
        data = f.read()
        AT('+CFSWFILE=3,"{}",0,{},5000'.format(CA_NAME, len(data)), success="DOWNLOAD")
        send(data)
        time.sleep(3)
    if CERT_NAME == "" or KEY_NAME == "":
        return False
    with open(os.path.join(CERTS_FOLDER, CERT_NAME),'rb') as f:
        data = f.read()
        AT('+CFSWFILE=3,"{}",0,{},5000'.format(CERT_NAME, len(data)), success="DOWNLOAD")
        send(data)
        time.sleep(3)
    with open(os.path.join(CERTS_FOLDER, KEY_NAME),'rb') as f:
        data = f.read()
        AT('+CFSWFILE=3,"{}",0,{},5000'.format(KEY_NAME, len(data)), success="DOWNLOAD")
        send(data)
        time.sleep(3)
    AT('+CFSTERM')
    return True

# MQTT (SSL) - No client cert, working for Mosquitto.org :-(
def mqtt_ca_cert():
    print("++++++++++++++++++++ MQTT - CA Cert Only +++++++++++++++++++++\n")
    AT("+CNACT=1") # Open wireless connection
    AT("+CNACT?") # Check connection open and have IP


    AT('+CACID={}'.format(CID)) # set connection ID
    AT('+CSSLCFG="sslversion",{},3'.format(CID)) # ctindex=CID, sslversion=TLS 1.2
    AT('+CSSLCFG="convert",2,"{}"'.format(CA_NAME)) # convert server certificate
    AT('+CASSLCFG={},ssl,1'.format(CID)) # cid = CID, ssl flag = support ssl
    # trust all server certificates
    AT('+CAOPEN={},"{}",8883'.format(CID, MQTT_URL)) # cid = CID
    time.sleep(2)
    msg = "hi"
    # msg = "Hello Moto {}".format(datetime.now()).encode('utf-8')
    AT('+CASEND={},{}'.format(CID, len(msg)+1), success=">") # cid = CID, datalen = length of message
    send(msg.encode('utf-8'))
    time.sleep(2)
    AT('+CACLOSE={}'.format(CID)) # close connection, cid = CID
    AT('+CNACT=0') # Close wireless connection

    # AT('+SMCONF="CLIENTID", "TOMTEST01"')
    # AT('+SMCONF="KEEPTIME",60') # Set the MQTT connection time (timeout?)
    # AT('+SMCONF="CLEANSS",1')
    # AT('+SMCONF="URL","{}","8883"'.format(MQTT_URL)) # Set MQTT address
    # AT('+CSSLCFG="ctxindex", 0') # Use index 1
    # AT('+CSSLCFG="sslversion",0,3') # TLS 1.2
    # AT('+CSSLCFG="convert",2,"{}"'.format(CA_NAME))
    # time.sleep(5)
    # AT('+SMSSL=0, {}'.format(CA_NAME))
    # AT('+SMSSL?')
    # AT('+SMSTATE?') # Check MQTT connection state
    # AT('+SMCONN', timeout=60, success="OK") # Connect to MQTT
    # AT('+SMSTATE?', timeout=5) # Check MQTT connection state
    # msg = "Hello Moto {}".format(datetime.now())
    # AT('+SMPUB="test002","{}",1,1'.format(len(msg))) # Publish command
    # send(msg.encode('utf-8'))
    #AT('+SMSUB="test1234",1')
    # AT('+SMDISC') # Connect to MQTT

# MQTT (SSL) - CA and client certs, working for Mosquitto.org :-(
def mqtt_both_certs():
    if CERT_NAME == "" or KEY_NAME == "":
        print("ERROR: both certs not provided.")
        return False
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
    time.sleep(1)
    AT('+CSSLCFG="convert",1,"{}","{}"'.format(CERT_NAME, KEY_NAME)) # prepare client certificate/key pair for use
    time.sleep(1)
    AT('+SMSSL=1, {}, {}'.format(CA_NAME, CERT_NAME)) # prepare remote certificate for use
    AT('+SMSSL?')
    AT('+SMSTATE?') # Check MQTT connection state
    AT('+SMCONN', timeout=60, success="OK") # Connect to MQTT, this can take a while
    AT('+SMSTATE?', timeout=5) # Check MQTT connection state
    msg = "Hello Moto {}".format(datetime.now())
    AT('+SMPUB="test001","{}",1,1'.format(len(msg)), success=">") # Publish command
    watch_and_send(msg)
    #AT('+SMSUB="test1234",1')
    AT('+SMDISC') # Connect to MQTT

if __name__ == '__main__':
    main()
