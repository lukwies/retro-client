import curses
import threading


"""\
Entrybox

+-------------------------------+
| Title				|
+-------------------------------+
|				|
+-------------------------------+
"""

class EntryBoxWindow:

	def __init__(self, parent, lock:threading.Lock,
			keys, title="Enter",
			is_password=False,
			password_replace_char=''):
		"""\
		Args:
		  parent: Underlying curses window
		  lock:   Lock for parent window
		  keys:   Keyboard (see Keyboard.py)
		  title:  Title
		"""

		self.parent = parent
		self.lock   = lock
		self.keys   = keys
		self.title  = title
		self.ispass = is_password
		self.passchar = password_replace_char

		title_len = len(title)
		if title_len < 26:
			title_len = 26

		h,w = self.parent.getmaxyx()

		self.W = curses.newwin(5,
				title_len+4,
				int(h/2-2),
				int(w/2-title_len/2))
		self.W.keypad(True)

		self.cx   = 0
		self.text = ''


	def get_input(self):
		"""\
		Asks user to confirm quesion.
		Return: True or False
		"""
		curses.curs_set(True)
		self.text = ''
		self.__redraw()

		while True:
			try:
				ch = self.W.getch()
			except KeyboardInterrupt:
				self.text=None
				break

			cx  = self.cx
			txt = self.text

			if ch == self.keys['CTRL_X']:
				self.text=None
				break
			elif ch == self.keys['ENTER']:
				break
			elif ch > ord(' ') and ch <= ord('~'):
				if len(txt) < len(self.title)+4:
					self.text = txt[:cx] \
						  + chr(ch) \
						  + txt[cx:]
					self.cx   += 1
			elif ch == self.keys['BACKSPACE']:
				if self.cx > 0:
					self.text = txt[:cx-1] \
						  + txt[cx:]
					self.cx -= 1
			self.__redraw()

		curses.curs_set(False)
		return self.text


	def __redraw(self):

		h,w = self.W.getmaxyx()
		title = " " + self.title + " "*(w-len(self.title)-1-2)

		self.lock.acquire()
		try:
			self.W.clear()
			self.W.addstr(1, 1, title, curses.A_REVERSE)

			if self.ispass:
				self.W.addstr(2, 2, self.passchar*len(self.text))
			else:	self.W.addstr(2, 2, self.text)
			self.W.addstr(3, 2, 'Press [CTRL+X] to quit',
					curses.A_DIM)

			self.W.move(2, 2+self.cx)
			self.W.border()
			self.W.refresh()
		finally:
			self.lock.release()


	def __del__(self):
		"""\
		Make sure window is deleted properly.
		"""
		del self.W
