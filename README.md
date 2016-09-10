# mysql-dumper
Simple python script that dumps mysql database into a slave, using mysqldump.

This utility takes as arguments your mysql user and password and a slave to transfer the dump.

The dump will be copy over to the slave and use the old classic way to apply a dump: ```mysql < dump.sql ```

Then it will execute ```CHANGE MASTER . . ``` and make for you master-slave servers automatically.

## Requirements
- Python 2.4+
- SSH keys between the servers

## Usage
The usage is simple as that:

```mysql_dump.py <mysql_user> <mysql_password> <slave dns name>```

Example:

```mysql_dump.py root Aa123456 mysqldb-prod2```

You may want to customize the following variables according to your env:
```
## Mysql Specific Variables  - can be customized##
mycnf = '/etc/my.cnf'
mysql_replication_user = 'repl'
mysql_replication_password = 'repl'
mysql_master_connect_retry = '60'
#mysqldump arguments
mysqldump_arguments = '--all-databases --events --flush-logs --routines --triggers --master-data=2 --single-transaction'
```
