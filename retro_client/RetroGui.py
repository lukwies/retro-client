"""
 ___ ___ ___ ___ ____
 |_/ |_   |  |_/ |  |
 | \ |___ |  | \ |__|

"""

import curses
import threading
import logging as LOG

from time    import sleep    as time_sleep
from os      import listdir  as os_listdir
from os.path import join     as path_join
from os.path import basename as path_basename
from shutil  import copyfile as shutil_copyfile
from time    import sleep    as time_sleep

from libretro.RetroClient import *
from libretro.Account import get_all_accounts

from . ui.Keyboard         import Keyboard
from . ui.TextWindow       import TextWindow
from . ui.FileBrowseWindow import FileBrowseWindow
from . ui.EntryBoxWindow   import EntryBoxWindow
from . ui.SelectOptionWindow import *

from . FriendsWindow import FriendsWindow
from . ChatView      import *
from . MainView      import MainView
from . RecvThread    import RecvThread
from . FileTransfer  import *


"""
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
| log						|
+-----------------------------------------------+
"""


class RetroGui:

	def __init__(self, client):
		"""\
		Args:
		  client: RetroClient (MUST be loaded!!)
		"""

		self.W_LEFT_W  = 26	# Width of left window
		self.W_MAIN2_H = 6	# Height of "main2" window

		self.cli        = client # RetroClient context
		self.conf       = client.conf # Config
		self.resdir     = path_join(self.conf.basedir, "res")
		self.username   = self.cli.account.name	# Username
		self.connected  = False	# Are we connected ?
		self.recvThread = None	# Receive thread, initialized if connected.
		self.winLock    = threading.Lock() # Window lock
		self.colors     = {} # Curses colors dict (see self.__setup())
		self.keys       = Keyboard() # All keyboard keys/shortcuts
		self.stdscr     = curses.initscr()

		h,w = self.stdscr.getmaxyx()
		# All windows are stored in a dict
		self.W = {}
		self.W['top']  = curses.newwin(1, w, 0, 0)
		self.W['left'] = curses.newwin(h-2, self.W_LEFT_W, 1, 0)
		self.W['main'] = curses.newwin(h-2-self.W_MAIN2_H, w-self.W_LEFT_W,
					1, self.W_LEFT_W)
		self.W['main2']  = curses.newwin(self.W_MAIN2_H, w-self.W_LEFT_W,
					h-2-self.W_MAIN2_H, self.W_LEFT_W)
		self.W['log']    = curses.newwin(1, w, h-1, 0)

		# curses colors (key=color, value=id)
		# Colors can be r,g,y,b,m,c,rb, ...
		self.colors = {}
		self.__setup()

		# Views (sidebar, mainview, chatview)
		# Default view is (sidebar|mainview)
		self.sidebar  = FriendsWindow(self)
		self.mainView = MainView(self)
		self.chatView = None

		# Filetransfer handler
		self.fileTransfer = FileTransfer(self)


	def run(self):
		"""
		Mainloop of retro-client.
		"""
		self.redraw(resize=True)
		UnseenMsgCounter(self).start()
		self.__connect()

		while True:

			try:
				ch = self.sidebar.getch()
			except KeyboardInterrupt:
				break

			if ch == self.keys['ENTER']:
				# User pressed <Enter>, open chat with
				# selected friend.
				friend = self.sidebar.get_selected()
				if friend != None:
					# Open chatview
					self.__open_chat(friend)

			elif ch == self.keys['CTRL_F']:
				# Add a new friend
				self.__add_friend()

			elif ch == self.keys['CTRL_A']:
				self.__change_account()

			elif ch == self.keys['CTRL_R']:
				# Reconnect to server
				self.__connect()

			elif ch == self.keys['CTRL_X']:
				# Quit retrochat
				break

			elif ch == self.keys['CTRL_H']:
				# Show help
				self.__help()

			elif ch == self.keys['PUP']:
				# Scroll log messages up
				self.mainView.scroll_up()

			elif ch == self.keys['PDOWN']:
				# Scroll log messages down
				self.mainView.scroll_down()

			elif ch == curses.KEY_RESIZE:
				# Resize window
				self.__resize()
			else:
				# Sidebar event (up/down/enter/..)
				self.sidebar.handle_event(ch)
			self.redraw()


		# Quitting ...
		self.cli.send_dict({'type':'disconnect'})
		self.info("Waiting for recv thread to finish ...")
		if self.recvThread:
			self.cli.close()
			self.recvThread.done = True
			self.recvThread.join()

		curses.endwin()


	def redraw(self, resize=False):
		"""
		Redraw default view (sidebar, mainview).
		"""
		if resize:
			self.__resize()

		self.print_topwin()
		self.sidebar.redraw()
		self.mainView.redraw()


	def log_msg(self, text, error=False):
		"""
		Write message to self.W['log'].
		"""
		log = LogMsgThread(self, text, error)
		log.start()


	def clear_win(self, win_name):
		"""
		Clear and refresh window with given name.
		"""
		self.winLock.acquire()
		try:
			if win_name in self.W:
				self.W[win_name].clear()
				self.W[win_name].refresh()
		finally:
			self.winLock.release()


	def print_topwin(self):
		"""
		Draws the top window.
		This is also used by the ChatView..
		"""
		win = self.W['top']
		_,w = win.getmaxyx()

		left   = "User: " + self.cli.account.name
		center = "retro-0.1 (2023)"
		right  = "online " if self.connected else "offline "

		self.winLock.acquire()
		try:
			win.clear()
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
		finally:
			self.winLock.release()


	def info(self, text, redraw=True, on_logwin=False):
		self.mainView.add_msg(LOG.INFO, text, redraw)
		if on_logwin and self.chatView:
			self.log_msg(text, error=False)

	def error(self, text, redraw=True, on_logwin=False):
		self.mainView.add_msg(LOG.ERROR, text, redraw)
		if on_logwin and self.chatView:
			self.log_msg(text, error=True)

	def warn(self, text, redraw=True):
		self.mainView.add_msg(LOG.WARNING, text, redraw)

	def debug(self, text, redraw=True):
		self.mainView.add_msg(LOG.DEBUG, text, redraw)

	#-- PRIVATE --------------------------------------------------

	def __connect(self):
		"""
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
			# Start receive thread
			self.recvThread = RecvThread(self)
			self.recvThread.start()

			# Send all friends to server to keep track of their
			# status (online/offline)
			friends = list(self.cli.account.friends.keys())
			self.cli.send_dict({'type' : 'friends',
				'users' : ','.join(friends)})


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
		self.redraw(resize=True)


	def __help(self):
		# Open help window
		path = path_join(self.resdir, "help/main.txt")
		help = TextWindow(self.stdscr, self.winLock,
				self.keys, title="Mainview Help")
		if not help.read_textfile(path):
			self.error("Failed to open helpfile '"+path+"'")
		else:
			help.show()
			self.mainView.changed = True
			self.sidebar.changed  = True
			self.sidebar.redraw()
		del help


	def __add_friend(self):
		# Add a new friend current account.
		# First let user enter the new friend's name,
		# then open filebrowser to let user select the friends
		# publickey filepath.

		# Read friend's name from user
		entryBox = EntryBoxWindow(self.stdscr,
				self.winLock, self.keys,
				"Enter name of friend")
		username = entryBox.get_input()
		del entryBox

		self.mainView.changed = True
		self.sidebar.changed  = True

		if not username:
			return

		# Get friend's retro key filepath
		fileBrowser = FileBrowseWindow(self.stdscr,
				self.winLock, self.keys,
				"Select {}'s retro key".format(
				username))
		userkeyfile = fileBrowser.select_file(
				allowed_ext=[".pem"])
		del fileBrowser

		if not userkeyfile:
			return

		# Add friend to account and update UI
		try:
			self.cli.account.add_friend(username,
				userkeyfile)
			self.sidebar.reset_friends()
			self.info("You have a new friend!")
		except Exception as e:
			self.error("Add friend: " + str(e))
			return


	def __resize(self):
		# Resize screen
		h,w = self.stdscr.getmaxyx()
		if h < 10 or w < 30:
			return

		self.winLock.acquire()
		try:
			[w.clear() for w in self.W.values()]

			self.W['top'].resize(1, w)
			self.W['top'].mvwin(0, 0)

			self.W['left'].resize(h-2, self.W_LEFT_W)
			self.W['left'].mvwin(1, 0)

			self.W['main'].resize(h-2, w-self.W_LEFT_W)
			self.W['main'].mvwin(1, self.W_LEFT_W)

			self.W['log'].resize(1, w)
			self.W['log'].mvwin(h-1, 0)

			[w.refresh() for w in self.W.values()]

		finally:
			self.winLock.release()

		self.mainView.changed = True
		self.sidebar.changed = True


	def __setup(self):
		# Setup colors, load keyboard keys/shortcuts.

		curses.curs_set(False)
		curses.noecho()
		curses.start_color()

		# curses colors go from 0=black to 7=white
		# 1=red, 2=green, 3=yellow, 4=blue, 5=magenata
		# 6=cyan

		def init_color(name, id, fg, bg):
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


		[w.clear() for w in self.W.values()]
		self.W['top'].bkgdset(self.colors['Wb'])
		self.W['left'].keypad(True)
		self.W['log'].bkgdset(self.colors['Wb'])
		[w.refresh() for w in self.W.values()]

		# Load keyboard keys/shortcuts
		path = path_join(self.conf.basedir, "res/keyboard.json")
		self.keys.load_json(path)



class UnseenMsgCounter(threading.Thread):
	"""
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
	"""
	Print a logging message with timeout.
	"""
	def __init__(self, gui, msg, is_error=False,
			show_sec=5):
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
