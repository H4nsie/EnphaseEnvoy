# Enphase Enphase Envoy LAN micro inverters
#
# Authors: H4nsie, claskfosmic, 0crap
#
# Version
# 1.0.6 - [H4nsie] Added `password="true"` to the parameter field, so the password is hidden in the GUI.
# 1.0.6 - [claskfosmic] added login using Enlighten username and password in order to get the required sessionId automatically, in order to login on the local Envoy/IQ Gateway.
# 1.0.5 - added auto distinction between Envoy firmware D5 and D7 - 19 oct 2022
# 1.0.4 - removed username / pass for Envoy parameters, as specs Enphase say that this is always 'evoy' + serial read from info.xml - 18 oct 2022
# 1.0.3 - now using 243 as return devices - 15 oct 2022
# 1.0.2 - minor corrections - 9 oct 2022
# 1.0.0 - initial release - oct 2022

# TODO
# - implement and try "/auth/check_jwt" for activate inverters communicate every minute

"""
<plugin key="EnphaseEnvoy" name="Enphase Envoy - with micro inverters" author="H4nsie" version="1.0.6" wikilink="http://www.domoticz.com/" externallink="https://github.com/H4nsie/EnphaseEnvoy">
    <description>
        <h2>Enphase Envoy - with micro inverters</h2><br/>
        <ul style="list-style-type:square">
            <li>Enlighten's username and password are only needed at Envoy's firmware 7.</li>
        </ul>
    </description>
    <params>
        <param field="Address" label="IP" width="250px" required="true"/>
        <param field="Username" label="Username" width="250px" />
        <param field="Password" label="Password" width="250px" password="true" />
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
        self.freq = 2 #multiplier for Domoticz.Heartbeat (no need to update frequent as Envoy itself is updated only every 5 minutes.)
        self.running = True # be able to disable this pugin until restart, on connection error.
        self.sessionId = ''
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
            Domoticz.Device(Name="total", Unit=1, Type=250, Subtype=1, Used=1, DeviceID='EnphaseEnvoyUsage').Create()
            UpdateDevice(Unit=1, nValue=0, sValue="0;0;0;0;0", TimedOut=0)
            Domoticz.Debug("Device EnphaseEnvoyUsage created")

        # get serialnumber and version firmware and test LAN connection to Envoy
        try:
            systemXML = requests.get('http://' + Parameters["Address"] + '/info.xml', verify=False)
            global envoyserial
            if "<sn>" in systemXML.text:
                envoyserial= systemXML.text.split("<sn>")[1].split("</sn>")[0]
            else:
                envoyserial = 'not found'
            global envoyfirmware
            if "<software>" in systemXML.text:
                envoyfirmware= systemXML.text.split("<software>")[1].split("</software>")[0][:2] #note [:2] first 2 chars
            else:
                envoyfirmware = 'not found'            

            Domoticz.Log("Connection made with Enphase envoy serial: "+envoyserial)
            Domoticz.Log("Enphase envoy firmware is: "+envoyfirmware)
        
        except Exception as err:
            Domoticz.Debug("ConnectionException")
            Domoticz.Error("Error connecting to Enphase Envoy on {} error: {}. Please restart plugin.".format(Parameters["Address"], err) )
            self.running = False # stop the heartbeat
            return
            
        if (not envoyfirmware =="D5" and not envoyfirmware=="D7"):
            Domoticz.Error("Error this firmware ({}) of Envoy is not supported by this plugin.".format(envoyfirmware))
            self.running = False # stop the heartbeat
            return

    def getData(self):

        if envoyfirmware == 'D7' and self.sessionId == '':

            # Go login with Enphase Enlighten Account
            #
            data = {
                'user[email]': Parameters["Username"],
                'user[password]': Parameters["Password"]
            }
            try:
                response = requests.post('https://enlighten.enphaseenergy.com/login/login.json?', data=data)
            except Exception as err:
                Domoticz.Debug("ConnectionException")
                Domoticz.Error("Error connecting to Enphase Enlighten on enlighten.enphaseenergy.com - Error: {}".format(err) )
                return

            response_data = json.loads(response.text)
            Domoticz.Debug("Got sessionId '" + response_data['session_id'] + "' from Enphase Enlighten.")

            # Get authToken
            #
            data = {
                'session_id': response_data['session_id'],
                'serial_num': envoyserial,
                'username': Parameters["Username"]
            }

            try:
                response = requests.post('https://entrez.enphaseenergy.com/tokens', json=data)
            except Exception as err:
                Domoticz.Debug("ConnectionException")
                Domoticz.Error("Error connecting to Enphase Energy on entrez.enphaseenergy.com - Error: {}".format(err) )
                return

            authToken = response.text
            Domoticz.Debug("Got authToken '" + authToken + "' from Enphase Energy.")

            if authToken != "":

                # Validate token on IQ Gateway
                #
                headers = {
                    "Authorization": "Bearer " + authToken
                }
                response = requests.get('https://' + Parameters["Address"] + '/auth/check_jwt', headers=headers, verify=False)

                # Check response, a valid response will look like: <!DOCTYPE html><h2>Valid token.</h2>
                #
                if "Valid token." in response.text:

                    # Extract the sessionId from the cookies.
                    #
                    self.sessionId = response.cookies['sessionId']

            if self.sessionId != '':
                Domoticz.Debug("Got sessionId '" + self.sessionId + "' from {}".format(Parameters["Address"]) )
            else:
                Domoticz.Error("Error getting sessionId and/or authToken using Enphase Enlighten username and password.")
        
        # GET TOTAL PRODUCTION (NOW AND EVER LIFETIME) (no credentials needed)
        if (envoyfirmware == "D5"):
            try: 
                jsonproduction = requests.get('http://' + Parameters["Address"] + '/production.json', verify=False)
            except Exception as err:
                Domoticz.Debug("ConnectionException")
                Domoticz.Error("Error connecting to Enphase Envoy on {} error: {}".format(Parameters["Address"], err) )
                return  

        if (envoyfirmware == "D7"):
            try:
                jsonproduction = requests.get('https://' + Parameters["Address"] + '/production.json', cookies=dict(sessionid=self.sessionId), verify=False)
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
        
        # GET INVERTER PRODUCTION (credentials or TokenID needed, depending on envoyfirmware)
        if (envoyfirmware == "D5"):
            try:
                jsoninverters = requests.get('http://' + Parameters["Address"] + '/api/v1/production/inverters/' , auth=HTTPDigestAuth('envoy', envoyserial[-6:]))
                Domoticz.Debug('Using credentials {} : {}'.format('envoy', envoyserial[-6:]))
            except Exception as err:
                Domoticz.Error("Error connecting to Enphase Envoy on {} error: {}".format(Parameters["Address"], err) )
                return

        if (envoyfirmware == "D7"):
            try:
                jsoninverters = requests.get('http://' + Parameters["Address"] + '/api/v1/production/inverters/' ,cookies=dict(sessionid=self.sessionId), verify=False)
            except Exception as err:
                Domoticz.Error("Error connecting to Enphase Envoy on {} error: {}".format(Parameters["Address"], err) )
                return
        
        if (jsoninverters.status_code == 200):
            Domoticz.Debug("Envoy HTTP concection report status code: {}".format(str(jsoninverters.status_code)))
            #numberInverters = len(jsoninverters.json())
            inverters=jsoninverters.json()
            for inverter in inverters:
                Domoticz.Debug( 'Inverter: ' + inverter['serialNumber'] + ' Lastreport: ' + str(inverter['lastReportDate'])  + ' Reports: ' + str(inverter['lastReportWatts']) )
                
                # Check if device with given deviceid=serial and devicetype is already present and update value, otherwise create it
                DeviceFound = False
                for Device in Devices:
                    if Devices[Device].DeviceID == str(inverter['serialNumber']) and Devices[Device].Type == 243:
                        #Domoticz.Log(dir(Devices[Device]))
                        #for attr in dir(Devices[Device]):
                            #Domoticz.Log(str(Devices[Device].DeviceID)+"Devices[Device].%s = %r" % (attr, getattr(Devices[Device], attr)))
                        DeviceFound = True
                        #update the Watts for this SN
                        Domoticz.Log("Inverter {} reads {} Watts".format(inverter['serialNumber'], inverter['lastReportWatts']))
                        UpdateDevice(Unit=Devices[Device].Unit, nValue=0, sValue=str(inverter['lastReportWatts'])+";0", TimedOut=0)
                        
                # CREATE new device for this SN
                if not DeviceFound:
                    iUnit=len(Devices)+1
                    Domoticz.Device(Unit=iUnit, DeviceID=str(inverter['serialNumber']), Name="panel "+str(inverter['serialNumber']), TypeName='kWh', Subtype=29, Used=1, Switchtype=4, Options={'EnergyMeterMode':'1'}).Create()
                    UpdateDevice(Unit=iUnit, nValue=0, sValue=str(inverter['lastReportWatts'])+";0", TimedOut=0)
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
