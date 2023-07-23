import curses
import threading
import textwrap


"""\
Dialog window.

+-------------------------------+
| Title ...			|
+-------------------------------+
| Body message ...		|
|				|
| [button1] [button2] ...	|
+-------------------------------+


"""


class DialogWindow:

	def __init__(self, parent, lock:threading.Lock, keys,
			title="Warning",
			body="Do you want to quit?",
			buttons=['no','yes'],
			selected=None):
		"""\
		Init the dialog window.

		The window height is defined by the number of
		lines of body message (max-linelength=36)

		Args:
		  parent:   Underlying curses window
		  lock:     Lock for parent window
		  keys:     See Keyboard.py
		  title:    Window title message
		  body:     Window body message
		  buttons:  List with button names
		  selected: Selected button (None or button name)
		"""
		tw = textwrap.TextWrapper(36)

		self.parent = parent
		self.lock   = lock
		self.keys   = keys
		self.title  = title
		self.body   = tw.wrap(body) # Wrap body text to list
		self.btns   = buttons	# List with buttons (strings)
		self.btni   = 0		# Selected button (index)

		# Resolve 'selected' to index in self.btns.
		if selected and selected in buttons:
			self.btni = self.btns.index(selected)

		ph,pw = self.parent.getmaxyx()

		h = 6 + len(self.body)
		w = 40
		y = int(ph/2-h/2)
		x = int(pw/2-w/2)

		self.W = curses.newwin(h, w, y, x)
		self.W.keypad(True)


	def show(self):
		"""\
		Show the dialog window and let user select/press
		on of the buttons.

		Return: The name of pressed button or None if
		        interrupted.
		"""
		curses.curs_set(False)
		self.__redraw()

		while True:
			try:
				ch = self.W.getch()
			except KeyboardInterrupt:
				break

			if ch == self.keys['ENTER']:
				# User pressed enter.
				# Return name of selected button
				return self.btns[self.btni]

			elif ch == self.keys['LEFT'] and\
					self.btni > 0:
				self.btni -= 1
			elif ch == self.keys['RIGHT'] and\
					self.btni < len(self.btns)-1:
				self.btni += 1
			elif ch == self.keys['CTRL_X']:
				break

			self.__redraw()

		return None


	def __redraw(self):
		"""\
		Redraw the dialog window.
		"""
		with self.lock:
			h,w = self.W.getmaxyx()
			self.W.clear()
			self.W.addstr(1, 1, ' '+self.title+' '*(w-3-len(self.title)),
					curses.A_REVERSE)

			for i,s in enumerate(self.body):
				self.W.addstr(i+3, 2, s)

			self.W.move(h-2, 2)
			for i,btn in enumerate(self.btns):
				if i == self.btni:
					self.W.addstr("["+btn+"] ", curses.A_BOLD)
				else:	self.W.addstr("["+btn+"] ", curses.A_DIM)

			self.W.border()
			self.W.refresh()


	def __del__(self):
		"""\
		Make sure window is deleted properly.
		"""
		del self.W
