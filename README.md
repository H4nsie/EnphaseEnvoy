# EnphaseEnvoy
Enphase Envoy with LAN interface - **with individual micro inverters** (Domoticz plugin)


**THIS IS THE DEVELOPMENT BRANCH. - There could be [issues](https://github.com/H4nsie/EnphaseEnvoy/issues) with this version.**

Supports Enphase Envoy v5 and v7 firmware.
Tested with Domoticz 2022.1

Monitor production (and log over time) each individual solar panel.

This Domoticz plugin reads the Enphase Envoy interface and the individual micro inverters at the solar panels. The individual panels are polled and their power generated is updated in Domoticz. If new micro invertes (per solar panel) are added to your system, they automaticaly are added as new 'kWh' devices in your Domoticz.

![alt text](https://github.com/H4nsie/EnphaseEnvoy/blob/main/images/sample_screenshot.png?raw=true)


Installation and setup
----------------------
Note: User credentials for the Envoy are read from the internal xml file

Follow the Domoticz guide on [Using Python Plugins](https://www.domoticz.com/wiki/Using_Python_plugins). Check limitations on the bottom of the page.

Login to a shell, go to the domoticz plugin directory and clone this repository:
```bash
cd domoticz/plugins
git clone https://github.com/H4nsie/EnphaseEnvoy.git
```

Restart Domoticz server, you can try one of these commands (on Linux):
```bash
sudo systemctl restart domoticz.service
or
sudo service domoticz.sh restart
```

Open the Domoticz interface and go to: **Setup** > **Hardware**. You can add new Hardware add the bottom, in the list of hardware types choose for: **Enphase Envoy with micro inverters**.

Fill out the parameters shown in the form. 

**NOTE** When your Envoy is on D7 firmware, you must enter the session-id obtained at Enphase.

Updating
--------
Login to a shell, go to the plugin directory inside the domoticz plugin directory and execute git pull:
```bash
cd domoticz/plugins/EnphaseEnvoy
git pull
```
