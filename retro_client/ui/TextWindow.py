import curses
from threading import Lock
import textwrap


"""
HelpWindow

Load a textfile and renders a scrolled text window
from it.

Keys:
 UP,DOWN:  Scroll text window
 CTRL-X:   Quit helpview
 CTRL-C:   Quit helpview

"""

class TextWindow:
	def __init__(self, parent, lock:Lock, keys, title="Help"):
		"""
		Args:
		  parent: Underlying curses window
		  lock:   Window lock
		  keys:   Class Keyboard (see Keyboard.py)
		  title:  Window title
		"""

		self.parent = parent
		self.lock   = lock
		self.keys   = keys
		self.title  = title

		h,w = parent.getmaxyx()
		self.W = curses.newwin(h-2, w, 1, 0)
		self.W.keypad(True)

		self.lines   = ['']
		self.cy      = 0
		self.changed = True


	def add_line(self, text):
		self.lines.append(text)


	def read_textfile(self, path):
		"""
		Converts content of given path's file to
		a list of lines (self.lines)
		"""
		try:
			data = open(path, 'r').read()
		except:	return False

		_,w = self.W.getmaxyx()
		tw  = textwrap.TextWrapper(w-2)

		for line in data.splitlines():
			x = tw.wrap(line)
			self.lines += x if x else ['']

		return True



	def show(self):

		curses.curs_set(False)
		while True:
			self.__redraw()

			try:
				ch = self.W.getch()
			except KeyboardInterrupt:
				break

			if ch == self.keys['CTRL_X']:
				# Quit helpview
				break

			elif ch == self.keys['UP'] and self.cy > 0:
				# Scroll up
				self.cy -= 1
				self.changed = True

			elif ch == self.keys['DOWN'] and\
					self.cy < len(self.lines)-1:
				# Scroll down
				self.cy += 1
				self.changed = True
		return True


	#-----------------------------------------------------------

	def __redraw(self):
		if not self.changed:
			return

		self.lock.acquire()
		try:
			h,w = self.W.getmaxyx()

			self.W.clear()
			self.W.addstr(1, 1, " "+self.title \
				+ ' '*(w-3-len(self.title)),
				curses.A_REVERSE)
#			y = 2
			attr = 0

			for y,line in enumerate(self.lines[self.cy:], start=2):
				if y >= h-3: break
				attr = self.__print_line(
					y, 1, line, attr)

			self.W.addstr(h-2, 2, 'Press [CTRL+X] to quit',
				curses.A_DIM)

			self.W.border()
			self.W.refresh()
		finally:
			self.lock.release()
			self.changed = False




	def __print_line(self, y, x, line, attr=0):
		"""
		Print text to given window at y/x position.
		This supports the following expression for styled
		text ouput:

		  **TEXT**      Bold text
		  __TEXT__      Underlined text
		  ??TEXT??      Dimmed text
		  ~~TEXT~~      Reverse text
		  ##TEXT##      Blinking text

		Args:
		  win:	Curses window instance
		  y:	Y position in window
		  x:	X position in window
		  line: Line string
		  attr: Printing attributes, should be 0 on
			first call!
		Return:
		  Last used attributes
		"""

		# All string are placed between 2 of
		# the following characters, it has an attribute.
		SPEC = {
			'**' : curses.A_BOLD,
			'??' : curses.A_DIM,
			'~~' : curses.A_REVERSE,
			'__' : curses.A_UNDERLINE,
			'##' : curses.A_BLINK
		}

		active = {}
		for key in SPEC.keys(): active[key] = 0

		i = 0
		self.W.move(y, x)
		while i < len(line):
			ch = line[i]
			if line[i:i+2] in SPEC:
				# Found one of '**', '~~', ...
				# So let's either turn on or off attributes
				spec = line[i:i+2]
				if (attr & SPEC[spec]):
					attr &= ~SPEC[spec]
				else:	attr |= SPEC[spec]
				i += 2
			else:
				self.W.addch(ch, attr)
				i += 1
		return attr
