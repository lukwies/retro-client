"""\
 ___ ___ ___ ___ ____
 |_/ |_   |  |_/ |  |
 | \ |___ |  | \ |__|

"""

import curses
import threading
import logging

from time    import sleep    as time_sleep
from os      import listdir  as os_listdir
from os.path import join     as path_join
from os.path import basename as path_basename
from shutil  import copyfile as shutil_copyfile
from time    import sleep    as time_sleep

from libretro.protocol import *
from libretro.RetroClient import *
from libretro.Account import get_all_accounts

from . ui.Keyboard         import Keyboard
from . ui.TextWindow       import TextWindow
from . ui.FileBrowseWindow import FileBrowseWindow
from . ui.EntryBoxWindow   import EntryBoxWindow
from . ui.SelectOptionWindow import *

#from . MenuWindow      import MenuWindow
from . UiConfig        import UiConfig
from . FriendsWindow   import FriendsWindow
from . MainView        import MainView
from . ChatView        import *
from . RecvThread      import RecvThread
from . AudioCall       import AudioCall
from . AudioCallWindow import AudioCallWindow
from . AudioPlayer     import AudioPlayer
from . EventNotifier   import EventNotifier
from . SettingsWindow  import SettingsWindow

"""\
+-----------------------------------------------+
| top						|
+---------------+-------------------------------+
| left		| main				|
|		|				|
|		|				|
|		|				|
|		|				|
|		|-------------------------------|
|		| main2				|
|		|				|
+-----------------------------------------------+
| call						|
+-----------------------------------------------+
| log						|
+-----------------------------------------------+
"""

RETRO_CLIENT_VERSION = "0.1.1"
RETRO_CLIENT_RELEASE = "retro-"+RETRO_CLIENT_VERSION+" (2023)"


LOG = logging.getLogger(__name__)

class RetroGui:
	"""\
	Main class of the retro-client program.
	"""
	def __init__(self):
		"""\
		Init RetroGui.
		"""
		self.W_LEFT_W  = 26	# Width of left window
		self.W_MAIN2_H = 6	# Height of "main2" window

		self.cli        = RetroClient() # RetroClient context
		self.conf       = self.cli.conf	# Config
		self.username   = ""		# Username
		self.userid     = ""		# User ID
		self.connected  = False		# Are we connected ?
		self.recvThread = None		# Receive thread

		self.uiconf  = UiConfig(self.conf) # UI Configs
		self.stdscr  = None		# Curses std screen
		self.W       = {}		# All curses windows
		self.winLock = threading.Lock() # Window lock
		self.colors  = {} 		# Ui colors
		self.keys    = Keyboard()	# Keyboard keys/shortcuts

		self.sidebar         = None	# Sidebar
		self.mainView        = None	# Mainview
		self.chatView        = None	# Chatview
		self.audioCallWindow = None	# Window for audio calls

		self.audioCall    = None	# Audiocall handler
		self.audioPlayer  = AudioPlayer(self)	# Audio player
		self.evNotifier   = EventNotifier(self)	# Event notifier


	def load(self, username, password):
		"""\
		Loads retro account from ~/.retro/accounts/<username>
		and all other required directories and files...
		The follwing pathes are readed:

		  ~/.retro/config.txt
		  ~/.retro/server-cert.pem
		  ~/.retro/accounts/<username>/*
		  ~/.retro/res/ui.conf
		  ~/.retro/res/keyboard.json
		  ~/.retro/res/sounds/*

		Return:
		  True:  All files loaded
		  False: Failed to load files
		"""
		try:
			# Load base configs and account
			self.cli.load(username, password)
			self.username = self.cli.account.name
			self.userid   = self.cli.account.id

			# Load UI settings
			self.uiconf.load()

			# Load keyboard keys and shortcuts
			kbpath = self.uiconf.res_path('keyboard.json')
			self.keys.load_config(kbpath)
			self.audioPlayer.load_sound_files()
			return True

		except Exception as e:
			LOG.error(str(e))
			return False


	def run(self):
		"""\
		Mainloop of retro-client.
		"""
		# Setup everything
		self.__setup()

		self.redraw(resize=True)
		UnseenMsgCounter(self).start()
		self.__connect()

		while True:

			try:
				ch = self.sidebar.getch()
			except KeyboardInterrupt:
				if not self.audioCall.closed():
					self.error("Please finish "\
						"your call first")
					continue
				else: break

			if ch == self.keys['ENTER']:
				# User pressed <Enter>, open chat with
				# selected friend.
				friend = self.sidebar.get_selected()
				if friend != None:
					# Open chatview
					self.__open_chat(friend)

			elif ch == self.keys['CTRL_G']:
				# Show settings
				w = SettingsWindow(self)
				w.show()
				self.set_view_changed()

			elif ch == self.keys['CTRL_F']:
				# Add a new friend
				self.__add_friend()

			elif ch == self.keys['CTRL_D']:
				# Delete friend
				self.__delete_friend()

			elif ch == self.keys['CTRL_R']:
				# Reconnect to server
				self.__connect()

			elif ch == self.keys['CTRL_X']:
				# Quit retrochat
				if not self.audioCall.closed():
					self.error("Please finish "\
						"your call first")
				else: break

			elif ch == self.keys['CTRL_H']:
				# Show help
				self.__help()

			elif ch == self.keys['PUP']:
				# Scroll log messages up
				self.mainView.scroll_up()

			elif ch == self.keys['PDOWN']:
				# Scroll log messages down
				self.mainView.scroll_down()

			elif ch == self.keys['CTRL_O']:
				# Reject, stop, hangup audio call
				self.audioCallWindow.handle_event(ch)

			elif ch == self.keys['CTRL_P']:
				# If there's an active call let the audio
				# window handle the event, otherwise start
				# a call to selected friend.
				if not self.audioCall.closed():
					self.audioCallWindow.handle_event(ch)
				else:
					friend = self.sidebar.get_selected()
					if friend:
						self.start_call(friend)

			elif ch == curses.KEY_RESIZE:
				# Resize window
				self.resize()
			else:
				# Sidebar event (up/down/enter/..)
				self.sidebar.handle_event(ch)

			self.redraw()


		# Quitting ...
		if self.connected:
			self.cli.send_packet(Proto.T_GOODBYE)

			self.info("Waiting for recv thread to finish ...")
			if self.recvThread:
				self.cli.close()
				self.recvThread.done = True
				self.recvThread.join()

		curses.endwin()


	def redraw(self, force=False, resize=False):
		"""\
		Redraw screen depending on the current view.
		The topwindow and audiowindow are printed
		independently from the current view.

		Args:
		  force:  Force redraw ? This will set all
			  windows to changed before drawing.
		  resize: Resize the view before drawing?
		"""
		if resize:
			self.resize()

		self.print_topwin()

		if self.chatView:
			self.chatView.redraw(force)
		else:
			self.sidebar.redraw(force)
			self.mainView.redraw(force)
			self.audioCallWindow.redraw(force)


	def log_msg(self, text, error=False, show_sec=2):
		"""\
		Write message to self.W['log'].
		"""
		log = LogMsgThread(self, text, error, show_sec)
		log.start()


	def clear_win(self, win_name):
		"""\
		Clear and refresh window with given name.
		"""
		with self.winLock:
			if win_name in self.W:
				self.W[win_name].clear()
				self.W[win_name].refresh()


	def print_topwin(self):
		"""\
		Draws the top window.
		This is also used by the ChatView..
		"""
		left   = "User: " + self.cli.account.name
		center = RETRO_CLIENT_RELEASE
		right  = "online " if self.connected else "offline "

		with self.winLock:
			win = self.W['top']
			win.clear()
			_,w = win.getmaxyx()

			try:
				win.addstr(0, 1, left, curses.A_BOLD)
				win.addstr(0, int(w/2-len(center)/2), center)

				if self.connected:
					rcol = self.colors['gb']|curses.A_BOLD
				else:	rcol = self.colors['rb']|curses.A_BOLD

				win.addstr(0, w-len(right)-1, right, rcol)
			except:
				# Screen too small
				pass
			win.refresh()


	def info(self, text, redraw=True, on_logwin=False):
		self.mainView.add_msg(logging.INFO, text, redraw)
		if on_logwin and self.chatView:
			self.log_msg(text, error=False)

	def error(self, text, redraw=True, on_logwin=False):
		self.mainView.add_msg(logging.ERROR, text, redraw)
		if on_logwin and self.chatView:
			self.log_msg(text, error=True)

	def warn(self, text, redraw=True):
		self.mainView.add_msg(logging.WARNING, text, redraw)

	def debug(self, text, redraw=True):
		self.mainView.add_msg(logging.DEBUG, text, redraw)


	def resize(self):
		"""\
		Resize all window instances depending on the
		current view. This is the only function resizing
		the screen and can be called from everywhere.
		"""

		h,w = self.stdscr.getmaxyx()

		# Is there an audiocall currently?
		# If there's an active audiocall we show the
		# AudioCallWindow and need to eventually
		# adjust the sidebar, main or main2 windows.
		is_call = not self.audioCall.closed()

		if self.chatView:
			# The chatview has no sidebar but two
			# main windows (main,main2) placed on
			# top of each other.
			left_w  = 0
			main_h  = h-2-self.W_MAIN2_H
			main_w  = w
			main_x  = 0
			main2_h = self.W_MAIN2_H
			main2_y = h-1-self.W_MAIN2_H
		else:
			# The default view has a sidebar on the
			# left and the main window on the right
			# side of the screen.
			left_w  = self.W_LEFT_W
			main_h  = h-2
			main_w  = w - left_w
			main_x  = left_w
			main2_h = 0
			main2_y = 0

		if is_call:
			# If audioCallWindow is open, the main-
			# height is 4 lines smaller.
			main_h  -= 4
			main2_y -= 4


		self.winLock.acquire()
		try:
			[win.clear() for win in self.W.values()]

			self.W['top'].resize(1, w)
			self.W['top'].mvwin(0, 0)

			if not self.chatView:
				self.W['left'].resize(main_h, left_w)
				self.W['left'].mvwin(1, 0)

			self.W['main'].resize(main_h, main_w)
			self.W['main'].mvwin(1, main_x)

			if self.chatView:
				self.W['main2'].resize(main2_h, main_w)
				self.W['main2'].mvwin(main2_y, main_x)

			if is_call:
				self.W['call'].resize(4, w)
				self.W['call'].mvwin(h-5, 0)

			self.W['log'].resize(1, w)
			self.W['log'].mvwin(h-1, 0)

			[win.refresh() for win in self.W.values()]
		except:
			# Window too small...
			pass
		finally:
			self.winLock.release()

		self.set_view_changed()


	def start_call(self, friend):
		"""\
		Start a call with given friend.
		"""

		# Can only call friends that are online
		if friend.status != Friend.ONLINE:
			self.log_msg(friend.name+" is offline!",
				error=True)
			return

		# Let user confirm before starting call
		dia = DialogWindow(self.stdscr,
				self.winLock, self.keys,
				"Start Audiocall ...",
				"Do you really want to call "\
				"your friend "+friend.name+"?",
				['no', 'yes'], 'yes')
		res = dia.show()
		self.set_view_changed()

		# Start audiocall if user selected 'yes'
		if res == 'yes':
			self.audioCall.start_call(friend)


	def set_view_changed(self):
		"""\
		Update all views that they will be printed
		to screen if any redraw() method is called.
		"""
		self.mainView.changed = True
		self.sidebar.changed  = True
		if self.chatView:
			self.chatView.wMsg.changed = True
			self.print_topwin()

	#-- PRIVATE --------------------------------------------------

	def __connect(self):
		"""\
		Connect to retro server.
		"""
		if self.connected:
			self.log_msg("You are already connected", error=True)
			return

		self.info("Connecting to " +
			self.cli.get_hoststr() + " ...")
		try:
			self.cli.connect()
			self.connected = True
			self.info("We are connected :-)")
			#self.debug("SSL: ".format(self.cli.conn.cipher()))
		except Exception as e:
			self.error(str(e))
			self.connected = False

		# Redraw topwin to see connection status
		self.print_topwin()

		if self.connected:

			# Send all friends to server to keep track of their
			# status (online/offline)
			friend_ids = list(self.cli.account.friends.keys())
			if friend_ids:
				self.cli.send_packet(Proto.T_FRIENDS,
					b''.join(friend_ids))

			# Start receive thread
			self.recvThread = RecvThread(self)
			self.recvThread.start()


	def __open_chat(self, friend):
		# Open conversation with given friend.
		if friend.status == Friend.UNKNOWN:
			self.error("Can't open chat with "\
				"unknown user '{}'"\
				.format(friend.name))
			return

		# Open and run chatview loop
		self.chatView = ChatView(self)
		if self.chatView.load_chat(friend):
			self.chatView.loop()
		self.chatView = None

		# Resize/redraw everything
		self.redraw(force=True, resize=True)


	def __help(self):
		# Open help window
		path = path_join(self.uiconf.helpdir, "main.txt")
		help = TextWindow(self.stdscr, self.winLock,
				self.keys, title="Mainview Help")
		if not help.read_textfile(path):
			self.error("Failed to open helpfile '"+path+"'")
		else:
			help.show()
			self.set_view_changed()


	def __add_friend(self):
		# Add a new friend current account.
		# Let user enter the new friends name and userid.
		# Send T_GET_PUBKEY to server and let the recvThread
		# deal with the response..

		if not self.connected:
			self.log_msg("Not connected", error=True)
			return

		# Let user enter new friend's name
		entryBox = EntryBoxWindow(self.stdscr,
				self.winLock, self.keys,
				"Enter name of friend")
		username = entryBox.get_input()
		self.set_view_changed()

		if not username: return

		# Let user enter new friend's userid
		entryBox = EntryBoxWindow(self.stdscr,
				self.winLock, self.keys,
				"Enter userid of friend")
		useridx = entryBox.get_input()
		self.set_view_changed()

		try:
			# Validate userinput and convert it
			# to userid (8 byte)
			userid = Proto.hexstr_to_userid(useridx)
		except Exception as e:
			self.error(str(e))
			return

		# Tell receive thread the friend's name that he
		# knows it when receiving the response..
		self.recvThread.add_info('friendname', username)

		# Send T_GET_PUBKEY request
		self.cli.send_packet(Proto.T_GET_PUBKEY, userid)


	def __delete_friend(self):
		# Delete selected friend from account.

		friend = self.sidebar.get_selected()
		if not friend: return

		# Let user confirm before deleting friend
		dia = DialogWindow(self.stdscr,
			self.winLock, self.keys,
			"Delete friend {}?".format(friend.name),
			"Delete your friend "+friend.name+" and "\
			"all your conversations? This cannot be "\
			"undone!", ['no', 'yes'], 'no')
		res = dia.show()
		self.set_view_changed()

		if res == 'yes':
			self.cli.account.delete_friend(friend.id)
			self.sidebar.reset_friends()
			self.info("Deleted your friend "+friend.name)
			self.redraw(force=True)


	def __setup(self):
		"""\
		Setup curses, all the colors (self.colors), all the
		windows (self.W) and all the views.
		"""
		self.stdscr = curses.initscr()

		curses.curs_set(False)
		curses.noecho()
		curses.start_color()

		# We create a dictionary for colors (self.colors)
		# where the keys are abbreviations of the colors
		# and the values are the curses attribute ids.
		# Keys can have or two characters, first is the
		# foreground and second the background.
		# For example to get the color blue we then can
		# just do self.colors['b'] and for red with a
		# blue background self.colors['rb'].

		# curses colors go from 0=black to 7=white
		# 1=red, 2=green, 3=yellow, 4=blue, 5=magenata
		# 6=cyan

		def init_color(name, id, fg, bg):
			# Init color pair and store the curses id
			# to color dict (self.colors).
			curses.init_pair(id, fg, bg)
			self.colors[name] = curses.color_pair(id)

		# Init base colors red - cyan
		names = 'rgybmc'
		for i,name in enumerate(names):
			init_color(name, i+1, i+1,
					curses.COLOR_BLACK)

		# Init colors with blue background
		init_color('rb', 8,  curses.COLOR_RED, curses.COLOR_BLUE)
		init_color('gb', 9,  curses.COLOR_GREEN, curses.COLOR_BLUE)
		init_color('yb', 10, curses.COLOR_BLUE, curses.COLOR_BLUE)
		init_color('mb', 11, curses.COLOR_YELLOW, curses.COLOR_BLUE)
		init_color('Wb', 12, curses.COLOR_WHITE, curses.COLOR_BLUE)
		init_color('Bb', 13, curses.COLOR_BLACK, curses.COLOR_BLUE)
		init_color('Wr', 14, curses.COLOR_WHITE, curses.COLOR_RED)
		init_color('BW', 15, curses.COLOR_BLACK, curses.COLOR_WHITE)


		h,w = self.stdscr.getmaxyx()
		[w.clear() for w in self.W.values()]

		# All windows are stored in a dict
		self.W = {}
		# The topwindow shows the useraccount name, retro version
		# and the current connection status (online/offline).
		self.W['top'] = curses.newwin(1, w, 0, 0)
		self.W['top'].bkgdset(self.colors['Wb'])

		# This window holds the sidebar (FriendsWindow). It shows
		# all friends of current account and let the user interact
		# with it (select friends, ...).
		self.W['left'] = curses.newwin(h-2, self.W_LEFT_W, 1, 0)
		self.W['left'].keypad(True)

		# The main window may either hold the MainView or ChatView,
		# depending on the current ui state.
		self.W['main'] = curses.newwin(h-2-self.W_MAIN2_H, w-self.W_LEFT_W,
					1, self.W_LEFT_W)

		# Window main2 holds a text input window if the ChatView
		# has been opened. In the MainView it won't be shown.
		self.W['main2'] = curses.newwin(self.W_MAIN2_H, w-self.W_LEFT_W,
					h-2-self.W_MAIN2_H, self.W_LEFT_W)
		self.W['main2'].keypad(True)

		# The call window appears at the bottom part of the screen
		# if there's an active call (!this.audioCall.closed()).
		self.W['call'] = curses.newwin(0,0,0,0)
		self.W['call'].keypad(True)

		# Bottom window for showing log messages. This window has a
		# blue background by default which may become while printing
		# error messages.
		self.W['log'] = curses.newwin(1, w, h-1, 0)
		self.W['log'].bkgdset(self.colors['Wb'])

		[w.refresh() for w in self.W.values()]

		# Init curses dependent view and window instances.
		self.sidebar         = FriendsWindow(self)
		self.mainView        = MainView(self)
		self.audioCall       = AudioCall(self)
		self.audioCallWindow = AudioCallWindow(self)
#		self.audioPlayer     = AudioPlayer(self)


class UnseenMsgCounter(threading.Thread):
	"""\
	This threads counts the number of unseen messages for
	each friend and stores them at friend.unseen_msgs.
	After execution, the sidebar will be redrawn.
	"""
	def __init__(self, gui):
		super().__init__()
		self.gui = gui
		self.friends = gui.cli.account.friends

	def run(self):
		for fr in self.friends.keys():
			n = self.gui.cli.msgStore.get_num_unseen(self.friends[fr])
			self.friends[fr].unseen_msgs = n
		self.gui.sidebar.changed = True
		if not self.gui.chatView:
			self.gui.sidebar.redraw()
			self.gui.sidebar.changed = True


class LogMsgThread(threading.Thread):
	"""\
	Print a logging message with timeout.
	"""
	def __init__(self, gui, msg, is_error=False,
			show_sec=3):
		super().__init__()
		self.gui = gui		# RetroGui
		self.msg = msg		# Text
		self.err = is_error	# Is error?
		self.sec = show_sec	# Seconds to show

	def run(self):
		win = self.gui.W['log']

		self.__print_msg(win)
		time_sleep(self.sec)
		self.__clear(win)

		if self.gui.chatView:
			self.gui.chatView.reset_cursor()

	def __print_msg(self, win):
		with self.gui.winLock:
			_,w = win.getmaxyx()
			win.clear()

			if self.err:
				win.bkgd(' ', self.gui.colors['Wr'])
			else:	win.bkgd(' ', self.gui.colors['Wb'])

			win.addstr(0, 1, self.msg[:w-2], curses.A_BOLD)
			win.refresh()

	def __clear(self, win):
		with self.gui.winLock:
			win.clear()
			win.bkgd(' ', self.gui.colors['Wb'])
			win.refresh()
