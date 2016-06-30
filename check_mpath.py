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
def parse_esxi_mpath(data,verbose=False):
	global last_device_count
	device = ""
	state = ""
	active = 0
	dead = 0
	lost_devices = 0
	unknown = 0
	disabled = 0
	devices = "\n"
	ret = 0
	device_count = 0
	wwn = ""
	if data:
		for line in data:
			line = line.replace('\n',"")
			if re.search('Device: ', line):
				device = line[11:]	
			if re.search('State: ', line):
				state = line[10:]
			if re.search('Target Transport',line):
				wwn = line[35:58]
					
			if device != "" and state != "" and wwn != "":
				device_count += 1

				if state == "dead":
					dead += 1
					ret = 1
					wwn = ''
				if state == "unkown":
					unknown += 1
					ret = 3 
				if state == "disabled":
					disabled += 1
					ret = 1
				if state == 'active':
					active += 1
	
				#print device,state	

				if verbose:
					devices = devices + "Device: %s WWN: %s Status: %s" % (device,wwn,state) 
					#devices = devices + "Device: %s Status: %s" % (device,state) 
					devices = devices + "\n" 

				device = ""
				dev_state = ""
		
		lost_devices = last_device_count - device_count 

		if lost_devices > 0:
			ret = 1

		devices = devices + "\nDevices Summary:\nActive: %d\nDisabled: %d\nUnknown: %d\nDead: %d\nLost: %d\n" %(active,disabled,unknown,dead,lost_devices)


		if active < 2:
			ret = 2

		last_device_count = device_count
	else:
		ret = 3

	return (ret,devices)

# parse the results of the linux command multipath -l
def parse_linux_mpath(data,verbose=False):
	global last_device_count
        devices = ''
        ret = 0
	active = 0
	status = ''
	enabled = 0
	lost_devices = 0
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
				device_count += 1

				if verbose:
					devices += "\nDevice: %s " % device

        	        p = line.find('status=')
                	if p > 0:
                        	status = line[p+7:]

        	                if (status != 'active' and status != 'enabled'):
                	                #print 'status',status
                        	        ret = 1
				if(status == 'enabled'):
					enabled += 1
				if(status  == 'active'):
					active += 1
	
				if verbose:
	                       		devices += 'Status: %s ' % status

                lost_devices = last_device_count - device_count

                if lost_devices > 0:
                        ret = 1

                devices = devices + "\nDevices Summary:\nActive: %d\nEnabled: %d\nLost: %d\n" %(active,enabled,lost_devices)

		if active < 2:
			ret = 2

		last_device_count = device_count
	else:
		ret = 3

        return (ret,devices)

# ssh backend
def ssh_mpath(host,user,passwd,system,verbose=False):
	if system == 'esxi':
		command = 'esxcfg-mpath -l'
		data = exec_ssh(host,user,passwd,command)
		return parse_esxi_mpath(data,verbose)
	elif system == 'linux':
		command = 'multipath -l'
		data = exec_ssh(host,user,passwd,command)
		return parse_linux_mpath(data,verbose)
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
	parser.add_option("-v","--verbose",dest="verbose")

	(options,args) = parser.parse_args()

	host = options.host
	user = options.user
	passwd = options.passwd

	try:
		last_device_count = readcache(host)
	except:
		last_device_count = -1

	if options.backend == 'ssh':
		ret,device_summary = ssh_mpath(host,user,passwd,options.system,options.verbose)
	elif options.backend == 'snmp':
		ret = 3
		device_summary = '\nBACKEND STILL NOT IMPLEMENTED'
	else:
		ret = 3
                device_summary = '\nBACKEND NOT IMPLEMENTED'

	savecache(host,last_device_count)

	# output check results
	print status[ret] + device_summary
	sys.exit(ret)

# Main entry point
if __name__ == "__main__":
	main()
