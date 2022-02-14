#!/usr/bin/env python3

# AQI Monitor
# - Read PM2.5 and PM10 metrics from an SDS011 PM sensor via USB
# - Computes AQI and uploads metrics to Adafruit.IO
# - Optionallys ends SMS via Twilio when AQI is unhealthy
# - Runs as daemon or in interactive mode

import daemon, getopt, os, sys, syslog, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))+'/py-sds011')

# https://github.com/ikalchev/py-sds011
from sds011 import SDS011

# https://adafruit-io-python-client.readthedocs.io/en/latest/quickstart.html#basic-client-usage
from Adafruit_IO import *

# https://pypi.org/project/python-aqi/
import aqi

import twilio.rest

def usage():
    scriptName = os.path.basename(__file__)
    print(
        '''Usage: {} [options]
 -d, --daemon  Daemon mode; defaults to interactive mode
 -h, --help    Show this help
 -n, --notify  Notify via SMS'''.format(scriptName)
    )


def version():
    scriptName = os.path.basename(__file__)
    versionNumber = open("VERSION.TXT", "r").read()
    print("{} version {}".format(scriptName, versionNumber))


def sensor_loop(daemonMode = False, notifyMode = False):
    if daemonMode:
        syslog.syslog(syslog.LOG_INFO, "Initializing Adafruit.io connection")
    else:
        print("Initializing Adafruit.io connection")
    import aqi_monitor_config
    aio = Client(aqi_monitor_config.ADAFRUIT_IO_USERNAME, aqi_monitor_config.ADAFRUIT_IO_KEY)
    pm25_feed = aio.feeds(aqi_monitor_config.PM25_FEED_KEY)
    pm10_feed = aio.feeds(aqi_monitor_config.PM10_FEED_KEY)
    aqi_feed = aio.feeds(aqi_monitor_config.AQI_FEED_KEY)

    twilioClient = None
    if notifyMode:
        if daemonMode:
            syslog.syslog(syslog.LOG_INFO, "Initializing Twilio")
        else:
            print("Initializing Twilio")
        twilioClient = twilio.rest.Client(aqi_monitor_config.TWILIO_SID, aqi_monitor_config.TWILIO_SECRET)


    sensor = SDS011("/dev/ttyUSB0", use_query_mode=True)
    lastaqi = None

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
            try:
                pm25, pm10 = sensor.query()
            except:
                exc_type, value, exc_traceback = sys.exc_info()
                if daemonMode:
                    syslog.syslog(syslog.LOG_ERROR, exc_type)
                    syslog.syslog(syslog.LOG_ERROR, value)
                    syslog.syslog(syslog.LOG_ERROR, exc_traceback)
                else:
                    print(exc_type, value, exc_traceback)
            myaqi = aqi.to_aqi([
                    (aqi.POLLUTANT_PM25, pm25),
                    (aqi.POLLUTANT_PM10, pm10)
            ])
            if daemonMode:
                syslog.syslog(syslog.LOG_INFO, "PM2.5: {}, PM10: {}, AQI: {}".format(pm25, pm10, myaqi))
            else:
                print("PM2.5: {}, PM10: {}, AQI: {}".format(pm25, pm10, myaqi))


            # Notify if AQI is unhealthy
            if notifyMode and myaqi >= 100 and (lastaqi is None or lastaqi < 100) and twilioClient is not None:
                fromNumber = aqi_monitor_config.FROM_NUMBER
                toNumber = aqi_monitor_config.TO_NUMBER
                twilioClient.messages.create(body="AQI is unhealthy - last reading " + str(myaqi),
                                             to=toNumber, from_=fromNumber)
                if daemonMode:
                    syslog.syslog(syslog.LOG_INFO, "Notified via Twilio")
                else:
                    print("Notified via Twilio")

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


            lastaqi = myaqi
            time.sleep(45)
    except KeyboardInterrupt:
        if sensor is not None:
            sensor.sleep()


def main() -> int:
    try:
        opts, args = getopt.getopt(sys.argv[1:], "dhn", ["daemon", "help", "notify"])
    except getopt.GetoptError as err:
        print(err)
        syslog.syslog(syslog.LOG_ERR, str(err))
        usage()
        return 2

    daemonMode = False
    notifyMode = False

    for o, a in opts:
        if o in ("-d", "--daemon"):
            daemonMode = True
        elif o in ("-h", "--help"):
            usage()
            return 0
        elif o in ("-n", "--notify"):
            notifyMode = True
        else:
            assert False, "unhandled option"

    if daemonMode:
        syslog.syslog(syslog.LOG_INFO, "Starting AQI monitor in daemon mode")
        with daemon.DaemonContext():
            sensor_loop(daemonMode, notifyMode)
    else:
        print("Starting AQI monitor in interactive mode")
        sensor_loop(daemonMode, notifyMode)

    return 0


if __name__ == '__main__':
    sys.exit(main())

