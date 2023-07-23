import curses
from threading import Lock

from os import getcwd  as os_getcwd
from os import listdir as os_listdir
from os import stat    as os_stat

from os.path import join    as path_join
from os.path import dirname as path_dirname
from os.path import isdir   as path_isdir


"""\
A window for showing retro client settings
and user change audio and notification configs.
A window showing all settings.
"""

class SettingsWindow:

	VIEW_DEFAULT_SETTINGS=0
	VIEW_SOUND_SETTINGS=1
	VIEW_NOTIFY_SETTINGS=2

	def __init__(self, gui):
		"""\
		Args:
		  gui: RetroGuiInstance
		"""

		self.gui    = gui
		self.acc    = gui.cli.account
		self.conf   = gui.conf
		self.uiconf = gui.uiconf
		self.view   = self.VIEW_DEFAULT_SETTINGS
		self.titles = ['Configs', 'Sounds', 'Notifications']

		# A list default options, tuples (opt,value)
		self.defopts = []
		self.defopts.append(("Username", self.acc.name))
		self.defopts.append(("UserId", self.acc.id.hex()))

		for k,v in self.conf.__dict__.items():
			self.defopts.append((
				k.replace('_', ' ').title(), v))
		self.max_opt = max([len(x[0]) for x in self.defopts])

		# List with all sound options
		self.sndopts = [
			("Receive chat message", "recv-message"),
			("Receive file message", "recv-filemessage"),
			("Sent chat message", "sent-message"),
			("Sent file message", "sent-filemessage"),
			("Incoming call", "incoming-call"),
			("Outgoing call", "outgoing-call"),
			("Friend is online", "friend-online"),
			("Friend is offline", "friend-offline")
		]

		# List with all notify options
		self.notifyopts = [
			("Receive chat message", "recv-message"),
			("Receive file message", "recv-filemessage"),
			("Incoming call", "incoming-call"),
			("Friend is online", "friend-online"),
			("Friend is offline", "friend-offline")
		]

		ph,pw = self.gui.stdscr.getmaxyx()
		self.W = curses.newwin(ph-2, pw, 1, 0)
		self.W.keypad(True)

		self.cy = 0


	def show(self):
		"""\
		Show settings window.
		"""
		self.cy = self.vy = 0
		self.__redraw()

		while True:
			try:
				ch = self.W.getch()
			except KeyboardInterrupt:
				break

			if ch == self.gui.keys['CTRL_X']:
				break

			elif ch == self.gui.keys['ENTER']:
				# Change settings
				if self.view == self.VIEW_SOUND_SETTINGS:
					name = self.sndopts[self.cy][1]
					self.uiconf.set_sound_enabled(name, None)
				elif self.view == self.VIEW_NOTIFY_SETTINGS:
					name = self.notifyopts[self.cy][1]
					self.uiconf.set_notify_enabled(name, None)

			# Select previous/next option
			elif ch == self.gui.keys['UP'] and self.cy > 0:
				self.cy -= 1
			elif ch == self.gui.keys['DOWN']:
				if self.view == self.VIEW_DEFAULT_SETTINGS\
					and self.cy < len(self.defopts)-1:
					self.cy += 1
				elif self.view == self.VIEW_SOUND_SETTINGS\
					and self.cy < len(self.sndopts)-1:
					self.cy += 1
				elif self.view == self.VIEW_NOTIFY_SETTINGS\
					and self.cy < len(self.notifyopts)-1:
					self.cy += 1

			# Switch between views
			elif ch == self.gui.keys['RIGHT']:
				self.view = (self.view+1)%3
				self.cy   = 0
			elif ch == self.gui.keys['LEFT']:
				self.view = (self.view-1)%3
				self.cy   = 0

			self.__redraw()


	def __redraw(self):
		if self.view == self.VIEW_SOUND_SETTINGS:
			self.__redraw_sound_settings()
		elif self.view == self.VIEW_NOTIFY_SETTINGS:
			self.__redraw_notify_settings()
		else:	self.__redraw_default_settings()


	def __redraw_default_settings(self):
		with self.gui.winLock:
			h,w = self.W.getmaxyx()
			self.W.clear()
			self.__print_title(w)

			for y,o in enumerate(self.defopts[self.vy:]):
				if y > h-4: break
				self.__print_default_option(o, y+3, self.vy+y)

			self.W.addstr(h-2, 2, "Press [CTRL+X] to quit",
					curses.A_DIM)
			self.W.border()
			self.W.refresh()


	def __redraw_sound_settings(self):
		with self.gui.winLock:
			h,w = self.W.getmaxyx()
			self.W.clear()
			self.__print_title(w)

			for y,o in enumerate(self.sndopts):
				if y > h-4: break
				self.__print_sound_option(o, y+3, y)

			self.W.addstr(h-2, 2, "Press [CTRL+X] to quit",
					curses.A_DIM)
			self.W.border()
			self.W.refresh()

	def __redraw_notify_settings(self):
		with self.gui.winLock:
			h,w = self.W.getmaxyx()
			self.W.clear()
			self.__print_title(w)

			for y,o in enumerate(self.notifyopts):
				if y > h-4: break
				self.__print_notify_option(o, y+3, y)

			self.W.addstr(h-2, 2, "Press [CTRL+X] to quit",
					curses.A_DIM)
			self.W.border()
			self.W.refresh()


	def __print_default_option(self, opt, y, index):
		prefix = '  '
		attr = 0
		if index == self.cy:
			attr = curses.A_BOLD
			prefix = '> '
		self.W.addstr(y, 2, opt[0], curses.A_BOLD)
		self.W.addstr(y, 4+self.max_opt, str(opt[1]))

	def __print_sound_option(self, opt, y, index):
		attr = curses.A_DIM
		is_enabled = self.uiconf.is_sound_enabled(opt[1])

		if index == self.cy:
			attr = curses.A_BOLD

		if is_enabled:
			self.W.addch(y, 2, "[")
			self.W.addch("X", self.gui.colors['g']|attr)
			self.W.addstr("] ")
		else:	self.W.addstr(y, 2, "[ ] ", attr)

		self.W.addstr(opt[0], attr)


	def __print_notify_option(self, opt, y, index):
		attr = curses.A_DIM
		is_enabled = self.uiconf.is_notify_enabled(opt[1])

		if index == self.cy:
			attr = curses.A_BOLD

		if is_enabled:
			self.W.addch(y, 2, "[")
			self.W.addch("X", self.gui.colors['g']|attr)
			self.W.addstr("] ")
		else:	self.W.addstr(y, 2, "[ ] ", attr)

		self.W.addstr(opt[0], attr)


	def __print_title(self, w):
		"""\
		Print the titles
		"""
		attr = curses.A_REVERSE
		s = " | ".join(self.titles)
		self.W.addch(1, 1, ' ', attr)

		for i,title in enumerate(self.titles):
			if i == self.view:
				self.W.addstr("["+title+"]", attr)
			else:	self.W.addstr(title, attr|curses.A_BOLD)

			if i < len(self.titles)-1:
				self.W.addstr(" | ", attr|curses.A_BOLD)
		self.W.addstr(" "*(w-len(s)-3), attr)


	def __del__(self):
		"""\
		Make sure window is deleted properly.
		"""
		del self.W

