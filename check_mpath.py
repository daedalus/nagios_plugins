#!/bin/sh
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


def exec_ssh(host,user,passwd,command):

	ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host, username=user, password=passwd)
        stdin, stdout, stderr = ssh.exec_command(command)
	return stdout.readlines()

def parse_esxi_mpath(data):
	device = ""
	state = ""
	active = 0

	devices = ""

	num_status = 0

	for line in data:
		line = line.replace('\n',"")
		if re.search('Device: ', line):
			device = line[11:]	
		if re.search('State: ', line):
			state = line[9:]
		
		if device != "" and state != "":

			if state == "dead":
				num_status = 1
			if state == "unkown":
				num_status = 3 
			if state == "disabled":
				num_status = 1

			if state == 'active':
				active += 1
		
			#print device,state	

			devices = devices + "%s %s" % (device,state) 
			devices = devices + "\n" 
			device = ""
			dev_state = ""
	if active < 2:
		num_status = 2

	return (num_status,devices)

def parse_linux_mpath(data):
        str_status = ''

        ret = 0
	active = 0

        def is_hex(s):
        	try:
                	int(s, 16)
                	return True
        	except ValueError:
                	return False

        for line in data:
                line = line.replace('\n','')
                d = line[:33]
                device = ''

                if is_hex(d):
                        device = d
                        str_status += '\ndevice %s ' % device

                p = line.find('status=')
                if p > 0:
                        status = line[p+7:]
                        str_status += 'status %s ' % status

                        if (status != 'active' and status != 'enabled'):
                                #print 'status',status
                                ret = 1
			if(status  == 'active'):
				active += 1
			
		if active < 2:
			ret = 2

                #str_status += '\n'

        return ret,str_status

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
		return (3,'SYSTEM NOT IMPLEMENTED')

def main():

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

	if options.backend == 'ssh':
		num_status,devices = ssh_mpath(host,user,passwd,options.system)
	elif options.backend == 'snmp':
		num_status = 3
		devices = 'BACKEND NOT IMPLEMENTED'
	else:
		num_status = 3
                devices = 'BACKEND NOT IMPLEMENTED'



	print status[num_status] + "\n" + devices
	sys.exit(num_status)

if __name__ == "__main__":
	main()
