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

client_id = "Readmeter_%d" % os.getpid()
mqttc = mosquitto.Mosquitto(client_id)

oldwatts = "0"

if DEBUG:
    logging.basicConfig(filename=LOGFILE, level=logging.INFO)
else:
    logging.basicConfig(filename=LOGFILE, level=logging.DEBUG)

logging.info('Starting mqtt-readmeter')
logging.info('INFO MODE')
logging.debug('DEBUG MODE')

def cleanup(signum, frame):
     """
     Signal handler to ensure we disconnect cleanly 
     in the event of a SIGTERM or SIGINT.
     """
     logging.info("Disconnecting from broker")
     mqttc.publish("/status/" + socket.getfqdn(), "Offline")
     mqttc.disconnect()
     logging.info("Exiting on signal %d", signum)

def connect():
    """
    Connect to the broker, define the callbacks, and subscribe
    """
    mqttc.connect(MQTT_HOST, MQTT_PORT, 60, True)

    #define the callbacks
    mqttc.on_message = on_message
    mqttc.on_connect = on_connect
    mqttc.on_disconnect = on_disconnect

    mqttc.subscribe(MQTT_TOPIC, 2)

def on_connect(result_code):
     """
     Handle connections (or failures) to the broker.
     """
     ## FIXME - needs fleshing out http://mosquitto.org/documentation/python/
     if result_code == 0:
        logging.info("Connected to broker")
        mqttc.publish("/status/" + socket.getfqdn(), "Online")
     else:
        logging.warning("Something went wrong")
        cleanup()

def on_disconnect(result_code):
     """
     Handle disconnections from the broker
     """
     if result_code == 0:
        logging.info("Clean disconnection")
     else:
        logging.info("Unexpected disconnection! Reconnecting in 5 seconds")
        logging.debug("Result code: %s", result_code)
        time.sleep(5)
        connect()
        main_loop()

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
