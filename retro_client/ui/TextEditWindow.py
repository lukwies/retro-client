import curses
import threading

class TextEditWindow:
	"""\
	Window for editing text.
	Args:
	  win:      Ncurses window instance
	  border:   Drawing border?
	  headline: Draw headline if given
	  keys:     Dictionary with supported keys
	  lock:     Window thread lock
	NOTES:
		- Lines have no ending newline '\n' !!
	"""
	def __init__(self, win,	border=False, headline=None,
			lock:threading.Lock=None):

		# Editing window
		self.W = win

		self.lines  = ['']	# List with lines (str)
		self.cy     = 0		# Cursor Y position
		self.cx     = 0		# Cursor X position
		self.vy     = 0		# Viewport y
		self.border = border	# Draw window border ?
		self.headline = headline # Draw headline ?
		self.lock     = lock	# Lock for window locking

		self.W.keypad(True)

		if self.lock:
			self.lock.acquire()
		try:
			self.W.clear()
			self.W.move(0, 0)
			self.W.refresh()
		finally:
			if self.lock:
				self.lock.release()


	def getch(self):
		"""\
		Key key from this window at current
		cursor position.
		"""
		cy = self.cy-self.vy
		cx = self.cx
		if self.border:
			cy += 1
			cx += 1
		if self.headline:
			cy += 1
		return self.W.getch(cy, cx)


	def handle_event(self, ch):
		"""\
		Handle key event.
		"""
		if ch >= ord(' ') and ch <= ord('~'):
			self.__add_char(chr(ch))
		elif ch == ord('\n'):
			self.__key_return()
		elif ch == curses.KEY_BACKSPACE:
			self.__key_backspace()
		elif ch == curses.KEY_DC:
			self.__key_del()
		elif ch == curses.KEY_UP:
			self.__move_cursor(0)
		elif ch == curses.KEY_RIGHT:
			self.__move_cursor(1)
		elif ch == curses.KEY_DOWN:
			self.__move_cursor(2)
		elif ch == curses.KEY_LEFT:
			self.__move_cursor(3)
		elif ch == ord('\t'):
			self.__add_char(' ')
		else:
			return
		self.__adjust_view()
		self.redraw()


	def get_text(self):
		"""\
		Get text.
		"""
		return "\n".join(self.lines).strip()


	def clear(self, clear_border=True):
		"""\
		Clear window and erase lines.
		"""
		self.lines  = ['']
		self.cy     = 0
		self.cx     = 0
		self.vy     = 0

		if self.lock:
			self.lock.acquire()
		try:
			self.W.clear()
			if not clear_border:
				self.W.border()
			self.W.refresh()
		finally:
			if self.lock:
				self.lock.release()


	def redraw(self):
		"""\
		Render text.
		"""
		h,w = self.W.getmaxyx()

		max_h = h	# Textbox height
		max_w = w	# Textbox width
		dy    = 0	# Text input Y pos
		dx    = 0	# Text input X pos

		if self.lock:
			self.lock.acquire()
		try:
			self.W.clear()
			if self.border:
				max_h -= 2
				max_w -= 2
				dy += 1
				dx += 1
				self.W.border()
			if self.headline:
				self.__print_headline(dy, dx, max_w)
				max_h -= 1
				dy += 1

			for li in range(self.vy, len(self.lines)):
				if li - self.vy >= max_h: break
				self.W.addstr(li-self.vy+dy, dx, self.lines[li])

			self.W.refresh()
		except:
			# Screen too small
			pass
		finally:
			if self.lock:
				self.lock.release()


	def update_cursor(self):
		"""\
		Updates the cursor position to self.cy/self.cx.
		"""
		self.W.move(self.cy-self.vy+2, self.cx+1)
		self.W.refresh()


	# ------------------------------------------------------------
	def __add_char(self, ch):
		"""\
		Add a character to the text.
		"""
		_,w = self.W.getmaxyx()
		if len(self.lines[self.cy]) >= w - 2:
			return
		s = self.lines[self.cy]
		s = s[:self.cx] + ch + s[self.cx:]
		self.lines[self.cy] = s
		self.cx += 1


	def __key_backspace(self):
		""" Do backspace """
		if self.cx == 0:
			if self.cy > 0:
				cx = len(self.lines[self.cy-1])
				self.lines[self.cy-1] += \
					self.lines[self.cy]
				self.lines.pop(self.cy)
				self.cy -= 1
				self.cx = cx
		else:
			s = self.lines[self.cy]
			s = s[:self.cx-1] + s[self.cx:]
			self.lines[self.cy] = s
			self.cx -= 1


	def __key_del(self):
		""" Do delete """
		s = self.lines[self.cy]
		if self.cx < len(s):
			s = s[:self.cx] + s[self.cx+1:]
			self.lines[self.cy] = s
		elif self.cy < len(self.lines)-1:
			self.lines[self.cy] += \
				self.lines[self.cy+1]
			self.lines.pop(self.cy+1)


	def __key_return(self):
		""" Do enter """
		if self.cx < len(self.lines[self.cy]):
			s = self.lines[self.cy]
			self.lines.insert(self.cy+1, s[self.cx:])
			self.lines[self.cy] = s[:self.cx]
		else:
			self.lines.insert(self.cy+1, "")
		self.cx  = 0
		self.cy += 1


	def __move_cursor(self, direction=0):
		"""\
		Move cursor.
		Args:
		  direction: 0=up, 1=right, 2=down, 3=left
		"""
		if direction == 0:
			if self.cy > 0:
				n = len(self.lines[self.cy-1])
				if n < self.cx:
					self.cx = n
				self.cy -= 1
			else:	self.cx = 0

		elif direction == 1:
			n = len(self.lines[self.cy])
			if self.cx >= n:
				if self.cy < len(self.lines)-1:
					self.cx = 0
					self.cy += 1
			else:	self.cx += 1

		elif direction == 2:
			if self.cy < len(self.lines)-1:
				n = len(self.lines[self.cy+1])
				if n < self.cx:
					self.cx = n
					self.cy += 1
				else:	self.cy += 1
			else:
				self.cx = len(self.lines[self.cy])

		elif direction == 3:
			if self.cx == 0:
				if self.cy > 0:
					self.cx = len(self.lines[self.cy-1])
					self.cy -= 1
			else:	self.cx -= 1


	def __adjust_view(self):
		"""\
		Adjust the view y position that cursor
		is always in viewport bounds.
		"""
		h,_ = self.W.getmaxyx()

		if self.border:
			h -= 2	# substract top/bottom line of border
		if self.headline:
			h -= 1

		if self.cy < self.vy:
			self.vy = self.cy
		elif self.cy >= self.vy + h:
			self.vy += 1


	def __print_headline(self, y, x, w):
		# Print Prompt
		s = "Enter command/message:"
		self.W.addstr(y, x, s + " "*(w-len(s)),
				curses.A_REVERSE)
		# Print text length
		ls = "{}/{}".format(self.cy, self.cx)
		self.W.addstr(y, w-len(ls), ls,
			curses.A_REVERSE|curses.A_DIM)


