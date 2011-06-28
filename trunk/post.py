from pprint import pprint
import subprocess
import re
import psycopg2
import ConfigParser

# iptables --list accounting --verbose --exact --zero
if __name__ == '__main__':
	# Try reading settings file.
	config = None
	try:
		config = ConfigParser.RawConfigParser()
		config.read('/opt/ude/etc/bandwidth.ini')
	except Exception as e:
		print "E:",e
		sys.exit()
	
	conn = None
	try:
		conn = psycopg2.connect("dbname='{0}' user='{1}' host='{2}' password='{3}'".format(config.get('Database','dbname'),config.get('Database','user'),config.get('Database','host'),config.get('Database','password')));
	except Exception as e:
		print "I am unable to connect to the database:",e
		sys.exit()
	
	out = subprocess.check_output(["iptables", "--list","accounting", "--verbose", "--exact","--zero"])
	out_lines = out.split("\n")[2:][:-2]
	
	accounting = []
	
	for out_line in out_lines:
		# 1. Remove extra spaces.
		# 2. Remove spaces on the ends.
		# 3. Split into array.
		split = re.sub(r' +',' ',out_line).strip().split(' ')
		accounting.append({
			"packets":int(split[0]),
			"bytes":int(split[1]),
			"target":split[2],
			"protocol":split[3],
			"options":split[4],
			"iface_in":split[5],
			"iface_out":split[6],
			"source":split[7],
			"destination":split[8]
			})
	
	cur = conn.cursor()
	cur.executemany("""INSERT INTO poll_raw(bytes,destination,iface_in,iface_out,options,packets,protocol,source,target) VALUES (%(bytes)s, %(destination)s,%(iface_in)s,%(iface_out)s,%(options)s,%(packets)s,%(protocol)s,%(source)s,%(target)s)""", accounting)
	del cur
	conn.commit()
	

