#!/usr/bin/python

import os
import subprocess
import re
import sys
import time
import socket

# This method will execute remote ssh
def runscript_remote(host,cmd):
  print ('###########################################################')
  print ('Executing '+cmd+' on '+host)
  ssh = subprocess.Popen(['ssh','-q','-o StrictHostKeyChecking=no','-o UserKnownHostsFile=/dev/null', "%s" % host, cmd],
                         shell=False,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
  result = ssh.stdout.readlines()
  if result == []:
      error = ssh.stderr.readlines()
      print >>sys.stderr, " %s" % error
  else:
      print result

# This method will execute bash commands by cmd argument
def runscript(cmd):
  try:
      print ('###########################################################')
      print ('Executing '+cmd+' on '+socket.gethostname())
      cmd_shell = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
      result = cmd_shell.communicate(input=cmd)
      if result[1] == '':
          return result[0]
      else:
          pass
          # TODO: throw error result[1]
  except Exception:
      raise
  return result


# Check argv (arguments given to the script)
if len(sys.argv) == 4:
    mysql_user     =  sys.argv[1]
    mysql_password =  sys.argv[2]
    mysql_slave    =  sys.argv[3]
else:
    print 'Usage: mysql_dump.py <mysql_user> <mysql_password> <slave dns name>'
    print 'The above arguments is mandatory!'
    quit()


## Mysql Specific Variables  - can be customized##
mycnf = '/etc/my.cnf'
mysql_replication_user = 'repl'
mysql_replication_password = 'repl'
mysql_master_connect_retry = '60'

## General Variables ##
dump_dir = '/outbrain/mysql/dump_'+time.strftime("%d-%m-%Y")
dump_name = 'dump_'+socket.gethostname()+'_'+time.strftime("%d-%m-%Y")+'.sql'
mysql_version = runscript('mysqladmin -V | cut -d\' \' -f6 | cut -d\'-\' -f1 | cut -d\'.\' -f1,2')
mysql_version = float(mysql_version)

# Fetch port out of my.cnf
mysql_port = runscript('cat '+mycnf+' | grep -v report_port |grep "port ="')
mysql_port = mysql_port.replace('port = ','').replace('\n','')
if (mysql_port == ''):
    mysql_port = '3306'

# Fetch socket out of my.cnf
mysql_socket = runscript('cat '+mycnf+' | grep socket | uniq')
mysql_socket = mysql_socket.replace('socket = ','').replace('\n','')
if (mysql_socket == ''):
    mysql_socket = '/tmp/mysql.sock'

# Fetch datadir out of my.cnf
mysql_datadir = runscript('cat '+mycnf+' | grep datadir')
mysql_datadir = mysql_datadir.replace('datadir = ','').replace('\n','')
if (mysql_datadir == ''):
    mysql_datadir = '/var/lib/mysql'

#mysqldump arguments
mysqldump_arguments = '--all-databases --events --flush-logs --routines --triggers --master-data=2 --single-transaction'

# Create dump dir
runscript('mkdir -p '+dump_dir)

# Dump database
runscript('mysqldump -S '+mysql_socket+' -u'+mysql_user+' -p'+mysql_password+' '+mysqldump_arguments+' > '+dump_dir+'/'+dump_name)

# Kill mysql on slave
runscript_remote(mysql_slave,'pkill -9 -f mysqld')

# Remove destination data dir on slave
runscript_remote(mysql_slave,'rm -rf '+mysql_datadir+'/*')

# Create the dest dump dir
runscript_remote(mysql_slave,'mkdir -p '+dump_dir)

# Copy over the dump.sql
runscript('scp -o \"StrictHostKeyChecking=no\" -o \"UserKnownHostsFile=/dev/null\" '+dump_dir+'/'+dump_name+' root@'+mysql_slave+':'+dump_dir+'/')


# Check if version is 5.5 and below or above and initalize slave db
if mysql_version <= 5.5:
    runscript_remote(mysql_slave,'mysql_install_db --no-defaults --datadir='+mysql_datadir+' --user=mysql')
else:
    runscript_remote(mysql_slave,'mysqld --initialize-insecure --datadir='+mysql_datadir+' --user=mysql')

# Start mysql on slave
runscript_remote(mysql_slave,'service mysql start')

# Restore the database
runscript_remote(mysql_slave,'mysql -uroot -S '+mysql_socket+' < '+dump_dir+'/'+dump_name)

# flush privileges
runscript_remote(mysql_slave,'mysql -uroot -S '+mysql_socket+' -e \"flush privileges;\"')

# Save the change master file and position from dump
search_in_file = open(dump_dir+'/'+dump_name)
change_master_sql_command=''
for line in search_in_file:
    line = line.rstrip()
    if re.search('-- CHANGE MASTER TO', line) :
        change_master_sql_command=line

# Remove leading string --
change_master_sql_command = change_master_sql_command.replace('-- ','')
# Add additional paramteres
change_master_sql_command = change_master_sql_command.replace(';',',MASTER_HOST = \''+socket.gethostname()+'\', \
                                                               MASTER_USER = \''+mysql_replication_user+'\', \
                                                               MASTER_PASSWORD = \''+mysql_replication_password+'\', \
                                                               MASTER_PORT = '+mysql_port+', \
                                                               MASTER_CONNECT_RETRY = '+mysql_master_connect_retry+';')

# Stop slave
runscript_remote(mysql_slave,'mysql -u'+mysql_user+' -p'+mysql_password+' -S '+mysql_socket+' -e \"stop slave;\"')

# Change maser
runscript_remote(mysql_slave,'mysql -u'+mysql_user+' -p'+mysql_password+' -S '+mysql_socket+' -e \"'+change_master_sql_command+'\"')

# Start slave
runscript_remote(mysql_slave,'mysql -u'+mysql_user+' -p'+mysql_password+' -S '+mysql_socket+' -e \"start slave;\"')

# Remove leftovers of dump files
runscript('rm -rf '+dump_dir)
runscript_remote(mysql_slave,'rm -rf '+dump_dir)
