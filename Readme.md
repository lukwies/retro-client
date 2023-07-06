# Retro
An end-to-end ecrytped messenger for terminal lovers (me and my friends <3).

## Features
- Transport layer security (TLS)
- Strong end-to-end encryption (AES-256-CBC,RSA-2048-OAEP,HMAC-SHA256,ED25519)
- Encrypted file transfer (AES-256-CBC, HMAC-SHA256)
- Simple and easy to use interface (curses)
- Arbitrary message sizes
- Offline usage (limited)
- All messages are stored encrytped (server and client side)
- Server only stores messages until receiver fetched them
- Server only stores files until they are downloaded
- Server doesn't log anything (except in debugging mode)
- Server doesn't know your friend's names


## Install
Install required dependencies, and create retro base directory at `~/.retro`.
<pre>
$ pip install .
$ ./install.sh
</pre>


## Start
Before using the retro messenger, an account must be created.
<pre>
$ retro-client --create-account
</pre>
Follow the instructions and run:
<pre>
$ retro-client
</pre>


## Usage
<pre>
 Calling retro-client without any arguments the user is asked to
 select an account (if there are more than one) and the client
 interface will be started.

 Usage: retro-client [OPTIONS] ...

 -u, --user=USER	Set username

 --init-keyboard        Ask user to type all keys required by retro
			in an interactive curses window. These keys
			then stored at ~/.retro/res/keyboard.json.
 --create-account	Create a new retro account
</pre>


## Base Directory
The retro basedirectory is located at `~/.retro` and has the following
structure:
<pre>
 ~/.retro
    |__ config.txt		Config file
    |__ accounts/		All accounts stored here
    |   |__ USER1/		Account dir of 'user1'
    |       |__ key.pem		User's private key
    |       |__ USER1ID.pem	User's public key
    |       |__ friends/	To store friend keys
    |       |__ msg/		To store all conversations
    |__ res/			UI resources
    |   |__ keyboard.json	Keyboard keys/shortcuts settings
    |   |__ help/		Helpfiles
    |       |__ main.txt	Help for mainview
    |       |__ chat.txt	Help for chatview
    |__ server-cert.pem		Server certificate
</pre>


## Config File
The retro client's config file is located at `~/.retro/config.txt`
and contains the following options:

<pre>
[default]
loglevel  = ERROR|WARN|INFO|DEBUG
logformat = '%(levelname)s  %(message)s'
logfile   = LOGFILE_PATH
recv_timeout = 5

[server]
address = 127.0.0.1
port = 8443
fileport = 8444
certificate = SERVER_CERTFILE_PATH
hostname = SERVER_HOSNAME
</pre>
