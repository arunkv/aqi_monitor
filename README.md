# aqi_monitor
AQI monitor on a Raspberry Pi using the SDS011 PM sensor and Adafruit IO

## Dependencies
- Python3
- [py-sds011](https://github.com/ikalchev/py-sds011 "py-sds011")
- [python-aqi](https://pypi.org/project/python-aqi/ "python-aqi")
- [Adafruit_IO](https://adafruit-io-python-client.readthedocs.io/en/latest/quickstart.html "Adafruit_IO")

## Usage

Follow instructions in `adafruit_io_creds.pysample` to configure Adafruit

Then run with:

`aqi_monitor.py [-d]`
`-d, --daemon  Daemon mode; defaults to interactive mode`

