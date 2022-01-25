#!/usr/bin/env python3

# AQI Monitor
# - Read PM2.5 and PM10 metrics from an SDS011 PM sensor via USB
# - Computes AQI and uploads metrics to Adafruit.IO
# - Runs as daemon or in interactive mode

import daemon, getopt, os, sys, syslog, time

# https://github.com/ikalchev/py-sds011
from sds011 import SDS011

# https://adafruit-io-python-client.readthedocs.io/en/latest/quickstart.html#basic-client-usage
from Adafruit_IO import *

# https://pypi.org/project/python-aqi/
import aqi

# Adafruit.io feeds for the PM2.5, PM10 and AQI metrics
# https://adafruit-io-python-client.readthedocs.io/en/latest/feeds.html
PM25_FEED_KEY = 'plh-aqi-pm-2-dot-5'
PM10_FEED_KEY = 'plh-aqi-pm-10'
AQI_FEED_KEY = 'plh-aqi-aqi'

def usage():
    scriptName = os.path.basename(__file__)
    print(
        '''Usage: {} [options]
 -d, --daemon  Daemon mode; defaults to interactive mode
 -h, --help    Show this help
 -V, --version Show version number and quit'''.format(scriptName)
    )


def version():
    scriptName = os.path.basename(__file__)
    versionNumber = open("VERSION.TXT", "r").read()
    print("{} version {}".format(scriptName, versionNumber))


def sensor_loop(daemonMode = False):
    if daemonMode:
        syslog.syslog(syslog.LOG_INFO, "Initializing Adafruit.io connection")
    else:
        print("Initializing Adafruit.io connection")
    import adafruit_io_creds
    aio = Client(adafruit_io_creds.ADAFRUIT_IO_USERNAME, adafruit_io_creds.ADAFRUIT_IO_KEY)
    pm25_feed = aio.feeds(PM25_FEED_KEY)
    pm10_feed = aio.feeds(PM10_FEED_KEY)
    aqi_feed = aio.feeds(AQI_FEED_KEY)

    sensor = SDS011("/dev/ttyUSB0", use_query_mode=True)

    try:
       # Read from sensor every 60 seconds
        while True:
            # Turn on the sensor and wait for 15 sec to "warm up"
            if daemonMode:
                syslog.syslog(syslog.LOG_INFO, "Turning on SDS011 sensor")
            else:
                print("Turning on SDS011 sensor")
            sensor.sleep(sleep=False)
            time.sleep(15)

            # Read from the sensor
            if daemonMode:
                syslog.syslog(syslog.LOG_INFO, "Querying SDS011 sensor")
            else:
                print("Querying SDS011 sensor")
            pm25, pm10 = sensor.query()
            myaqi = aqi.to_aqi([
                    (aqi.POLLUTANT_PM25, pm25),
                    (aqi.POLLUTANT_PM10, pm10)
            ])
            if daemonMode:
                syslog.syslog(syslog.LOG_INFO, "PM2.5: {}, PM10: {}, AQI: {}".format(pm25, pm10, myaqi))
            else:
                print("PM2.5: {}, PM10: {}, AQI: {}".format(pm25, pm10, myaqi))

            # Turn off the sensor
            if daemonMode:
                syslog.syslog(syslog.LOG_INFO, "Turning off SDS011 sensor")
            else:
                print("Turning off SDS011 sensor")
            sensor.sleep()

            # Send data to Adafruit.io
            try:
                if daemonMode:
                    syslog.syslog(syslog.LOG_INFO, "Sending data to Adafruit.IO")
                else:
                    print("Sending data to Adafruit.IO")
                aio.send_data(pm25_feed.key, pm25)
                aio.send_data(pm10_feed.key, pm10)
                aio.send_data(aqi_feed.key, float(myaqi))
                if daemonMode:
                    syslog.syslog(syslog.LOG_INFO, "Sent data to Adafruit.IO")
                else:
                    print("Sent data to Adafruit.IO")
            except AdafruitIOError:
                if daemonMode:
                    syslog.syslog(syslog.LOG_ERR, "Failed to send data to Adafruit.IO")
                else:
                    print("Failed to send data to Adafruit.IO")


            time.sleep(45)
    except KeyboardInterrupt:
        sensor.sleep()


def main() -> int:
    try:
        opts, args = getopt.getopt(sys.argv[1:], "dhV", ["daemon", "help", "version"])
    except getopt.GetoptError as err:
        print(err)
        syslog.syslog(syslog.LOG_ERR, err)
        usage()
        return 2

    daemonMode = False

    for o, a in opts:
        if o in ("-d", "--daemon"):
            daemonMode = True
        elif o in ("-h", "--help"):
            usage()
            return 0
        elif o in ("-V", "--version"):
            version()
            return 0
        else:
            assert False, "unhandled option"

    if daemonMode:
        syslog.syslog(syslog.LOG_INFO, "Starting AQI monitor in daemon mode")
        with daemon.DaemonContext():
            sensor_loop(daemonMode)
    else:
        print("Starting AQI monitor in interactive mode")
        sensor_loop()

    return 0


if __name__ == '__main__':
    sys.exit(main())

