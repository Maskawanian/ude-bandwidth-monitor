#!/usr/bin/env python2
import web
import psycopg2
from pprint import pprint
import json
from datetime import datetime,timedelta
import sys
import ConfigParser

render = web.template.render('/opt/ude/share/bandwidth/templates/')

urls = (
	"/internet/bandwidth/(.*)","index",
	"/(.*)", "index"
)
#urls = (
#	"/", "index",
#	"/history","history"
#)
app = web.application(urls, globals())

conn = None
config = None

wrapday = 14 # Day in the month that billing wraps around. Eg. 17-Dec-10
cap = 100 # 100
utc_offset = (21600*1000)*-1

class index:
	def GET(self,name):
		global conn
		global config
		
		if config == None:
			try:
				config = ConfigParser.RawConfigParser()
				config.read('/opt/ude/etc/bandwidth.ini')
			except Exception as e:
				print "E:",e
		if conn == None:
			try:
				conn = psycopg2.connect("dbname='{0}' user='{1}' host='{2}' password='{3}'".format(config.get('Database','dbname'),config.get('Database','user'),config.get('Database','host'),config.get('Database','password')));
			except:
				print "I am unable to connect to the database"
		
		print "GET '{0}'".format(name)
		
		if name in ["","bw/"]:
			suffix = ""
			if wrapday in [1,3,23]:
				suffix = "rd"
			elif wrapday in [2,22]:
				suffix = "nd"
			elif wrapday in [4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,24,25,26,27,28,29,30]:
				suffix = "th"
			elif wrapday in [21,31]:
				suffix = "st"
			
			return render.index(wrapday,suffix)
		elif name in ["history","bw/history"]:
			
			mx_data_u,mx_data_d,mx_data_c = self.get_data()
			return render.history(json.dumps(mx_data_u),json.dumps(mx_data_d),json.dumps(mx_data_c))
			
		elif name in ["m0","bw/m0"]:
			date_start,date_end = self.get_billing_start_end()
			
			mx_data_u,mx_data_d,mx_data_c = self.get_data(date_start,date_end)
			return render.m0(json.dumps(mx_data_u),json.dumps(mx_data_d),json.dumps(mx_data_c),cap)
			
		elif name in ["m1","bw/m1"]:
			date_start,date_end = self.get_billing_start_end_last()
			mx_data_u,mx_data_d,mx_data_c = self.get_data(date_start,date_end)
			
			return render.m1(json.dumps(mx_data_u),json.dumps(mx_data_d),json.dumps(mx_data_c),cap)
		elif name in ["m2","bw/m2"]:
			date_start,date_end = self.get_billing_start_end_last2()
			mx_data_u,mx_data_d,mx_data_c = self.get_data(date_start,date_end)
			return render.m2(json.dumps(mx_data_u),json.dumps(mx_data_d),json.dumps(mx_data_c),cap)
		elif name in ["today","bw/today"]:
			date_now = datetime.now()
			date_start = datetime(date_now.year,date_now.month,date_now.day,0,0,0,0)
			date_end = datetime(date_now.year,date_now.month,date_now.day,24-1,60-1,60-1,1000000-1)
			mx_data_u,mx_data_d,mx_data_c = self.get_data(date_start,date_end)
			return render.today(json.dumps(mx_data_u),json.dumps(mx_data_d),json.dumps(mx_data_c))
		else:
			return name
	
	def get_billing_start_end_last2(self):
		bdate_start,bdate_end = self.get_billing_start_end_last()
		
		date_start = None
		date_end = None
		
		if bdate_start.month == 1:
			date_start = datetime(bdate_start.year-1,12,bdate_start.day,bdate_start.hour,bdate_start.minute,bdate_start.second,bdate_start.microsecond)
		else:
			date_start = datetime(bdate_start.year,bdate_start.month-1,bdate_start.day,bdate_start.hour,bdate_start.minute,bdate_start.second,bdate_start.microsecond)
		
		if bdate_end.month == 1:
			date_end = datetime(bdate_end.year-1,12,bdate_end.day,bdate_end.hour,bdate_end.minute,bdate_end.second,bdate_end.microsecond)
		else:
			date_end = datetime(bdate_end.year,bdate_end.month-1,bdate_end.day,bdate_end.hour,bdate_end.minute,bdate_end.second,bdate_end.microsecond)
		return date_start,date_end
	
	def get_billing_start_end_last(self):
		bdate_start,bdate_end = self.get_billing_start_end()
		
		date_start = None
		date_end = None
		
		if bdate_start.month == 1:
			date_start = datetime(bdate_start.year-1,12,bdate_start.day,bdate_start.hour,bdate_start.minute,bdate_start.second,bdate_start.microsecond)
		else:
			date_start = datetime(bdate_start.year,bdate_start.month-1,bdate_start.day,bdate_start.hour,bdate_start.minute,bdate_start.second,bdate_start.microsecond)
		
		if bdate_end.month == 1:
			date_end = datetime(bdate_end.year-1,12,bdate_end.day,bdate_end.hour,bdate_end.minute,bdate_end.second,bdate_end.microsecond)
		else:
			date_end = datetime(bdate_end.year,bdate_end.month-1,bdate_end.day,bdate_end.hour,bdate_end.minute,bdate_end.second,bdate_end.microsecond)
		return date_start,date_end
		
	def get_billing_start_end(self):
		date_now = datetime.now()
		date_start = None
		date_end = None
		
		if date_now.day >= wrapday: # After wrapday.
			date_start = datetime(date_now.year,date_now.month,wrapday)
			
			if date_start.month == 12:
				date_end = datetime(date_start.year+1,1,wrapday-1,24-1,60-1,60-1,1000000-1)
			else:
				date_end = datetime(date_start.year,date_start.month+1,wrapday-1,24-1,60-1,60-1,1000000-1)
		else: # Before wrapday.
			
			if date_now.month == 1:
				date_start = datetime(date_now.year-1,12,wrapday)
			else:
				date_start = datetime(date_now.year,date_now.month-1,wrapday)
			
			date_end = datetime(date_now.year,date_now.month,wrapday-1,24-1,60-1,60-1,1000000-1)
		
		return date_start,date_end
	
	def get_data(self,date_start=None,date_end=None):
		# Outbound
		m0_data_u = []
		m0_c = conn.cursor()
		if date_start==None and date_end==None:
			m0_c.execute("""SELECT jstimestamp,gigabytes,time FROM bandwidth_flot WHERE iface_out = 'wan0';""")
		else:
			m0_c.execute("""SELECT jstimestamp,gigabytes,time FROM bandwidth_flot WHERE iface_out = 'wan0' AND time > %s AND time < %s;""",(date_start,date_end))
		m0_rows = m0_c.fetchall()
			
		m0_balance = 0.0
		for m0_row in m0_rows:
			m0_timestamp = m0_row[0]
			m0_timestamp += utc_offset
			m0_balance += m0_row[1]
		
			m0_data_u.append([m0_timestamp,m0_balance])
		del m0_c
		
		# Inbound
		m0_data_d = []
		m0_c = conn.cursor()
		if date_start==None and date_end==None:
			m0_c.execute("""SELECT jstimestamp,gigabytes,time FROM bandwidth_flot WHERE iface_in = 'wan0';""")
		else:
			m0_c.execute("""SELECT jstimestamp,gigabytes,time FROM bandwidth_flot WHERE iface_in = 'wan0' AND time > %s AND time < %s;""",(date_start,date_end))
		m0_rows = m0_c.fetchall()
		
		m0_balance = 0.0
		for m0_row in m0_rows:
			m0_timestamp = m0_row[0]
			m0_timestamp += utc_offset
			m0_balance += m0_row[1]
		
			m0_data_d.append([m0_timestamp,m0_balance])
		del m0_c
		
		# Combined
		m0_data_c = []
		
		for i in range(len(m0_data_d)):
			m0_timestamp = m0_data_u[i][0]
			m0_balance = m0_data_u[i][1] + m0_data_d[i][1]
		
			m0_data_c.append([m0_timestamp,m0_balance])
		
		return m0_data_u,m0_data_d,m0_data_c
		
if __name__ == "__main__":
	app.run()






















































