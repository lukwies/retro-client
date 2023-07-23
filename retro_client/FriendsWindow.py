import curses
from libretro.Friend import *

"""\
A window holding a list with all friends,
drawn at the left side of the screen.

+---------------+
| Friends       |
+---------------+
|-online--------|
| Alice         |
+---------------+
|-offline-------|
| Bob (2)       |
| Carl (1)      |
|               |
|               |
+---------------+

"""
class FriendsWindow:

	def __init__(self, gui):
		"""\
		Init friends list view inside gui.W['left'] window.
		Args:
		  gui:      RetroGui instance
		"""
		self.gui     = gui
		self.account = gui.cli.account
		self.W       = gui.W['left']

		self.friends = []	# List with friends
		self.cy      = None	# Selected friend
		self.vy      = None	# Y view position
		self.changed = True	# Must redraw?
		self.reset_friends()


	def reset_friends(self):
		"""\
		Reset the friends list, the selected friend and
		the viewport.
		"""
		self.friends = list(self.account.friends.values())
		self.cy = 0 if len(self.friends) > 0 else None
		self.vy = self.cy
		self.changed = True


	def getch(self):
		return self.W.getch()


	def get_selected(self):
		"""\
		Return name of selected friend or None
		if nothing is selected.
		"""
		if self.cy == None or self.cy >= len(self.friends):
			return None
		else:
			return self.friends[self.cy]


	def handle_event(self, ch):
		"""\
		Handle the keyevents 'UP' and 'DOWN' and
		select the previous or next friend within
		the friend list.
		"""
		if self.cy == None:
			return

		if ch == self.gui.keys['UP']:
			if self.cy > 0:
				self.cy -= 1
				self.__adjust_view()
				self.changed = True
		elif ch == self.gui.keys['DOWN']:
			if self.cy < len(self.friends)-1:
				self.cy += 1
				self.__adjust_view()
				self.changed = True


	def redraw(self, force_redraw=False):
		"""\
		Redraw the friendlist window.
		"""

		if not self.changed and not force_redraw:
			return

		# We sort friends by 'status' to have first the online
		# and then the offline friends.
		#self.friends = list(self.gui.cli.account.friends.values())
		self.friends = list(self.gui.cli.account.friends.values())
		self.friends.sort(key=lambda x: x.status, reverse=False)

		self.gui.winLock.acquire()
		try:
			h,w = self.W.getmaxyx()
			self.W.clear()
			try:
				self.W.addstr(1, 1, " Friends" + " "*(w-2-8),
					self.gui.colors['Wb']|curses.A_BOLD)

				self.__print_friendlist(h, w, 2)
				self.W.border()
			except:
				# Screen too small
				pass
			self.W.refresh()

		finally:
			self.gui.winLock.release()

		self.changed = False


	def __print_friendlist(self, h, w, y):
		"""\
		Print the friendlist.
		"""

		if len(self.friends) == 0:
			self.W.addstr(2, 2, "No friends :-(")
			return

		def print_hline(s, y, w, attr=0):
			self.W.addstr(y, 1, "-"+s+"-"*(w-len(s)-2),
				attr)

		status = None
		i = 0

		while i < len(self.friends):

			fr = self.friends[i]

			if fr.status == Friend.ONLINE and\
			   status != Friend.ONLINE:
				status = Friend.ONLINE
				print_hline("online", y, w,
					self.gui.colors['g'])
				y += 1
			elif fr.status == Friend.OFFLINE and\
			   status != Friend.OFFLINE:
				status = Friend.OFFLINE
				print_hline("offline", y, w)
				y += 1
			elif fr.status == Friend.UNKNOWN and\
			     status != Friend.UNKNOWN:
				status = Friend.UNKNOWN
				print_hline("unknown", y, w,
					self.gui.colors['r'])
				y += 1

			# Print the friend itself.
			a = [curses.A_BOLD, curses.A_DIM, curses.A_DIM]

			if i == self.cy:
				self.W.addstr(y, 1, "+ " + fr.name,
					curses.A_BOLD)
			else:	self.W.addstr(y, 1, "  " + fr.name,
					a[fr.status])

			# Print number of unseen messages "(N)"
			n_unseen = fr.unseen_msgs
			if n_unseen > 0:
				x = 3+len(fr.name)+1
				self.W.addstr(y, x, "(")
				self.W.addstr(str(n_unseen),
					self.gui.colors['r']|curses.A_BOLD)
				self.W.addstr(")")

			y += 1
			i += 1


	def __adjust_view(self):
		if self.cy == None:
			return
		h,_ = self.gui.stdscr.getmaxyx()

		if self.vy > self.cy:
			self.vy = self.cy
		elif self.cy > self.vy + h-1:
			self.vy += 1


