# Enphase Envoy with LAN interface - with individual inverters
#
# Author: Hans van der Heijden
#
# Version
# 1.0.0 - initial release

"""
<plugin key="Envoy2" name="Enphase Envoy with LAN interface - with individual inverters" author="Hans van der Heijden" version="1.0.0" wikilink="" externallink="https://github.com/H4nsie/EnphaseEnvoy.git">
    <params>
        <param field="Address" label="IP" width="250px" required="true"/>
        <param field="Username" label="Username" width="250px" required="true"/>
        <param field="Password" label="Password" width="250px" required="true"/>
        <param field="Mode5" label="Log level" width="100px">
            <options>
                <option label="Normal" value="Normal" default="true" />
                <option label="Debug" value="Debug"/>
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz
import requests
import datetime
import json
from requests.auth import HTTPBasicAuth, HTTPDigestAuth


class BasePlugin:
    enabled = False
    def __init__(self):
        #self.var = 123
        self.freq = 2 #multiplier for Domoticz.Heartbeat (no need to update frequent as Envoy itself is updated only every 5 minutes.
        self.running = True # be able to disable this pugin until restart, on connection error.
        return


    def onStart(self):

        if Parameters["Mode5"] == "Debug":
            Domoticz.Debugging(2)
            DumpConfigToLog()
        else:
            Domoticz.Debugging(0)
        Domoticz.Debug("onStart called")   
        
        Domoticz.Log("Plugin has " + str(len(Devices)) + " devices associated with it.")

		# set Heartbeat and freq        
        Domoticz.Heartbeat(10)    
        self.beatcount = self.freq*2
        Domoticz.Debug("beatcount :" + str(self.beatcount))
        self.heartbeat = self.beatcount

		# create P1 usage device if not yet created
        if (len(Devices) == 0):
            Domoticz.Device(Name="Production", Unit=1, Type=250, Subtype=1, Used=1, DeviceID='EnphaseEnvoyUsage').Create()
            UpdateDevice(Unit=1, nValue=0, sValue="0;0;0;0;0", TimedOut=0)
            Domoticz.Debug("Device EnphaseEnvoyUsage created")
            

        # get serialnumber and test LAN connection to Envoy
        try:
            jsonPCU = requests.get('http://' + Parameters["Address"] + '/inventory.json')
            envoyserial=jsonPCU.json()[0]['devices'][0]['serial_num']
            Domoticz.Log("Connection made with Enphase envoy serial: "+envoyserial)
        except Exception as err:
            Domoticz.Debug("ConnectionException")
            Domoticz.Error("Error connecting to Enphase Envoy on {} error: {}".format(Parameters["Address"], err) )
            self.running = False
            return
        






    def getData(self):
        
        # GET TOTAL PRODUCTION (NOW AND EVER LIFETIME) (no credentials needed)
        try: 
            jsonproduction = requests.get('http://' + Parameters["Address"] + '/production.json')
        except Exception as err:
            Domoticz.Debug("ConnectionException")
            Domoticz.Error("Error connecting to Enphase Envoy on {} error: {}".format(Parameters["Address"], err) )
            return	
            
        if (jsonproduction.status_code == 200):
            production=jsonproduction.json()['production'][0]
            #Domoticz.Log( str(production['whLifetime']))
            #Domoticz.Log( str(production['wNow']))
            #Domoticz.Log( str(production['readingTime']))  

            #sValue="USAGE1;USAGE2;RETURN1;RETURN2;CONS;PROD;DATE"
            sValue= str(production['whLifetime']) + ";0;0;0;" + str(production['wNow'])+";0" 
            Domoticz.Log('Total production read {} Watts, counter is {}'.format(production['wNow'], production['whLifetime']))
            UpdateDevice(Unit=1, nValue=0, sValue=sValue, TimedOut=0)
        else:
            Domoticz.Error( 'Could not connect to Envoy on {}, please check connection'.format(Parameters["Address"]))
        
        # GET INVERTER WATTS (credentials needed)
        jsoninverters = requests.get('http://' + Parameters["Address"] + '/api/v1/production/inverters/' , auth=HTTPDigestAuth(Parameters["Username"], Parameters["Password"]))

        if (jsoninverters.status_code == 200):
            Domoticz.Debug("Envoy HTTP concection report status code: {}".format(str(jsoninverters.status_code)))
            #numberInverters = len(jsoninverters.json())
            inverters=jsoninverters.json()
            for inverter in inverters:
                Domoticz.Debug( 'Inverter: ' + inverter['serialNumber'] + ' Lastreport: ' + str(inverter['lastReportDate'])  + ' Reports: ' + str(inverter['lastReportWatts']) )
                
                # Check if device with given deviceid=serial and devicetype is already present, otherwise create it
                DeviceFound = False
                for Device in Devices:
                    if Devices[Device].DeviceID == str(inverter['serialNumber']) and Devices[Device].Type == 248:
                        DeviceFound = True
                        #update the Watts for this SN
                        Domoticz.Log("Inverter {} read {} Watts".format(inverter['serialNumber'], inverter['lastReportWatts']))
                        UpdateDevice(Unit=Devices[Device].Unit, nValue=0, sValue=inverter['lastReportWatts'], TimedOut=0)
                        
				# create new device for this SN
                if not DeviceFound:
                    iUnit=len(Devices)+1
                    Domoticz.Device(Unit=iUnit, DeviceID=str(inverter['serialNumber']), Name="Solar "+str(inverter['serialNumber']), Type=248, Subtype=1, Used=1).Create()
                    UpdateDevice(Unit=iUnit, nValue=0, sValue=inverter['lastReportWatts'], TimedOut=0)
                    Domoticz.Log( 'Device Solar {} created'.format(inverter['serialNumber']))
              
        else:
            Domoticz.Error( 'Could not connect to Envoy on {}, please check connection and credentials'.format(Parameters["Address"]))
           
 
                    

    def onStop(self):
        Domoticz.Debug("onStop called")

    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug("onConnect called")
        Domoticz.Debug("Status:" + str(Status))

    def onMessage(self, Connection, Data):
        Domoticz.Debug("onMessage called")
        Domoticz.Debug("Data:" + str(Data))

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Debug("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Debug("onDisconnect called")

    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat called")
        if self.running == False:
            self.freq = 10 # increase interval while repeating error message:
            Domoticz.Error("Plugin not running. Please check parameters and LAN connection and restart plugin")
            return
        
        if self.heartbeat < self.beatcount:
            self.heartbeat = self.heartbeat + 1
            Domoticz.Debug("hearbeat:" + str(self.heartbeat))
        else:
            self.getData()
            Domoticz.Debug("Do update from Envoy")
            self.heartbeat = 0
            
        Domoticz.Debug("End heartbeat")



global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

def UpdateDevice(Unit, nValue, sValue, TimedOut=0, AlwaysUpdate=False):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it 
    if (Unit in Devices):
        if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue) or (Devices[Unit].TimedOut != TimedOut):
            Devices[Unit].Update(nValue=nValue, sValue=str(sValue), TimedOut=TimedOut)
            Domoticz.Debug("Update device: {} {} {} ".format(str(nValue), str(sValue), str(Devices[Unit].Name)))
    return




# Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    return