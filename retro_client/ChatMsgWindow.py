import curses
import textwrap
import time


from libretro.protocol import Proto
from . ui.FileDownloadWindow import filesize_to_string

"""\
  Window for rendering chat messages.
  The ChatMsgWindow is controlled by the ChatView class.


 +----------------------------------------------+
 | Conversation with r2d2			|
 +----------------------------------------------+
 | <r2d2> (2022-12-01 20:20)			|
 |  Hi There!					|
 |  peilnix (2022-12-01 21:30)			|
 |  Hey r2d2, how are you today?		|
 | ...						|
 |						|
 +----------------------------------------------+


Internally the messages are stored as a list of lines.
There are some special lines, determined by their prefix.

All messages start with the following line:
	/M/M/M<SENDER>/<TIMESTAMP>

A file info line:
	/F/F/F<FILENAME>/<FILESIZE_STRING>/<DOWNLOADED>

An 'unseen marker' (line between seen and unseen messages)
starts with:
	/U/U/U

A dimmed line starts with:
	/D/D/D


Date
 Mo, 2. july 20:21
"""

class ChatMsgWindow:

	def __init__(self, gui):

		self.gui = gui
		self.W   = gui.W['main']
		self.W.keypad(True)

		# Current communication partner.
		self.friend = None

		# All messages as a list of lines.
		# Each message has a leading line containing the
		# sender name and timestamp followed by the message
		# text:
		# 	msg1-line0: "/M/M/M[SENDER]/[TIMESTAMP]"
		# 	msg1-line1: text
		# 	msg1-lineN: ...
		# 	msg2-line0: "/U/U/U
		#	...
		# All messages are separated by an empty line.
		#
		self.lines      = []
		self.num_msgs   = 0	# Number of messages
		self.num_unseen = 0	# Number of unseen messages

		# Currently selected line
		self.cy = 0

		# Textwrapper for adjust message body to
		# window width
		_,w = self.W.getmaxyx()
		self.tw = textwrap.TextWrapper(w-4)
		self.last_color = 0 # For w.attron

		# Screen content has changed?
		self.changed = True


	def add_msg(self, msg):
		"""\
		Add message to line list.
		If message is unseen and self.num_unseen == 0, we add the
		string "/U/U/U" to the line list to mark the beginning of
		unseen messages.
		Args:
		  msg: Message dict
		"""

		if msg['unseen'] == 1:
			# If given message is "unseen" and there
			# were no "unseen" messages yet, add an
			# "unseen"-marker-line.
			if self.num_unseen == 0:
				self.lines.append("/U/U/U")
				self.lines.append("")
			self.num_unseen += 1

		# Add message header ("<sender> <msg-time>")
		self.lines.append("/M/M/M{}/{}".format(
			msg['from'],
			self.__format_msgtime(msg['time']) ))

		if msg['type'] == Proto.T_FILEMSG:
			# File message
			# TODO What happens if filename too long?
			ssize = filesize_to_string(msg['size'])
			self.lines.append("/F/F/F{}/{}/{}"\
				.format(msg['filename'], ssize,
					msg['downloaded']))
			if not msg['downloaded']:
				self.lines.append('/D/D/D'\
					'Press [ctrl+D] to download')
		else:
			# Message
			self.__add_wrap_text(msg['msg'])

		self.lines.append("")
		self.num_msgs += 1


	def set_msgs(self, msgs=[]):
		"""\
		Set chat messages.
		"""
		self.num_msgs   = 0
		self.num_unseen = 0
		self.cy         = 0
		self.lines      = []

		for msg in msgs:
			self.add_msg(msg)
		self.reset_view()


	def reset_view(self):
		"""\
		Set view point that latest message can be seen.
		"""
		h,_ = self.gui.W['main'].getmaxyx()
		boxh   = h-3
		nlines = len(self.lines)
		self.cy = 0 if nlines<boxh else nlines-boxh-1
		self.changed = True


	def scroll_up(self):
		""" Scroll up """
		if self.cy > 0:
			self.cy -= 1
			self.changed = True

	def scroll_down(self):
		""" Scroll down """
		h,_ = self.W.getmaxyx()

		if self.cy < len(self.lines)-h+2:
			self.cy += 1
			self.changed = True


	def redraw(self, force_redraw=False):
		"""\
		Redraw window

		Locks: self.gui.winLock
		"""
		if not self.changed and not force_redraw:
			return

		self.gui.winLock.acquire()
		try:
			h,w = self.W.getmaxyx()
			self.W.clear()

			try:
				self.__draw_headline(h, w)

				y = 2
				for line in self.lines[self.cy:]:
					if y >= h-1: break

					if line[:6] == '/M/M/M':
						self.__print_msg_header(y, line)
					elif line[:6] == '/F/F/F':
						self.__print_file_msg(y, line)
					elif line[:6] == "/D/D/D":
						self.W.addstr(y, 2, line[6:], curses.A_DIM)
					elif line == "/U/U/U":
						self.__print_unseen_marker_line(y, w)
					else:
						self.__print_msg(y, line)
					y += 1

				self.__draw_scrollbar(2, w-2, h-3)
				self.W.border()
			except:
				# Screen too small
				pass
			self.W.refresh()
		finally:
			self.gui.winLock.release()

		self.changed = False


	def remove_unseen_marker(self):
		"""\
		Remove line "/U/U/U" and the trailing one from self.lines.
		"""
		while True:
			try:
				i = self.lines.index("/U/U/U")
				self.lines.pop(i)
				self.lines.pop(i)
			except ValueError:
				break

	def close(self):
		self.gui.winLock.acquire()
		try:
			self.W.clear()
			self.W.refresh()
		finally:
			self.gui.winLock.release()

	#-- PRIVATE ------------------------------------------------------

	def __add_wrap_text(self, msg_text):
		# Add message text to line list.
		lines = msg_text.splitlines()
		for line in lines:
			self.lines += self.tw.wrap(line)


	def __draw_headline(self, h, w):
		# Draw the 1th line (headline) of the chat message window.
		self.W.addstr(1, 1, " "*(w-2), self.gui.colors['Wb'])
		self.W.addstr(1, 1, " Conversation with " + self.friend.name,
			self.gui.colors['Wb']|curses.A_BOLD)
		s = str(self.num_msgs)
		self.W.addstr(1, w-2-len(s), s, self.gui.colors['Wb'])


	def __print_msg_header(self, y, line):
		# Print a message header "SENDER (TIME)"
		sender,dt = line[6:].split('/')

		if sender == self.gui.cli.account.name:
			attr = self.gui.colors['b']
			sender = 'you'
		else:	attr = self.gui.colors['g']

		# Print sender name and sent time
		self.W.addstr(y, 1, sender, attr)
		self.W.addstr(" ("+dt+")", curses.A_DIM)


	def __print_unseen_marker_line(self, y, w):
		# Print a line marking the beginning of unseen
		# messages.
		s = " {} new messages ".format(self.num_unseen)
		self.W.addstr(y, 1, "-"*(w-2), self.gui.colors['r'])
		self.W.addstr(y, int(w/2-len(s)/2), s, self.gui.colors['r'])


	def __print_file_msg(self, y, line):
		# Print file message.
		# /F/F/F<FILENAME>/<FILESIZE_STRING>/<DOWNLOADED>
		fname,fsize,downl = line[6:].split('/')
		self.W.addstr(y, 2, 'File ')
		self.W.addstr("'"+fname+"'", curses.A_BOLD)
		self.W.addstr(" ("+fsize+")", curses.A_DIM)



	def __print_msg(self, y, line):
		"""\
		Print message line to chat msg window.
		This supports the following expression for styled
		text ouput:

		  **TEXT**      Bold text
		  __TEXT__      Underlined text
		  ??TEXT??      Dimmed text
		  ~~TEXT~~      Reverse text
		  ##TEXT##      Blinking text
		"""
		special = {
			'**' : curses.A_BOLD,
			'??' : curses.A_DIM,
			'~~' : curses.A_REVERSE,
			'__' : curses.A_UNDERLINE,
			'##' : curses.A_BLINK
		}
		active = {}
		for key in special.keys(): active[key] = 0

		attr = 0
		i = 0
		self.W.move(y, 2)
		while i < len(line):
			ch = line[i]
			if line[i:i+2] in special:
				spec = line[i:i+2]
				if active[spec] == 1:
					attr &= ~special[spec]
					active[spec] = 0
				else:
					attr |= special[spec]
					active[spec] = 1
				i += 2
			else:
				self.W.addch(ch, attr)
				i += 1

	def __draw_scrollbar(self, y, x, h):
		"""\
		Draw scrollbar at the right side of window.
		"""

		# Get max cursor y position
		cymax = len(self.lines) - h - 1
		if cymax < 0: cymax = 0

		# Get scrollbar block position
		bar_y = int(self.cy * ((h-1) / cymax))
		if bar_y > h-3:	bar_y = h-3

		self.W.addch(y, x, curses.ACS_UARROW, curses.A_BOLD)
		self.W.addch(y+1+bar_y, x, curses.ACS_BLOCK, curses.A_DIM)
		self.W.addch(y+h-1, x, curses.ACS_DARROW, curses.A_BOLD)


	def __format_msgtime(self, msg_time):
		"""\
		Get formatted time string from given
		message time.
		"""
		tm  = time.strptime(msg_time, "%y-%m-%d %H:%M")
		now = time.localtime()

		if tm.tm_year != now.tm_year:
			# Message is not from current year
			return time.strftime("%m %b %Y %H:%M", tm)

		elif tm.tm_mon != now.tm_mon:
			# Message is not from current month
			# Format: "12. May 20:32"
			return time.strftime("%m %b %H:%M", tm)

		# Message date is within current month...
		daydiff = abs(tm.tm_mday - now.tm_mday)

		if daydiff > 5:
			# Message is older than 5 days
			# Format: "12. May 20:32"
			return time.strftime("%m %b %H:%M", tm)
		elif daydiff > 1:
			# Message is older than yesterday
			# Format: "Monday 20:32"
			return time.strftime("%A %H:%M", tm)
		elif daydiff == 1:
			# Message is from yesterday
			# Format: "yesterday 20:32"
			return time.strftime("yesterday %H:%M", tm)

		# Message is from today
		return time.strftime("%H:%M", tm)

