import curses
from threading import Lock

from os import getcwd  as os_getcwd
from os import listdir as os_listdir
from os import stat    as os_stat

from os.path import join    as path_join
from os.path import dirname as path_dirname
from os.path import isdir   as path_isdir


"""\
SelectOptionWindow.

+-------------------------------+
| Headline			|
+-------------------------------+
| [ ] Chat messages
| [ ] File message
| [x] Incomoing calls
| [ ] Friend online
| [ ] Friend offline
+-------------------------------

Keys:
 UP,DOWN:  Select up/down
 ENTER:    Return selected option
 CTRL+X:   Return None
 CTRL+C:   Return None

"""

class SelectOptionWindow:

	def __init__(self, parent, lock:Lock, keys,
			title="Select option",
			options=[]):
		"""\
		Args:
		  parent: Underlying curses window
		  lock: Parent window lock
		"""

		self.parent = parent
		self.lock   = lock
		self.keys   = keys
		self.title  = title
		self.opts   = options

		ph,pw = self.parent.getmaxyx()

		h = int(ph/1.5)
		w = int(pw/1.5)
		y = int(ph/2-h/2)
		x = int(pw/2-w/2)

		self.W = curses.newwin(h, w, y, x)
		self.W.keypad(True)

		self.cy = 0
		self.vy = 0


	def select_option(self):
		"""\
		Ask user to enter save path
		Args:
		  options: List with options (strings)
		Return:
		  None: Quit
		  option: Selected option
		"""
		self.cy = self.vy = 0
		self.__redraw()

		# Selected option
		opt = None

		while True:
			try:
				ch = self.W.getch()
			except KeyboardInterrupt:
				break

			if ch == self.keys['CTRL_X']:
				break

			elif ch == self.keys['ENTER']:
				if self.cy in range(len(self.opts)):
					opt = self.opts[self.cy]
				break

			elif ch == self.keys['UP'] and self.cy > 0:
				# Scroll up
				self.cy -= 1
				self.__adjust_view()

			elif ch == self.keys['DOWN'] and\
					self.cy < len(self.opts)-1:
				# Scroll down
				self.cy += 1
				self.__adjust_view()

			self.__redraw()

		return opt



	def __redraw(self):

		self.lock.acquire()
		try:
			h,w = self.W.getmaxyx()

			self.W.clear()
			self.W.addstr(1, 1, ' '+self.title+' '*(w-len(self.title)-2),
				curses.A_REVERSE)

			for y,o in enumerate(self.opts[self.vy:]):
				if y > h-4: break

				self.__print_option(o, y+3, self.vy+y)

			self.W.addstr(h-2, 2, "Press [CTRL+X] to quit",
					curses.A_DIM)
			self.W.border()
			self.W.refresh()
		finally:
			self.lock.release()


	def __print_option(self, opt, y, index):
		prefix = '  '
		attr = 0
		if index == self.cy:
			attr = curses.A_BOLD
			prefix = '> '
		self.W.addstr(y, 1, prefix + opt, attr)


	def __adjust_view(self):
		h,w = self.W.getmaxyx()
		if self.cy < self.vy:
			self.vy = self.cy
		elif self.cy > self.vy+h-5:
			self.vy += 1


	def __del__(self):
		"""\
		Make sure window is deleted properly.
		"""
		del self.W
