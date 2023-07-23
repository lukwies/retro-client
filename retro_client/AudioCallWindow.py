import curses

from os import getcwd  as os_getcwd
from os import listdir as os_listdir
from os import stat    as os_stat
from os.path import join     as path_join
from os.path import dirname  as path_dirname
from os.path import isdir    as path_isdir
from os.path import splitext as path_splitext
from threading import Lock

from . AudioCall import *


"""\
The AudioCallWindow shows information about a
currently acitve voice call with a friend.
There are three different situations while
this window is open:

 1) Someone is calling us (phone is ringing)
 2) We are calling someone (their phone rings)
 3) We are currently talking with someone

+---------------------------------+
| Incoming call from USER ...     |
| ^O: Reject  ^P: Accept	  |
+---------------------------------+

+---------------------------------+
| Calling USER ...    	 	  |
| ^O: Stop			  |
+---------------------------------+

+---------------------------------+
| Talking with USER ...           |
| ^O: Hangup			  |
+---------------------------------+

"""
class AudioCallWindow:

	def __init__(self, gui):
		"""\
		Args:
		  gui: RetroGui instance
		"""
		self.gui = gui
		self.audioCall = gui.audioCall

		# ui
		self.W       = self.gui.W['call']
		self.title   = ''	# Title string
		self.help    = ''	# Command help string
		self.friend  = None	# Calling partner
		self.changed = True	# Win content changed?


	def open(self, friend): #, state=self.RINGING):
		"""\
		Opens the phonecall window.
		This will resize/refresh the gui.

		Args:
		  friend: The friend is calling or shall be called.
		"""
		if self.audioCall.closed():
			return False

		curses.curs_set(False)
		self.friend = friend
		self.set_state(self.audioCall.state)
		self.gui.redraw(force=True, resize=True)
		return True


	def close(self):
		"""\
		Close phone call window.
		This will resize and redraw the main gui.
		"""
		if not self.audioCall.closed():
			self.gui.clear_win('call')
			self.gui.audioCall.state = AudioCall.CLOSED
			self.gui.redraw(force=True, resize=True)


	def redraw(self, force_redraw=False):
		"""\
		Redraw audio call window.
		This method is called indirectly by ChatView
		and RetroGui.
		"""
		if self.audioCall.closed():
			return
		if not self.changed and not force_redraw:
			return

		ringing = self.audioCall.state == AudioCall.RINGING
		attr    = self.gui.colors['r'] | curses.A_BLINK


		with self.gui.winLock:
			self.W.clear()

			self.W.addstr(1, 2, self.title)
			self.W.addstr(2, 2, self.help, curses.A_DIM)

			if ringing: self.W.attron(attr)
			self.W.border()
			if ringing: self.W.attroff(attr)

			self.W.refresh()
			self.changed = False


	def handle_event(self, ch):
		"""\
		Pass event to handle.
		Keys:
		  CTRL+O  Cancel/Stop/Hangup
		  CTRL+P  Accept/Start call
		"""
		if self.audioCall.closed():
			return

		state = self.audioCall.state

		if ch == self.gui.keys['CTRL_P'] and \
				state == AudioCall.RINGING:
			# Accept and start call
			self.changed = True
			self.gui.audioCall.accept_call()

		elif ch == self.gui.keys['CTRL_O']:

			if state == AudioCall.RINGING:
				# Reject call
				self.changed = True
				self.gui.audioCall.reject_call()

			elif state == AudioCall.CALLING:
				# Stop calling (send 'stop-call')
				self.changed = True
				self.audioCall.stop_call()

			elif state == AudioCall.TALKING:
				# Hangup call
				self.changed = True
				self.audioCall.stop_call()

		self.redraw()



	def set_state(self, state):
		"""\
		Set current view state.

		Args:
		  state: The view state (See AudioCall.py)
			 AudioCall.RINGING
			 AudioCall.CALLING
			 AudioCall.TALKING
		"""
		frname = self.friend.name

		if state == AudioCall.RINGING:
			self.title = "Incoming call from " + frname + " ..."
			self.help  = "^O:Reject  ^P:Accept"
		elif state == AudioCall.CALLING:
			self.title = "Calling " + frname + " ..."
			self.help  = "^O:Stop"
		elif state == AudioCall.TALKING:
			self.title = "Talking with " + frname + " ..."
			self.help  = "^O:Hangup"
		else:
			self.title = "Closed"
			self.help  = "Shouldn't happen :-("

		self.changed = True

