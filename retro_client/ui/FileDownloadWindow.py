import curses
from threading import Lock

from os import getcwd  as os_getcwd
from os import listdir as os_listdir
from os import stat    as os_stat

from os.path import join    as path_join
from os.path import dirname as path_dirname
from os.path import isdir   as path_isdir


def filesize_to_string(filesize):
	# Get formatted string from filesize
	KB = 1024
	MB = KB*KB
	GB = MB*KB

	if filesize < KB:
		return str(filesize) + " b"
	elif filesize < MB:
		return str(round(filesize/KB,1)) + " Kb"
	elif filesize < GB:
		return str(round(filesize/MB, 2)) + " Mb"
	else:
		return str(round(filesize/GB, 3)) + " Gb"

"""\
DownloadFileWindow

+-------------------------------+
| Download file ...		|
+-------------------------------+
| file1  0.3Mb	2023-05-10 14:02
| file2	 932b	2022-01-23 12:32
| ...
+-------------------------------

Keys:
 UP,DOWN:  Select up/down
 ENTER:    Return selected file
 CTRL+X:   Return None
 CTRL+C:   Return None

"""

class FileDownloadWindow:

	def __init__(self, parent, lock:Lock, keys):
		"""\
		Args:
		  parent: Underlying curses window
		  lock:   Parent window lock
		  keys:   Keyboard instance (see Keyboard.py)
		"""

		self.parent = parent
		self.lock   = lock
		self.keys   = keys

		ph,pw = self.parent.getmaxyx()

		h = int(ph*0.8)
		w = pw-10
		y = int(ph/2-h/2)
		x = int(pw/2-w/2)

		self.W = curses.newwin(h, w, y, x)
		self.W.keypad(True)

		# A list of dictionaries.
		# Required keys: 'filename', 'size', 'time'
		self.files = []

		# Xpos of the three columns
		self.colx  = [0,0,0]

		self.cy = 0
		self.vy = 0


	def select_file(self, files=[]):
		"""\
		Ask user to enter save path
		Args:
		  files: A list of dictionaries.
			 Required keys: 'filename', 'size', 'time'
		Return:
		  None:   Quit
		  option: Selected file dict
		"""
		curses.curs_set(False)

		self.__set_files(files)
		self.__redraw()

		# Selected option
		opt = None

		while True:
			try:
				ch = self.W.getch()
			except KeyboardInterrupt:
				break

			if ch == self.keys['CTRL_X']:
				# Cancel
				break

			elif ch == self.keys['ENTER']:
				# Select file to download
				if self.cy in range(len(self.files)):
					opt = self.files[self.cy]
				break

			elif ch == self.keys['UP'] and self.cy > 0:
				# Scroll up
				self.cy -= 1
				self.__adjust_view()

			elif ch == self.keys['DOWN'] and\
					self.cy < len(self.files)-1:
				# Scroll down
				self.cy += 1
				self.__adjust_view()

			self.__redraw()

		return opt



	def __redraw(self):

		title = " Select file to download ..."
		self.lock.acquire()
		try:
			h,w = self.W.getmaxyx()

			self.W.clear()
			self.W.addstr(1, 1, title+' '*(w-len(title)-2),
				curses.A_REVERSE)

			self.__print_file_table(h, w, 3)

			self.W.border()
			self.W.refresh()
		finally:
			self.lock.release()


	def __print_file_table(self, h, w, y):
		# Table header
		self.W.addstr(y, self.colx[0], "Filename",  curses.A_BOLD)
		self.W.addstr(y, self.colx[1], "Size",      curses.A_BOLD)
		self.W.addstr(y, self.colx[2], "Timestamp", curses.A_BOLD)

		y += 1

		for i,file in enumerate(self.files[self.vy:]):

			if y > h-2: break
			self.__print_file(file, y, self.vy+i)
			y += 1


	def __print_file(self, file, y, index):
		# Print single line
		prefix = '  '
		attr = 0

		if index == self.cy:
			attr = curses.A_BOLD
			prefix = '> '

		self.W.addstr(y, 1, prefix, attr)
		self.W.addstr(y, self.colx[0], file['filename'], attr)

		self.W.addstr(y, self.colx[1],
				filesize_to_string(file['size']),
				curses.A_DIM|attr)

		self.W.addstr(y, self.colx[2], file['time'],
				curses.A_DIM|attr)


	def __adjust_view(self):
		h,w = self.W.getmaxyx()
		if self.cy < self.vy:
			self.vy = self.cy
		elif self.cy > self.vy+h-5:
			self.vy += 1


	def __set_files(self, files):

		self.cy    = 0
		self.vy    = 0
		self.files = files
		maxs       = [0,0,0]

		for file in self.files:
			n = len(file['filename'])
			if n > maxs[0]: maxs[0] = n

			n = len(filesize_to_string(file['size']))
			if n > maxs[1]: maxs[1] = n

			n = len(file['time'])
			if n > maxs[2]: maxs[2] = n

		# Set X position of all three columns
		self.colx = [
			3,
			3 + maxs[0] + 2,
			3 + maxs[0] + 2 + maxs[1] + 3
		]


