#! /usr/bin/python
import Adafruit_DHT
import sys
import sqlite3

humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.AM2302,'22')
if humidity is not None and temperature is not None:
	conn = sqlite3.connect('/home/pi/devel/littlepibot/littlepibot.db')
	curs = conn.cursor()
	curs.execute("""INSERT INTO sensor_data values(date('now'), time('now'),
					(?), (?))""", (temperature, humidity))
	conn.commit()
	conn.close()
else:
	print ('No sensor data retrieved!')

