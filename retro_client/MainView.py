import curses
import time
import logging
import textwrap


LOG = logging.getLogger(__name__)


"""\
 ___ ___ ___ ___ ____
 |_/ |_   |  |_/ |  |
 | \ |___ |  | \ |__|

This window contains a topsection showing the logo
and some information and a scroll text window holding
all log messages.

"""
class MainView:

	def __init__(self, gui):
		self.gui     = gui
		self.W       = gui.W['main']
		self.C       = gui.cli	# RetroClient
		self.cy      = 0	# Cursor y position
		self.changed = True

		# List with tuples (date,text,attr)
		self.lines = []

		# Textwrapper for log messages
		_,w = self.W.getmaxyx()
		self.tW = textwrap.TextWrapper(w-12)


	def add_msg(self, level, msg, redraw=True):
		"""\
		Add log message to mainview scroll text box.
		By default this will redraw the mainview if
		the chatview isn't opened.

		Args:
		  level:  Loglevel (logging.ERROR, ...)
		  msg:    Log message
		  redraw: Redraw mainview (if enabled) ?
		"""
		attrs = {
			logging.ERROR   : self.gui.colors['r'],
			logging.WARNING : self.gui.colors['y'],
			logging.INFO    : 0,
			logging.DEBUG   : 0 }

		attr  = 0
		if level in attrs:
			attr = attrs[level]

		lines = self.tW.wrap(msg)
		st = time.strftime("%H:%M:%S")

		for i,line in enumerate(lines):
			if i>0: st=None
			self.lines.append((
				st, line, attr))
		self.changed = True

		if not self.gui.chatView and redraw:
			self.redraw()

		LOG.log(level, msg)


	def scroll_up(self):
		if self.cy > 0:
			self.cy -= 1
			self.changed = True


	def scroll_down(self):
		if self.cy < len(self.lines)-1:
			self.cy += 1
			self.changed = True


	def redraw(self, force_redraw=False):
		"""\
		Redraw if changed.
		"""

		if not self.changed and not force_redraw:
			return

		with self.gui.winLock:
			h,w = self.W.getmaxyx()

			# Draw the logo and welcome message always
			# on top of window, before the scroll text.
			self.__print_logo(h, w)

			# Draw the scroll text (self.lines).
			y = 9
			boxh = h-y-1

			for boxy,line in enumerate(self.lines[self.cy:]):
				if boxy >= boxh: break
				self.__print_line(y, line)
				y += 1

			self.W.border()
			self.W.refresh()
			self.changed = False


	def __print_line(self, y, line):
		# Print single line
		try:
			if line[0]:
				self.W.addstr(y, 1, line[0],
					curses.A_DIM)
			self.W.addstr(y, 10, line[1], line[2])
		except:
			# Screen too small
			pass

	def __print_logo(self, h, w):
		# Print the logo, welcome message and command help.
		# Args: window height/width
		self.W.clear()
		self.W.addstr(1, 2, "___ ___ ___ ___ ____",self.gui.colors['b']|curses.A_BOLD)
		self.W.addstr(2, 2, "|_/ |_   |  |_/ |  |",self.gui.colors['b']|curses.A_BOLD)
		self.W.addstr(3, 2, "| \\ |___ |  | \\ |__|", self.gui.colors['b']|curses.A_BOLD)

		self.W.addstr(5, 2, "Hello {}, welcome to retro chat!"\
				.format(self.C.account.name), curses.A_BOLD)
		self.W.addstr(6, 2, "Press [ctrl]+H for more information ...")
		self.W.hline(8, 0, curses.ACS_HLINE, w)
