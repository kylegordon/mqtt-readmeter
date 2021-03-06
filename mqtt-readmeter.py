#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

__author__ = "Kyle Gordon"
__copyright__ = "Copyright (C) Kyle Gordon"

import mosquitto
import os
import logging
import signal
import socket
import time
import sys

import mosquitto
import ConfigParser

# Read the config file
config = ConfigParser.RawConfigParser()
config.read("/etc/mqtt-readmeter/mqtt-readmeter.cfg")

# Use ConfigParser to pick out the settings
DEBUG = config.getboolean("global", "debug")
LOGFILE = config.get("global", "logfile")
METERSOURCE = config.get("global", "metersource")
MQTT_HOST = config.get("global", "mqtt_host")
MQTT_PORT = config.getint("global", "mqtt_port")

MQTT_TOPIC="/raw/" + socket.getfqdn() + config.get("global", "MQTT_SUBTOPIC")

client_id = "Readmeter_%d" % os.getpid()
mqttc = mosquitto.Mosquitto(client_id)

LOGFORMAT = '%(asctime)-15s %(message)s'

if DEBUG:
    logging.basicConfig(filename=LOGFILE, level=logging.DEBUG, format=LOGFORMAT)
else:
    logging.basicConfig(filename=LOGFILE, level=logging.INFO, format=LOGFORMAT)

logging.info('Starting mqtt-readmeter')
logging.info('INFO MODE')
logging.debug('DEBUG MODE')

def cleanup(signum, frame):
     """
     Signal handler to ensure we disconnect cleanly 
     in the event of a SIGTERM or SIGINT.
     """
     logging.info("Disconnecting from broker")
     # FIXME - This status topis too far up the hierarchy.
     mqttc.publish("/status/" + socket.getfqdn(), "Offline")
     mqttc.disconnect()
     logging.info("Exiting on signal %d", signum)
     sys.exit(signum)

def connect():
    """
    Connect to the broker, define the callbacks, and subscribe
    """
    result = mqttc.connect(MQTT_HOST, MQTT_PORT, 60, True)
    if result != 0:
        logging.info("Connection failed with error code %s. Retrying", result)
        time.sleep(10)
        connect()

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

def on_message(msg):
    """
    What to do once we receive a message
    """
    logging.debug("Received: " + msg.topic)
    if msg.topic == "/status" and msg.payload == "status?":
        mqttc.publish("/status/" + socket.getfqdn(), "Online")

def main_loop():
    """
    The main loop in which we stay connected to the broker
    """
    oldwatts = ""
    while mqttc.loop() == 0:
        logging.debug("Looping")
        watts = open(METERSOURCE, 'r').read()
	watts = watts.rstrip('\n')
        if watts != oldwatts:
            mqttc.publish(MQTT_TOPIC, watts)
            oldwatts = watts

# Use the signal module to handle signals
signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

# Connect to the broker and enter the main loop
connect()
main_loop()
