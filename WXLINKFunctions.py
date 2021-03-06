
######################################
#
# readWXLINKData and buildWXLINKGraph
#
#
######################################

import gc
import matplotlib
# Force matplotlib to not use any Xwindows backend.
matplotlib.use('Agg')

from matplotlib import pyplot
from matplotlib import dates
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
import pylab

import sys

import smbus 
import time

from pytz import timezone

from struct import *


i2cbus = smbus.SMBus(1)

WXLINKaddress = 0x08


import httplib2 as http
import json


try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

from datetime import datetime
import MySQLdb as mdb


WXLINKtableName = 'WXLINKTable'

# set up your WxLink I2C address IP Address here
uri = 'http://192.168.1.140/FullDataString'
path = '/'

# fetch the JSON data from the OurWeather device
def fetchJSONData(uri, path):
	target = urlparse(uri+path)
	method = 'GET'
	body = ''

	h = http.Http()
	
	# If you need authentication some example:
	#if auth:
	#    h.add_credentials(auth.user, auth.password)

	response, content = h.request(
        	target.geturl(),
        	method,
        	body,
        	headers)

	# assume that content is a json reply
	# parse content with the json module
	data = json.loads(content)

	return data

headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json; charset=UTF-8'
}





def readWXLINKData(password):
    	print('readWXLINKData - The time is: %s' % datetime.now(timezone('US/Pacific')))

   	data1 = "" 
   	data2 =  ""
   	print "-----------"
   	print "block 1"
   	data1 = i2cbus.read_i2c_block_data(WXLINKaddress, 0);
	data1 = bytearray(data1)
   	#data1 = i2cbus.read_i2c_block_data(WXLINKaddress, 0);
   	print ' '.join(hex(x) for x in data1) 
   	print "block 2"
   	data2 = i2cbus.read_i2c_block_data(WXLINKaddress, 1);
	data2 = bytearray(data2)
   	#data2 = i2cbus.read_i2c_block_data(WXLINKaddress, 1);
   	print ' '.join(hex(x) for x in data2) 
   	print "-----------"
	
	#data1

	print len(data1)
	header0 = data1[0]
	header1 = data1[1]
	protocol = data1[2]
	timeSinceReboot = unpack('i',str(data1[3:7]))[0]
	windDirection = unpack('H', str(data1[7:9]))[0]
	averageWindSpeed = unpack('f', str(data1[9:13]))[0]
	windClicks = unpack('l', str(data1[13:17]))[0]
	totalRainClicks = unpack('l', str(data1[17:21]))[0]
	maximumWindGust = unpack('f', str(data1[21:25]))[0]
	outsideTemperature = unpack('f', str(data1[25:29]))[0]
	elements = [data1[29], data1[30], data1[31], data2[0]]
	outHByte = bytearray(elements)
	outsideHumidity = unpack('f', str(outHByte))[0]

	# data2

	batteryVoltage = unpack('f', str(data2[1:5]))[0]
	batteryCurrent = unpack('f', str(data2[5:9]))[0]
	loadCurrent = unpack('f', str(data2[9:13]))[0]
	solarPanelVoltage = unpack('f', str(data2[13:17]))[0]
	solarPanelCurrent = unpack('f', str(data2[17:21]))[0]
	
	auxA = unpack('f', str(data2[21:25]))[0]
	messageID = unpack('l', str(data2[25:29]))[0]
	checksumLow = data2[29]
	checksumHigh = data2[30]


	print "header = %x %x" % (header0, header1)
	print "protocol = %d" % (protocol )
	print "timeSinceReboot = %d" % timeSinceReboot
	print "windDirection = %d" % windDirection
	print "averageWindSpeed = %6.2f" % averageWindSpeed
	print "windClicks = %d" % windClicks
	print "totalRainClicks = %d" % totalRainClicks
	print "maximumWindGust = %6.2f" % maximumWindGust
	print "outsideTemperature = %6.2f" % outsideTemperature
	print "outsideHumidity = %6.2f" % outsideHumidity

	# data 2

	print "batteryVoltage = %6.2f" % batteryVoltage
	print "batteryCurrent = %6.2f" % batteryCurrent
	print "loadCurrent = %6.2f" % loadCurrent
	print "solarPanelVoltage = %6.2f" % solarPanelVoltage
	print "solarPanelCurrent = %6.2f" % solarPanelCurrent
	print "auxA = %6.2f" % auxA
	print "messageID = %d" % (messageID )
	print "checksumHigh =0x%x" % (checksumHigh )
	print "checksumLow =0x%x" % (checksumLow )

	# open database
	con = mdb.connect('localhost', 'root', password, 'DataLogger' )
	cur = con.cursor()

	#
	# Now put the data in MySQL
	# 
        # Put record in MySQL

        print "writing SQLdata ";

	# get last record read
	query = "SELECT MessageID FROM "+WXLINKtableName+" ORDER BY id DESC LIMIT 1"
        cur.execute(query)	

	results = cur.fetchone()
	lastMessageID = results[0]
	print "lastMessageID =", lastMessageID


	if (lastMessageID != messageID):
        	# write record
        	deviceid = 0
        	query = 'INSERT INTO '+WXLINKtableName+(' (TimeStamp , deviceid , Protocol, Outdoor_Temperature , Outdoor_Humidity , Indoor_Temperature , Barometric_Pressure , Current_Wind_Speed , Current_Wind_Clicks , Current_Wind_Direction , Rain_Total_Clicks , Battery_Voltage , Battery_Current , Load_Current , Solar_Panel_Voltage , Solar_Panel_Current , MessageID , Time_Since_Reboot , AuxA) VALUES(CONVERT_TZ(UTC_TIMESTAMP(),"+00:00","-07:00"), %i, %i, %.3f, %.3f, %.3f, %.3f, %.3f, %i, %i, %i, %.3f, %.3f, %.3f, %.3f, %.3f, %i, %i, %.3f)' % (0, protocol, outsideTemperature, outsideHumidity, 0, 0, averageWindSpeed , windClicks, windDirection, totalRainClicks, batteryVoltage, batteryCurrent, loadCurrent, solarPanelVoltage, solarPanelCurrent,  messageID, timeSinceReboot, auxA)) 


        
		print("query=%s" % query)

        	cur.execute(query)	

	con.commit()




# WXLINK graph building routine


def buildWXLINKGraphSolar(password, myGraphSampleCount):
    		print('buildWXLINKGraphSolar - The time is: %s' % datetime.now(timezone('US/Pacific')))

		# open database
		con1 = mdb.connect('localhost', 'root', password, 'DataLogger' )
		# now we have to get the data, stuff it in the graph 

    		mycursor = con1.cursor()

		print myGraphSampleCount
		query = '(SELECT timestamp, deviceid, Outdoor_Temperature, OutDoor_Humidity, Battery_Voltage, Battery_Current, Solar_Panel_Voltage, Solar_Panel_Current,  Load_Current, id FROM '+WXLINKtableName+' ORDER BY id DESC LIMIT '+ str(myGraphSampleCount) + ') ORDER BY id ASC' 

		print "query=", query
		try:
			mycursor.execute(query)
			result = mycursor.fetchall()
		except:
			e=sys.exc_info()[0]
			print "Error: %s" % e

		
		t = []   # time
		u = []   # Battery_Voltage
		v = []   # Battery_Current 
		x = []   # Solar_Panel_Voltage 
		y = []   # Solar_Panel_Current 
		z = []   # Load_Current 
		averagePowerIn = 0.0
		averagePowerOut = 0.0
 		currentCount = 0

		for record in result:
			t.append(record[0])
			u.append(record[4])
			v.append(record[5])
			x.append(record[6])
			y.append(record[7])
			z.append(record[8])

		print ("count of t=",len(t))

		fds = dates.date2num(t) # converted
		# matplotlib date format object
		hfmt = dates.DateFormatter('%H:%M:%S')
		#hfmt = dates.DateFormatter('%m/%d-%H')

		fig = pyplot.figure()
		fig.set_facecolor('white')
		ax = fig.add_subplot(111,axisbg = 'white')
		ax.vlines(fds, -200.0, 1000.0,colors='w')
		
		ax2 = fig.add_subplot(111,axisbg = 'white')


		ax.xaxis.set_major_formatter(hfmt)
		pyplot.xticks(rotation='45')
		pyplot.subplots_adjust(bottom=.3)
		pylab.plot(t, u, color='red',label="Battery Voltage (V) ",linestyle="-",marker=".")
		pylab.plot(t, x, color='green',label="Solar Voltage (V) ",linestyle="-",marker=".")
		pylab.xlabel("Time")
		pylab.ylabel("Voltage (V)")
		pylab.legend(loc='upper left', fontsize='x-small')
		pylab.axis([min(t), max(t), 0, 7])

		ax2 = pylab.twinx()
		pylab.ylabel("Current (mA) ")
		pylab.plot(t, v, color='black',label="Battery Current (mA)",linestyle="-",marker=".")
		pylab.plot(t, y, color='blue',label="Solar Current (mA)",linestyle="-",marker=".")
		pylab.plot(t, z, color='purple',label="Load Current (mA)",linestyle="-",marker=".")
		pylab.axis([min(t), max(t), -60, 80])
		pylab.legend(loc='lower left', fontsize='x-small')

		pylab.figtext(.5, .05, ("Solar Performance WXLink\n%s") % datetime.now(timezone('US/Pacific')),fontsize=18,ha='center')
		pylab.grid(True)

		pyplot.show()
		pyplot.savefig("/var/www/html/WXLINKDataLoggerGraphSolar.png", facecolor=fig.get_facecolor())	



		mycursor.close()       	 
		con1.close()

		fig.clf()
		pyplot.close()
		pylab.close()
		gc.collect()
		print "------WXLINKGraphTemperature finished now"



def buildWXLINKGraphTemperature(password, myGraphSampleCount):
    		print('buildWXLINKGraph - The time is: %s' % datetime.now(timezone('US/Pacific')))

		# open database
		con1 = mdb.connect('localhost', 'root', password, 'DataLogger' )
		# now we have to get the data, stuff it in the graph 

    		mycursor = con1.cursor()

		print myGraphSampleCount
		query = '(SELECT timestamp, deviceid, Outdoor_Temperature, OutDoor_Humidity, OurWeather_Station_Name, id FROM '+WXLINKtableName+' ORDER BY id DESC LIMIT '+ str(myGraphSampleCount) + ') ORDER BY id ASC' 

		print "query=", query
		try:
			mycursor.execute(query)
			result = mycursor.fetchall()
		except:
			e=sys.exc_info()[0]
			print "Error: %s" % e


		t = []   # time
		u = []   # Outdoor temperature
		v = []   # Outdoor humidity
		averageTemperature = 0.0
 		currentCount = 0

		for record in result:
			t.append(record[0])
			u.append(record[2])
			v.append(record[3])
			averageTemperature = averageTemperature+record[2]
			currentCount=currentCount+1
			StationName = record[4]

		averageTemperature = averageTemperature/currentCount
		
		print ("count of t=",len(t))

		fds = dates.date2num(t) # converted
		# matplotlib date format object
		hfmt = dates.DateFormatter('%H:%M:%S')
		#hfmt = dates.DateFormatter('%m/%d-%H')

		fig = pyplot.figure()
		fig.set_facecolor('white')
		ax = fig.add_subplot(111,axisbg = 'white')
		ax.vlines(fds, -200.0, 1000.0,colors='w')
		
		ax2 = fig.add_subplot(111,axisbg = 'white')



		ax.xaxis.set_major_formatter(hfmt)
		pyplot.xticks(rotation='45')
		pyplot.subplots_adjust(bottom=.3)
		pylab.plot(t, u, color='r',label="Outside Temp (C) ",linestyle="-",marker=".")
		pylab.xlabel("Time")
		pylab.ylabel("degrees C")
		pylab.legend(loc='upper left')
		pylab.axis([min(t), max(t), -20, 50])

		ax2 = pylab.twinx()
		pylab.ylabel("% ")
		pylab.plot(t, v, color='b',label="Outside Hum %",linestyle="-",marker=".")
		pylab.axis([min(t), max(t), 0, 100])
		pylab.legend(loc='lower left')
		pylab.figtext(.5, .05, ("%s Average Temperature %6.2f\n%s") %( StationName, averageTemperature, datetime.now(timezone('US/Pacific'))),fontsize=18,ha='center')
		pylab.grid(True)

		pyplot.show()
		pyplot.savefig("/var/www/html/WXLINKDataLoggerGraphTemperature.png", facecolor=fig.get_facecolor())	



		mycursor.close()       	 
		con1.close()

		fig.clf()
		pyplot.close()
		pylab.close()
		gc.collect()
		print "------WXLINKGraphTemperature finished now"


def buildWXLINKGraphWind(password, myGraphSampleCount):
    		print('buildWXLINKGraph - The time is: %s' % datetime.now(timezone('US/Pacific')))

		# open database
		con1 = mdb.connect('localhost', 'root', password, 'DataLogger' )
		# now we have to get the data, stuff it in the graph 

    		mycursor = con1.cursor()

		print myGraphSampleCount
		query = '(SELECT timestamp, deviceid, Current_Wind_Speed, Current_Wind_Gust, OurWeather_Station_Name, id FROM '+WXLINKtableName+' ORDER BY id DESC LIMIT '+ str(myGraphSampleCount) + ') ORDER BY id ASC' 

		print "query=", query
		try:
			mycursor.execute(query)
			result = mycursor.fetchall()
		except:
			e=sys.exc_info()[0]
			print "Error: %s" % e


		t = []   # time
		u = []   # Current Wind Speed
		v = []   # Current Wind Gust 
		averageWindSpeed = 0.0
 		currentCount = 0

		for record in result:
			t.append(record[0])
			u.append(record[2])
			#v.append(record[3])
			averageWindSpeed = averageWindSpeed+record[2]
			currentCount=currentCount+1
			StationName = record[4]

		averageWindSpeed = averageWindSpeed/currentCount
		
		print ("count of t=",len(t))

		fds = dates.date2num(t) # converted
		# matplotlib date format object
		hfmt = dates.DateFormatter('%H:%M:%S')
		#hfmt = dates.DateFormatter('%m/%d-%H')

		fig = pyplot.figure()
		fig.set_facecolor('white')
		ax = fig.add_subplot(111,axisbg = 'white')
		ax.vlines(fds, -200.0, 1000.0,colors='w')



		#ax.xaxis.set_major_locator(dates.MinuteLocator(interval=1))
		ax.xaxis.set_major_formatter(hfmt)
		ax.set_ylim(bottom = -200.0)
		pyplot.xticks(rotation='45')
		pyplot.subplots_adjust(bottom=.3)
		pylab.plot(t, u, color='r',label="Wind Speed (kph)" ,linestyle="o",marker=".")
		#pylab.plot(t, v, color='b',label="Wind Gust (kph)" ,linestyle="o",marker=".")
		pylab.xlabel("Time")
		pylab.ylabel("Wind (kph)")
		pylab.legend(loc='lower center')
		pylab.axis([min(t), max(t), min(u)-20, max(u)+20])
		pylab.figtext(.5, .05, ("%s Average Windspeed %6.2f\n%s") %( StationName, averageWindSpeed, datetime.now(timezone('US/Pacific'))),fontsize=18,ha='center')

		pylab.grid(True)

		pyplot.show()
		pyplot.savefig("/var/www/html/WXLINKDataLoggerGraphWind.png", facecolor=fig.get_facecolor())	



		mycursor.close()       	 
		con1.close()

		fig.clf()
		pyplot.close()
		pylab.close()
		gc.collect()
		print "------WXLINKGraphWind finished now"


######################################
#
# readWXLINKData and buildWXLINKGraph
#
#
######################################

