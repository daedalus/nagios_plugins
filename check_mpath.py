#!/usr/bin/env python
#
# Nagios plugin to check the state of multipath devices for linux and esxi
#
# (C) 2006 Dario Clavijo
# Licensed under the General Public License, Version 3
# Contact: Dario Clavijo, clavijodario@gmail.com
#
# v1.0 initial version

import sys
import re
import paramiko
from optparse import OptionParser

status = { 0:'OK' , 1:'WARNING', 2: 'CRITICAL' , 3: 'UNKNOWN'}
last_device_count = 0

# execute a remote command by ssh
def exec_ssh(host,user,passwd,command):
	ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host, username=user, password=passwd)
        stdin, stdout, stderr = ssh.exec_command(command)
	return stdout.readlines()

# parse the results of the esxi esxcfg-mpath -l
def parse_esxi_mpath(data):
	global last_device_count
	device = ""
	state = ""
	active = 0
	devices = "\n"
	num_status = 0
	device_count = 0
	wwn = 0
	if data:
		for line in data:
			line = line.replace('\n',"")
			if re.search('Device: ', line):
				device = line[11:]	
			if re.search('State: ', line):
				state = line[10:]
			if re.search('Target Transport',line):
				wwn = line[35:]
					
			if device != "" and state != "":
				device_count += 1

				if state == "dead":
					num_status = 1
				if state == "unkown":
					num_status = 3 
				if state == "disabled":
					num_status = 1

				if state == 'active':
					active += 1
	
				#print device,state	

				devices = devices + "Device: %s WWN: %s Status: %s" % (device,wwn,state) 
				devices = devices + "\n" 
				device = ""
				dev_state = ""

		if device_count < last_device_count:
			num_status = 1

		if active < 2:
			num_status = 2

		last_device_count = device_count
	else:
		num_status = 3

	return (num_status,devices)

# parse the results of the linux command multipath -l
def parse_linux_mpath(data):
	global last_device_count
        str_status = ''
        ret = 0
	active = 0
	device_count = 0

        def is_hex(s):
        	try:
                	int(s, 16)
                	return True
        	except ValueError:
                	return False
	if data:
	        for line in data:
        	        line = line.replace('\n','')
                	d = line[:33]
	                device = ''

        	        if is_hex(d):
                	        device = d
                        	str_status += '\nDevice: %s ' % device
				device_count += 1

        	        p = line.find('status=')
                	if p > 0:
                        	status = line[p+7:]
	                        str_status += 'Status: %s ' % status

        	                if (status != 'active' and status != 'enabled'):
                	                #print 'status',status
                        	        ret = 1
				if(status  == 'active'):
					active += 1
			
		if device_count < last_device_count:
        	       	num_status = 1

		if active < 2:
			ret = 2

		last_device_count = device_count
	else:
		ret = 3

        return ret,str_status

# ssh backend
def ssh_mpath(host,user,passwd,system):
	if system == 'esxi':
		command = 'esxcfg-mpath -l'
		data = exec_ssh(host,user,passwd,command)
		return parse_esxi_mpath(data)
	elif system == 'linux':
		command = 'multipath -l'
		data = exec_ssh(host,user,passwd,command)
		return parse_linux_mpath(data)
	else:
		return (3,'\nSYSTEM NOT IMPLEMENTED')

# save the results in a cache 
def savecache(host,devices):
        fp = open('/tmp/check_mpath.%s.tmp' % host,'w')
        fp.write('devices=%s' % str(devices))
        fp.close()

# read the results from the cache
def readcache(host):
        fp = open('/tmp/check_mpath.%s.tmp' % host,'r')
        for line in fp:
                line = line.replace('\n','')
                p = line.find('devices=')
                if p > -1:
                        return int(line[8:])

def main():
	global last_device_count

	# parse earch argument into the needed options
	parser = OptionParser()
	parser.add_option("-H","--host",dest="host")
	parser.add_option("-u","--user", dest="user")
	parser.add_option("-p","--passwd",dest="passwd")
	parser.add_option("-b","--backend",dest="backend")
	parser.add_option("-s","--system",dest="system")

	(options,args) = parser.parse_args()

	host = options.host
	user = options.user
	passwd = options.passwd

	try:
		last_device_count = readcache(host)
	except:
		last_device_count = -1

	if options.backend == 'ssh':
		num_status,device_summary = ssh_mpath(host,user,passwd,options.system)
	elif options.backend == 'snmp':
		num_status = 3
		device_summary = '\nBACKEND STILL NOT IMPLEMENTED'
	else:
		num_status = 3
                device_summary = '\nBACKEND NOT IMPLEMENTED'

	savecache(host,last_device_count)

	# output check results
	print status[num_status] + device_summary
	sys.exit(num_status)

# Main entry point
if __name__ == "__main__":
	main()
