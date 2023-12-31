# retro-client
An end-to-end ecrytped messenger for terminal lovers (me and my friends <3).
**NOTE**: retro-client depends on 
<a href='https://github.com/lukwies/libretro'>libretro</a>
, so build this first!

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

 -u, --user=USER           Set username

 --init-keyboard           Ask user to type all keys required by retro
                           in an interactive curses window. These keys
                           then stored at ~/.retro/res/keyboard.json.
 --create-account=REGKEY   Create a new retro account
</pre>


## Base Directory
The retro basedirectory is located at `~/.retro` and has the following
structure:
<pre>
 ~/.retro
    |__ config.txt                    Config file
    |__ accounts/                     All accounts stored here
    |   |__ {username}/               Account dir of 'user1'
    |       |__ account.db            Account db (encrypted sqlite)
    |       |__ friends/              Friends dir
    |           |__ friends.db        Friends db (encrypted sqlite)
    |           |__ msg/              To store all conversations
    |__ bots/                         All bot accounts stored here
    |   |__ ...                       Same structure as 'accounts'
    |__ res/                          UI resources
    |   |__ keyboard.json             Keyboard keys/shortcuts settings
    |   |__ help/                     Helpfiles
    |   |   |__ main.txt              Help for mainview
    |   |   |__ chat.txt              Help for chatview
    |   |__ img/                      Images for desktop notifications
    |   |   |__ recv-message.png
    |   |   |__ friend-online.png
    |   |   |__ friend-offline.png
    |   |__ sounds/                   Sounds for events
    |   |   |__ recv-message.wav
    |   |   |__ sent-message.wav
    |   |   |__ recv-filemessage.wav
    |   |   |__ sent-filemessage.wav
    |   |   |__ friend-online.wav
    |   |   |__ friend-offline.wav
    |   |__ ui.conf                   User interface config
    |__ server-cert.pem               Server certificate
</pre>


## Config File
The retro client's config file is located at `~/.retro/config.txt`
and contains the following options:

<pre>
[default]
loglevel  = ERROR|WARN|INFO|DEBUG
logfile   = LOGFILE_PATH
recv_timeout = 5

[server]
address = 127.0.0.1
port = 8443
fileport = 8444
certificate = SERVER_CERTFILE_PATH
hostname = SERVER_HOSNAME
</pre>

## UI Config File
The userinterface config file is located at `~/.retro/res/ui.conf`
and contains the following options:
<pre>
[sounds]
recv-message = True
sent-message = True
friend-online = True
friend-offline = True

[notify]
enabled = True
timeout = 5
</pre>
