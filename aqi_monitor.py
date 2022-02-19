#!/usr/bin/env python3

"""
AQI Monitor
- Read PM2.5 and PM10 metrics from an SDS011 PM sensor via USB
- Computes AQI and uploads metrics to Adafruit.IO
- Optionallys ends SMS via Twilio when AQI is unhealthy
- Runs as daemon or in interactive mode
"""

import getopt
import os
import sys
import syslog
import time
import serial
import daemon
import twilio.rest

# https://adafruit-io-python-client.readthedocs.io/en/latest/quickstart.html#basic-client-usage
from Adafruit_IO import AdafruitIOError, Client

# https://pypi.org/project/python-aqi/
import aqi

# https://github.com/ikalchev/py-sds011
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))+'/py-sds011')
from sds011 import SDS011

import aqi_monitor_config

def usage():
    """ Display AQI Monitor usage information """
    script_name = os.path.basename(__file__)
    print(
        '''Usage: {} [options]
 -d, --daemon  Daemon mode; defaults to interactive mode
 -h, --help    Show this help
 -n, --notify  Notify via SMS'''.format(script_name)
    )


def report_info(message, daemon_mode = False):
    """ Report by printing to STDOUT or logging to syslog """
    if daemon_mode:
        syslog.syslog(syslog.LOG_INFO, message)
    else:
        print(message)


def twilio_notify(twilio_config, myaqi, daemon_mode):
    """ Notify via Twilio"""
    twilio_client = None
    report_info("Initializing Twilio", daemon_mode)
    twilio_client = twilio.rest.Client(twilio_config.TWILIO_SID,
                                       twilio_config.TWILIO_SECRET)
    if twilio_client is not None:
        from_number = twilio_config.FROM_NUMBER
        to_number = twilio_config.TO_NUMBER
        sms = "AQI is unhealthy - last reading " + str(myaqi)
        twilio_client.messages.create(body=sms,
                                      to=to_number,
                                      from_=from_number)
        report_info("Notified via Twilio", daemon_mode)


def sensor_loop(daemon_mode = False, notify_mode = False):
    """ Main sensor loop that runs forever """
    report_info("Initializing Adafruit.io connection", daemon_mode)

    aio = Client(aqi_monitor_config.ADAFRUIT_IO_USERNAME, aqi_monitor_config.ADAFRUIT_IO_KEY)
    pm25_feed = aio.feeds(aqi_monitor_config.PM25_FEED_KEY)
    pm10_feed = aio.feeds(aqi_monitor_config.PM10_FEED_KEY)
    aqi_feed = aio.feeds(aqi_monitor_config.AQI_FEED_KEY)

    sensor = SDS011("/dev/ttyUSB0", use_query_mode=True)
    lastaqi = None

    try:
       # Read from sensor every 60 seconds
        while True:
            # Turn on the sensor and wait for 15 sec to "warm up"
            report_info("Turning on SDS011 sensor", daemon_mode)
            sensor.sleep(sleep=False)
            time.sleep(15)

            # Read from the sensor
            report_info("Querying SDS011 sensor", daemon_mode)
            try:
                pm25, pm10 = sensor.query()
            except serial.SerialException:
                exc_type, value, exc_traceback = sys.exc_info()
                if daemon_mode:
                    syslog.syslog(syslog.LOG_ERR, exc_type)
                    syslog.syslog(syslog.LOG_ERR, value)
                    syslog.syslog(syslog.LOG_ERR, exc_traceback)
                else:
                    print(exc_type, value, exc_traceback)
            myaqi = aqi.to_aqi([
                    (aqi.POLLUTANT_PM25, pm25),
                    (aqi.POLLUTANT_PM10, pm10)
            ])
            report_info("PM2.5: {}, PM10: {}, AQI: {}".format(pm25, pm10, myaqi), daemon_mode)


            # Turn off the sensor
            report_info("Turning off SDS011 sensor", daemon_mode)
            sensor.sleep()

            # Notify if AQI is unhealthy
            if notify_mode and myaqi >= 100 and (lastaqi is None or lastaqi < 100):
                twilio_notify(aqi_monitor_config, myaqi, daemon_mode)

            # Send data to Adafruit.io
            try:
                report_info("Sending data to Adafruit.IO", daemon_mode)
                aio.send_data(pm25_feed.key, pm25)
                aio.send_data(pm10_feed.key, pm10)
                aio.send_data(aqi_feed.key, float(myaqi))
                report_info("Sent data to Adafruit.IO", daemon_mode)
            except AdafruitIOError:
                if daemon_mode:
                    syslog.syslog(syslog.LOG_ERR, "Failed to send data to Adafruit.IO")
                else:
                    print("Failed to send data to Adafruit.IO")

            lastaqi = myaqi
            time.sleep(45)
    except KeyboardInterrupt:
        if sensor is not None:
            sensor.sleep()


def main() -> int:
    """ Main function - parse options and start the sensor loop """
    try:
        opts, _ = getopt.getopt(sys.argv[1:], "dhn", ["daemon", "help", "notify"])
    except getopt.GetoptError as err:
        print(err)
        syslog.syslog(syslog.LOG_ERR, str(err))
        usage()
        return 2

    daemon_mode = False
    notify_mode = False

    for opt, _ in opts:
        if opt in ("-d", "--daemon"):
            daemon_mode = True
        elif opt in ("-h", "--help"):
            usage()
            return 0
        elif opt in ("-n", "--notify"):
            notify_mode = True
        else:
            assert False, "unhandled option"

    report_info("Starting AQI monitor", daemon_mode)
    if daemon_mode:
        with daemon.DaemonContext():
            sensor_loop(daemon_mode, notify_mode)
    else:
        sensor_loop(daemon_mode, notify_mode)

    return 0


if __name__ == '__main__':
    sys.exit(main())
