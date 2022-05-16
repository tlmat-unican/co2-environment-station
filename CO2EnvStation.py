#!/usr/bin/python

__author__ = "Juan Ramón Santana, Pablo Sotres, Jorge Lanza, and Luis Sánchez"
__copyright__ = "Copyright 2022, Grupo de Ingeniería Telemática, Universidad de Cantabria"
__license__ = "MIT"
__version__ = "0.1"


# Misc libraries
import time
import string
from datetime import datetime
import json
import os
import errno
import inspect

# Load the libraries to control the sensor
import board
import busio
import adafruit_scd30

# Load the libraries for MQTT communication purposes
import paho.mqtt.publish as publish
import psutil

# Load the library for the GUI
import PySimpleGUI as sg

# Logging library
import logging
from logging.handlers import RotatingFileHandler

# Import library to enable software i2c
from adafruit_extended_bus import ExtendedI2C as I2C

####################################################################

PROGRAM_NAME = inspect.stack()[0][1].split('.py', 1)[0].split('/')[-1]
PROGRAM_PATH = os.path.abspath(os.path.dirname(__file__))
if not os.path.exists(PROGRAM_PATH + '/logs/'):
    os.makedirs(PROGRAM_PATH + '/logs/')

# Initialize logging
logging_file = PROGRAM_PATH + '/logs/' + PROGRAM_NAME + '.log'
console = logging.StreamHandler()
file_handler = RotatingFileHandler(logging_file, maxBytes=10240000, backupCount=5)
formatter = logging.Formatter('%(asctime)s %(levelname)s\t| %(filename)s:%(lineno)s\t| %(message)s')
file_handler.setFormatter(formatter)
console.setFormatter(formatter)

logger = logging.getLogger('main_logger')
logger.addHandler(console)
logger.addHandler(file_handler)

logger.setLevel(logging.INFO)

# Read current parameters from JSON config file
config_file_name = PROGRAM_PATH + '/CO2EnvStation_configuration.json'

try:
    with open(config_file_name, 'r') as config_file:
        json_configuration = json.load(config_file)
except OSError:
    logger.error('Could not open/read the configuration file: ' + config_file_name)
    quit()
except Exception as e:
    logger.error('Error while reading the JSON from config file: ' + str(e))
    quit()

# We load the GUI just in case the GUI parameter is set
if json_configuration['GUI']:
    layout = [
        [
            sg.Text('Configura los parámetros necesarios para la conexión con thingspeak:')
        ],
        [
            sg.Text('Channel ID \t'),
            sg.InputText(json_configuration['thingspeak']['channel_id'], key='channel_id', size=(50, 100))
        ],
        [
            sg.Text('Host \t\t'),
            sg.InputText(json_configuration['thingspeak']['mqtt_host'], key='mqtt_host', size=(50, 100))
        ],
        [
            sg.Text('Username \t'),
            sg.InputText(json_configuration['thingspeak']['mqtt_client_id'], key='mqtt_client_id', size=(50, 100))
        ],
        [
            sg.Text('Client ID \t'),
            sg.InputText(json_configuration['thingspeak']['mqtt_username'], key='mqtt_username', size=(50, 100))
        ],
        [
            sg.Text('Password \t'),
            sg.InputText(json_configuration['thingspeak']['mqtt_password'], key='mqtt_password', size=(50, 100))
        ],
        [
            sg.Text('Transport Protocol \t'),
            sg.InputText(json_configuration['thingspeak']['transport_protocol'], key='transport_protocol',
                         size=(50, 100))
        ],
        [
            sg.Text('Port \t\t'), sg.InputText(json_configuration['thingspeak']['port'], key='port', size=(50, 100))
        ],
        [
            sg.Button('SAVE & RUN'), sg.Button('CANCEL')
        ]
    ]

    window = sg.Window('CO2 Environmental Station', layout)  

    while True:
        event, values = window.read()
        # Program is ended in case the user presses CANCEL button (or closes the program)
        if event == 'CANCEL' or event == sg.WIN_CLOSED:
            window.close()
            quit()
        # Program starts when values are set
        if event == 'SAVE & RUN':
            json_configuration['thingspeak']['channel_id'] = values['channel_id']
            json_configuration['thingspeak']['mqtt_host'] = values['mqtt_host']
            json_configuration['thingspeak']['mqtt_client_id'] = values['mqtt_client_id']
            json_configuration['thingspeak']['mqtt_username'] = values['mqtt_username']
            json_configuration['thingspeak']['mqtt_password'] = values['mqtt_password']
            json_configuration['thingspeak']['mqtt_password'] = values['mqtt_password']
            json_configuration['thingspeak']['transport_protocol'] = values['transport_protocol']
            json_configuration['thingspeak']['port'] = int(values['port'])
            try:
                with open(config_file_name, 'w') as outfile:
                    json.dump(json_configuration, outfile)
            except OSError:
                logger.error('Could not write into the configuration file: ' + config_file_name)
                window.close()
                quit()
            window.close()
            break

# Prepare the I2C bus to communicate with the SCD30 sensor
i2c = I2C(json_configuration['i2c-bus'])

devices = i2c.scan()
timeout = time.time() + json_configuration['sensor']['timeout_secs']
while len(devices) < 1:
    time.sleep(1)
    devices = i2c.scan()
    if time.time() > timeout:
        logger.error('Timeout: no devices found in the I2C port')
        quit()

devices_hex = 'I2C device addresses found: '
for device in devices:
    devices_hex += '0x' + format(device, '02x') + '; '
logger.info(devices_hex[0:-2])

# Load the adafruit scd30 library (It supports autocallibration, etc...)
scd = adafruit_scd30.SCD30(i2c)

if json_configuration['GUI']:
    # Layout for showing data
    font_type = ("Helvetica", 44)
    layout_info = [[sg.Text('CO2:', font=font_type, size=(12,2)), sg.Text(size=(12,2), font=font_type, key='-CO2-')],
          [sg.Text('Temperature:', font=font_type, size=(12,2)), sg.Text(size=(12,2), font=font_type, key='-Temperature-')],
          [sg.Text('Humidity:', font=font_type, size=(12,2)), sg.Text(size=(12,2), font=font_type, key='-Humidity-')],
          [sg.Button('EXIT', size=(12,4))]]

    window_info = sg.Window('CO2 Environmental Station', layout_info, finalize=True, resizable=True, margins=(20,20))
    window_info.maximize()

while True:
    # Wait until the sensor has measurement data to be read
    if scd.data_available:
        CO2_value = scd.CO2
        TEMP_value = scd.temperature
        HUM_value = scd.relative_humidity
        logger.info('CO2: %d PPM' % CO2_value + '; Temperature: %0.2f ºC' % TEMP_value + '; Humidity: %0.2f %% RH' % HUM_value)
        if json_configuration['thingspeak']['channel_id'] != '':
            # Send the measurements to the MQTT channel
            payload = 'field1=%d' % CO2_value + '&field2=%0.2f' % TEMP_value + '&field3=%0.2f' % HUM_value
            try:
                logger.debug('Writing Payload: ' + payload + ' to host: ' + json_configuration['thingspeak']['mqtt_host'] +
                             ' clientID: ' + json_configuration['thingspeak']['mqtt_client_id'] + ' UserID: ' +
                             json_configuration['thingspeak']['mqtt_username'] + ' PWD: ' + json_configuration['thingspeak']['mqtt_password'])
                publish.single('channels/' + json_configuration['thingspeak']['channel_id'] + '/publish', payload,
                               hostname=json_configuration['thingspeak']['mqtt_host'],
                               transport=json_configuration['thingspeak']['transport_protocol'],
                               port=json_configuration['thingspeak']['port'],
                               client_id=json_configuration['thingspeak']['mqtt_client_id'],
                               auth={'username': json_configuration['thingspeak']['mqtt_username'],
                                     'password': json_configuration['thingspeak']['mqtt_password']})
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.exception('Error while sending data to Thingspeak: ' + str(e))
        if json_configuration['GUI']:
            window_info['-CO2-'].update('%d PPM' % CO2_value)
            window_info['-Temperature-'].update('%0.2f ºC' % TEMP_value)
            window_info['-Humidity-'].update('%0.2f %%' % HUM_value)
        if json_configuration['run_once']:
            break
        else:
            # Sleep for a minimum of 'freq_secs' seconds between readings
            sleep_readings = time.time() + json_configuration['sensor']['freq_secs']
            while True:
                if time.time() > sleep_readings:
                    break
                if json_configuration['GUI']:
                    event, values = window_info.read(timeout=100) # non-blocking window read waiting 100 ms
                    if event == 'EXIT' or event == sg.WIN_CLOSED:
                        window_info.close()
                        quit()
if json_configuration['GUI']:
    window_info.close()
