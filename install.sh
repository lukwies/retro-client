#!/bin/bash
# ___ ___ ___ ___ ____
# |_/ |_   |  |_/ |  |
# | \ |___ |  | \ |__| INSTALLER
#
# Creates the basic retro client directory tree.
#
# ~/.retro/
#    |__ accounts/
#    |__ bots/
#    |__ config.txt
#    |__ res/
#        |__ help/
#            |__ chat.txt
#            |__ main.txt
#
# Usage: ./install.sh (BASEDIR)
#

default_server_addr="127.0.0.1"
default_server_port=8443
default_file_server_port=8444
default_audio_server_port=8445
default_server_hostname="example.org"


# If an argument is given, handle it as the base
# directory path, otherwise use ~/.retro.
if [ "$1" ]; then
	base=$1
else
	base=$HOME/.retro
fi

# Loggin functions
function info() { echo -e "[\033[32minfo\033[0m]" $@; }
function ok()   { echo -e "[ \033[32mok\033[0m ]" $@; }
function fail() { echo -e "[\033[31mfail\033[0m]" $@; }
function warn() { echo -e "[\033[33mwarn\033[0m]" $@; }


function exec_cmd() {
	# Executes given command and prints a success or
	# error message. Terminates if failed to run cmd.
	if $@ > /dev/null 2>&1; then ok "$@"
	else fail "$@"; exit; fi
}

function check_create_dir() {
	# If given directory ($1) exists print a warning,
	# otherwise create that directory.
	dirpath=$1
	if [ -d $1 ]; then
		warn "Directory $1 already exists"
	else exec_cmd mkdir $1; fi
}

function create_config_file() {
	# Create the config file at ~/.retro/config.txt

	file=$1

	if [ -f $file ]; then
		warn "File $file exists"
		return
	fi

	echo "# This is the base configuration file of the retro client." > $file
	echo "# Adjust these values that they fit your personal needs." >> $file
	echo >> $file
	echo "[default]" >> $file
	echo "# Supported loglevels are ERROR,WARN,INFO,DEBUG" >> $file
	echo "loglevel = INFO" >> $file
	echo "# Logfile" >> $file
	echo "#logfile = $base/log.txt" >> $file
	echo "# Receive timeout in seconds" >> $file
	echo "#recv_timeout = 5" >> $file
	echo >> $file
	echo "[server]" >> $file
	echo "# Retro server address" >> $file
	echo "address = $default_server_addr" >> $file
	echo "# Retro server port" >> $file
	echo "port = $serv_port" >> $file
	echo "# Port for file transferring" >> $file
	echo "fileport = $default_file_server_port" >> $file
	echo "# Port for audio calls (still experimental)" >> $file
	echo "audioport = $default_audio_server_port" >> $file
	echo "# Server x509 certificate file" >> $file
	echo "certificate = $base/server-cert.pem" >> $file
	echo "# CN / server hostname" >> $file
	echo "#hostname = $default_server_hostname" >> $file
	ok "Created config file '$file'"
}



# Install ...
echo
info "Installing retro-client ..."
check_create_dir $base
check_create_dir $base/accounts
check_create_dir $base/bots

if [ -d $base/res ]; then warn "Directory $base/res exists"
else exec_cmd cp -r res $base/res; fi

create_config_file $base/config.txt


echo
echo -e "Please adjust the config file \033[1;33m~/.retro/config.txt\033[0m"
echo -e "to your personal needs!"
echo
echo -e "Note that there must be a valid server certificate stored"
echo -e "at \033[1;33m~/.retro/server-cert.pem\033[0m or at the path defined in"
echo -e "the config file as '\033[1;33mcertificate\033[0m'."
echo
