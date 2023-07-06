import curses

from os import getcwd  as os_getcwd
from os import listdir as os_listdir
from os import stat    as os_stat

from os.path import join     as path_join
from os.path import dirname  as path_dirname
from os.path import isdir    as path_isdir
from os.path import splitext as path_splitext

from threading import Lock

"""
Filebrowser

+-------------------------------+
| Select a file			|
+-------------------------------+
| ../
| foo.txt
| bar
| foobar.pdf
|
+-------------------------------
"""

class FileBrowseWindow:

	def __init__(self, parent, lock:Lock, keys,
			title="Select a file ..."):
		"""
		Args:
		  parent: Underlying curses window
		  lock:   Window thread lock
		  keys:   Keyboard instance (See ncui/Keyboard.py)
		"""

		self.parent = parent
		self.lock   = lock
		self.keys   = keys
		self.title  = title

		ph,pw = self.parent.getmaxyx()

		h = int(ph/1.5)
		w = pw-10
		y = int(ph/2-h/2)
		x = int(pw/2-w/2)

		self.W = curses.newwin(h, w, y, x)
		self.W.keypad(True)

		self.dirpath = None

		# Each index holds a tuple (name,size,is_dir)
		self.filelist = []

		self.cy   = 0
		self.vy   = 0
		self.colx = [3, 4] # Column x positions


	def select_file(self, dirpath=None, allowed_ext=None):
		"""
		Run the select file loop.
		If no dirpath is given, PWD is used instead.
		Args:
		  dirpath:     Path to directory. Can be None to
		               use current working directory.
		  allowed_ext: List with allowed file extensions.
		               If None or empty, list all files.
		Return:
		  None:     No file selected/Cancelled
		  filepath: Path of selected file
		"""
		if not dirpath:
			dirpath = os_getcwd()
		self.dirpath = dirpath

		curses.curs_set(False)
		self.__readdir(self.dirpath, allowed_ext)
		self.__redraw()

		while True:
			try:
				ch = self.W.getch()
			except KeyboardInterrupt:
				break

			if ch == self.keys['CTRL_X']:
				# Cancel
				break

			elif ch == self.keys['ENTER']:
				file,size,isdir = self.__get_selected()
				filepath = path_join(self.dirpath, file)

				if file == '..':
					# Goto parent directory
					self.__readdir(path_dirname(
						self.dirpath),
						allowed_ext)
				elif isdir:
					# Open selected directory
					self.__readdir(filepath,
						allowed_ext)
				else:
					# Return selected filename
					return filepath

			elif ch == self.keys['UP'] and self.cy > 0:
				# Scroll up
				self.cy -= 1
				self.__adjust_view()

			elif ch == self.keys['DOWN'] and\
					self.cy < len(self.filelist)-1:
				# Scroll down
				self.cy += 1
				self.__adjust_view()

			self.__redraw()

		return None



	def __redraw(self):

		with self.lock:
			h,w = self.W.getmaxyx()
			dirpath  = self.dirpath[-(w-2):]

			self.W.clear()
			self.W.addstr(1, 2, self.title, curses.A_BOLD)
			self.W.addstr(2, 1, dirpath + " "*(w-len(dirpath)-2),
				curses.A_REVERSE)

			for y,file in enumerate(self.filelist[self.vy:]):
				if y >= h-6: break

				self.__print_filelist_item(file, y+3,
					self.vy+y)

			s = "Press [CTRL+X] to quit"
			self.W.addstr(h-2, 2, s, curses.A_DIM)
			self.W.border()
			self.W.refresh()

	def __get_selected(self):
		try:
			return self.filelist[self.cy]
		except:	return None


	def __readdir(self, dirpath, allowed_ext=None):
		# Read all files of given directory to self.filelist.
		# The first item will always be '..'.

		self.dirpath = dirpath
		# Index 0 always holds '..'
		self.filelist  = [('..', 0, True)]

		self.cy = 0
		self.vy = 0

		try:
			# Catch permission errors and such
			all_files = os_listdir(self.dirpath)
		except:	return

		files = []
		dirs  = []
		maxnamelen = 0
		colmax = [0,0]
		h,w = self.W.getmaxyx()
		w -= 2

		for file in all_files:

			path = path_join(self.dirpath, file)
			try:
				size   = os_stat(path).st_size
				is_dir = path_isdir(path)
			except:
				continue

			if not is_dir:
				if not self.__has_ext(file, allowed_ext):
					continue

			fl = len(file)
			if fl >= w - 4 - 6: # TODO
				file = file[:10]+'...'+file[-10:]

			if len(file) > colmax[0]:
				maxnamelen = len(file)

			if is_dir:
				dirs.append((file, '', True))
			else:
				ssize = filesize_to_string(size)
				if len(ssize) > colmax[1]:
					colmax[1] = len(ssize)
				files.append((file, ssize, False))

		# Sort by name
		dirs.sort(key=lambda x: x[0])
		files.sort(key=lambda x: x[0])

		self.filelist += dirs + files
		self.colx = [3, w-colmax[1]-2]


	def __print_filelist_item(self, file, y, index):

		attr = 0
		size = ''

		if index == self.cy:
			attr |= curses.A_BOLD
			self.W.addstr(y, 1, '>', attr)

		# Print dirs in blue, but no size
		if file[2]:
			attr |= curses.color_pair(4)

		self.W.addstr(y, self.colx[0], file[0], attr)

		if not file[2]:
			self.W.addstr(y, self.colx[1], file[1],
				curses.A_DIM|attr)


	def __adjust_view(self):
		h,w = self.W.getmaxyx()
		if self.cy < self.vy:
			self.vy = self.cy
		elif self.cy > self.vy+h-7:
			self.vy += 1


	def __has_ext(self, filename, extensions=None):
		# Check if the filename's extension exists in given
		# list with allowed extensions. If no extensions
		# given, the return value will be always True!
		if not extensions:
			return True
		ext = path_splitext(filename)[1].lower()
		if not ext or ext not in extensions:
			return False
		return True
