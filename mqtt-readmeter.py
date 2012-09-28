#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

__author__ = "Kyle Gordon"
__copyright__ = "Copyright (C) Kyle Gordon"

import mosquitto
import os
import logging
import signal
import socket

import mosquitto
import ConfigParser

# Read the config file
config = ConfigParser.RawConfigParser()
config.read("/etc/mqtt-republisher/mqtt-republisher.cfg")

# Use ConfigParser to pick out the settings
DEBUG = config.getboolean("global", "debug")
LOGFILE = config.get("global", "logfile")
MAPFILE = config.get("global", "mapfile")
MQTT_HOST = config.get("global", "mqtt_host")
MQTT_PORT = config.get("global", "mqtt_host")

MQTT_TOPIC="/raw/" + socket.getfqdn() + config.get("global", "MQTT_SUBTOPIC")

mypid = os.getpid()
client_uniq = "Readmeter_"+str(mypid)
mqttc = mosquitto.Mosquitto(client_uniq)
oldwatts = "0"

LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL}

if DEBUG == 0: logging.basicConfig(filename=LOGFILE,level=logging.INFO)
if DEBUG == 1: logging.basicConfig(filename=LOGFILE,level=logging.DEBUG)

logging.info('Starting mqtt-readmeter')
logging.info('INFO MODE')
logging.debug('DEBUG MODE')

def cleanup(signum, frame):
    logging.info("Disconnecting from broker")
    mqttc.disconnect()
    logging.info("Exiting on signal " + str(signum))

#define what happens after connection
def on_connect(rc):
	logging.info("Connected to broker")

#On recipt of a message print it
def on_message(msg):
	logging.debug("Received: " + msg.topic)

# Use the signal module to handle signals
signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

#connect to broker
mqttc.connect(MQTT_HOST, MQTT_PORT, 60, True)

#define the callbacks
mqttc.on_message = on_message
mqttc.on_connect = on_connect

mqttc.subscribe(MQTT_TOPIC, 2)

#remain connected and publish
while mqttc.loop() == 0:
	logging.debug("Looping")
	watts = open('/var/lib/meter', 'r').read()
	if watts != oldwatts:
		mqttc.publish(MQTT_TOPIC, watts)
		oldwatts = watts
		pass
