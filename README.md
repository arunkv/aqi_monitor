# aqi_monitor
AQI monitor on a Raspberry Pi using the SDS011 PM sensor and Adafruit IO for reporting

## Dependencies
- Python3
- [python-aqi](https://pypi.org/project/python-aqi/ "python-aqi")
- [Adafruit_IO](https://adafruit-io-python-client.readthedocs.io/en/latest/quickstart.html "Adafruit_IO")

## Usage

Follow instructions in `aqi_monitor_config.py.sample` to configure 

Then run with:

`aqi_monitor.py [-d]`
`-d, --daemon  Daemon mode; defaults to interactive mode`

