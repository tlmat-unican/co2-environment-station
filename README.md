# CO2 Environment Station

This repository includes the software to make a CO2 Environment Station using a Raspberry Pi and a Sensirion SCD30 sensor. Besides, it also provides the means to send this data to the thingspeak.com platform, enabling remote access.

Raspberry Pi and Sensirion SCD30 connection is made through 4 pins: SDA and SCL for the I2C communication, the VDD (3.3V) and Ground.

The connection with Thingspeak is carried out through te MQTT interface it provides through websockets.

![CO2 Environment Station](img/co2_env_station.jpg?raw=true "CO2 Environment Station")

## Requirements
This script relies on several Python 3 libraries that can be installed using the following command (if pip3 is installed in the system):

    pip install adafruit-circuitpython-scd30 psutil paho-mqtt PySimpleGUI adafruit-extended-bus

All the tests have been carried out using the Raspbian OS, altough other using OS should be also ok.

Besides, although the pinout to which the SCD30 is connected can use the built-in I2C hardware interface, in this software we have enable it through software, as under our tests, it stopped working after some time. In this sense, the following updates shall be included in the /boot/config.txt file:

    dtparam=i2s=off # uncomment if existing and put it to off
    dtoverlay=vc4-kms-v3d,noaudio  # add noaudio -> with this we avoid hdmi audio errors
    dtoverlay=i2c-gpio,i2c_gpio_delay_us=20,i2c_gpio_sda=2,i2c_gpio_scl=3,bus=6 # add it to the end of the file

## How to use
The software is composed of two files: a python script which handles the communication with the sensors and upload the data to the thingspeak servers, and a JSON formatted configuration file. Additionally, an account on the Thingspeak.com platform is required to use this service.

### Thingspeak.com

So as to upload the information to the thingspeak.com servers, it is needed to create an account in it, and follow the next steps:

- Create a channel (either public or private, depending if you want to share it) and get the Channel ID parameter.
- Create the widgets on the channel you might want to use (e.g. time series graphs). Consider that this CO2 Environmental Station measures CO2 in ppm, temperature in Celsius and the relative humidity.
- Add a device and assign it to the channel created. Gather the Username, Client ID and Password parameters.

In the program, the MQTT host, the transport protocol and the port is set by default, although it can be changed.

### JSON configuration

There are two ways of configuring this file, either using the GUI or directly configuring the JSON file. In both cases, the parameters written above will be needed in case of the thingspeak platform is used.

![CO2 Environment Station configuration parameters](img/configuration_gui.png?raw=true "CO2 Environment Station configuration parameters")

Apart from the parameters related to Thingspeak, the following parameters are also needed:

- timeout_secs: timeout in case the sensor does not respond to the I2C communications.
- freq_secs: the period between measurement reads.

In case you want to simply send the measurements to the thingspeak server, you can deactivate the GUI by setting the "GUI" parameter to 0 and the run_once to "1". This way, we can call it at any pace from the system CRON service, adding the following line to the crontab:

    */1 * * * * /usr/bin/python3 /path/to/file/CO2EnvStation.py > /dev/null 2>&1

### Python script

Simply run the file:

    /user/bin/python3 /path/to/file/CO2EnvStation.py

If the GUI parameter is set, the program will remain open in full screen mode to show the sensor reads.

![CO2 Environment Station GUI](img/data_gui.png?raw=true "CO2 Environment Station GUI")
