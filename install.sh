#!/bin/bash
# ___ ___ ___ ___ ____
# |_/ |_   |  |_/ |  |
# | \ |___ |  | \ |__|
#
# Creates the retro client directory tree at ~/.retro
#
# ~/.retro/
#    |__ accounts/
#    |__ config.txt
#    |__ res/
#    |   |__ help/
#    |       |__ chat.txt
#    |       |__ main.txt
#    |__ server-cert.pem
#
base=$HOME/.retro


function ok()   { echo -e "[ \033[32mok\033[0m ]" $@; }
function fail() { echo -e "[\033[31mfail\033[0m]" $@; }


function exec_cmd() {
	# Executes given command and prints a success or
	# error message. Terminates if failed to run cmd.
	if $@ > /dev/null 2>&1; then
		ok "$@"
	else
		fail "$@"
		exit
	fi
}


function create_config_file() {
	# Create the config file at ~/.retro/config.txt
	# Values for server address/port, fileserver port and server certificate
	# must be entered by the user.

	file=$1

	echo
	echo "To create the base config file ~/.retro/config.txt,"
	echo "we need you to provide some information..."
	echo
	echo -n "Server address:  "; read serv_addr; if [ -z $serv_addr ]; then exit; fi
	echo -n "Server port:     "; read serv_port; if [ -z $serv_port ]; then exit; fi
	echo -n "Fileserver port: "; read fileserv_port; if [ -z $fileserv_port ]; then exit; fi
	echo
	echo "Please enter/copy the path to the server's certificate to copy it"
	echo "to it's required location..."
	echo -n "Server certfile: "; read serv_certfile; if [ -z $serv_certfile ]; then exit; fi

	# Create config file ...
	echo "# This is the base configuration file of the retro client." > $file
	echo "# Adjust these values that they fit your personal needs." >> $file
	echo >> $file
	echo "[default]" >> $file
	echo "# Supported loglevels are ERROR,WARN,INFO,DEBUG" >> $file
	echo "loglevel = INFO" >> $file
	echo "# Logmessage format (see python logging module docs)" >> $file
	echo "#logformat = '%(levelname)s  %(message)s'" >> $file
	echo "# Logfile (default: ~/.retro/log.txt)" >> $file
	echo "#logfile = /home/peilnix/.retro/log.txt" >> $file
	echo "# Receive timeout in seconds (default: 5)" >> $file
	echo "#recv_timeout = 5" >> $file
	echo >> $file
	echo "[server]" >> $file
	echo "# Retro server address (default 127.0.0.1)" >> $file
	echo "address = $serv_addr" >> $file
	echo "# Retro server port (default: 8443)" >> $file
	echo "port = $serv_port" >> $file
	echo "# Retroserver fileport (default: 8444)" >> $file
	echo "fileport = $fileserv_port" >> $file
	echo "# Path to server certfile (default: ~/.retro/server-cert.pem)" >> $file
	echo "#certificate = $base/server-cert.pem" >> $file
	echo "# CN (default: server-address)" >> $file
	echo "#hostname = $serv_addr" >> $file
	echo
	ok "Created config file '$file'"
}


# Already installed?
if [ -d $base ]; then
	fail "Directory $base already exists!"
	exit
fi

exec_cmd mkdir $base
exec_cmd mkdir $base/accounts
exec_cmd cp -r res $base/res
create_config_file $base/config.txt
exec_cmd cp $serv_certfile $base/server-cert.pem



