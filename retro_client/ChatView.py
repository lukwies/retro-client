import curses
import logging
from base64 import b64decode

from libretro.RetroClient import RetroClient
from libretro.protocol import Proto

from . ui.TextWindow import *
from . ui.DialogWindow import *
from . ui.TextEditWindow import *
from . ui.FileBrowseWindow import *
#from . ui.FileDownloadWindow import *

from . ChatMsgWindow import ChatMsgWindow
from . filetrans import SendFileThread, RecvFileThread
from . VoiceMsgWindow import VoiceMsgWindow

LOG = logging.getLogger(__name__)

"""\
View for chatmessages and message/command input.
This will also control message sending and storing.

+-------------------------------+
| message view			|
|				|
|				|
|				|
|				|
+-------------------------------+
| input window			|
|				|
+-------------------------------+


[ctrl]+X 		 Go back to main view
[ctrl]+C 		 Go back to main view
[ctrl]+H                 Show help text
[ctrl]+F                 Upload/Send file
[ctrl]+D		 Download file
[page-up]		 Scroll messages up
[page-down]		 Scroll messages down

[return]		Send message
[shift]+[return]	Newline

"""

class ChatView:
	def __init__(self, gui):
		"""\
		Opens the chatview.
		The chat messages will be shown in gui.W['main'] window,
		the text input box within the gui.W['main2'] window.

		Args:
		  gui: RetroGui instance
		"""
		self.gui  = gui
		self.conf = gui.conf
		self.keys = gui.keys
		self.W    = gui.W

		# Chat message window
		self.wMsg = ChatMsgWindow(gui)

		# Textinput ()
		self.wIn = TextEditWindow(gui.W['main2'],
				headline="Input message/command:",
				border=True, lock=self.gui.winLock)

		self.friend     = None	# Conversation partner
		self.msgStore   = gui.cli.msgStore
		self.msgHandler = gui.cli.msgHandler


	def load_chat(self, friend):
		"""\
		Load last 100 messages from message database.
		"""
		self.friend      = friend
		self.wMsg.friend = friend

		try:
			msgs = self.msgStore.get_msgs(friend, 50)
			self.wMsg.set_msgs(msgs)
			return True
		except Exception as e:
			self.gui.error("MsgStore: "+str(e))
			return False


	def loop(self):
		"""\
		Runs the chatview loop.
		"""
		self.gui.resize()
		self.gui.log_msg("Press ^H for help")

		self.wIn.clear()
		self.wMsg.reset_view()
		self.redraw(True)


		while True:

			try:
				ch = self.wIn.getch()
			except KeyboardInterrupt as e:
				# Go back to main view on keyboard
				# interrupt
				break

			if ch == self.keys['CTRL_X']:
				# Go back to main view
				break

			elif ch == self.keys['CTRL_H']:
				# Show helpview
				self.__help()

			elif ch == self.keys['CTRL_F']:
				# Open filebrowser and start file upload
				self.__file_upload()

			elif ch == self.keys['CTRL_D']:
				# Download file
				self.__file_download()

			elif ch == self.keys['CTRL_K']:
				# Delete message
				self.__delete_message()

			elif ch == self.keys['CTRL_V']:
				# Open Voice message
				self.__voice_message()

#			elif ch == self.keys['CTRL_P']:
#				# If no audio call is running start one,
#				# otherwise let AudioCallWindow handle
#				# the key.
#				if self.gui.audioCall.closed():
#					self.gui.start_call(self.friend)
#				else:
#					self.gui.audioCallWindow\
#						.handle_event(ch)

#			elif ch == self.keys['CTRL_O']:
#				# The key CTRL+O will be handled by the
#				# audio call window.
#				self.gui.audioCallWindow.handle_event(ch)

			elif ch == self.keys['ENTER']:
				# Get text from input textfield and
				# send message or handle command.
				text = self.wIn.get_text()
				if text:
					if text[0] == "/":
						# Handle command
						self.__handle_command(text)
					else:
						# Send/Store message
						self.__send_msg(text)
					self.wIn.clear(False)

			elif ch == self.keys['SHIFT_ENTER']:
				# Shift+Enter will be handled as newline in
				# message input since Enter is already used
				# to send the input.
				self.wIn.handle_event(ord('\n'))

			elif ch == self.keys['PUP']:
				# Scroll msglist up
				self.wMsg.scroll_up()

			elif ch == self.keys['PDOWN']:
				# Scroll msglist down
				self.wMsg.scroll_down()

			elif ch == curses.KEY_RESIZE:
				# Resize screen
				self.gui.resize()
				self.wMsg.changed = True
			else:
				# Handle text input
				self.wIn.handle_event(ch)

			self.redraw()


		# Clear everything
		self.wIn.clear()
		self.wMsg.close()
		curses.curs_set(False)

		# If closing the chatview, we assume the user
		# has read all messages and set unseen=0 to all
		# of them.
		self.msgStore.set_all_seen(self.friend)
		self.friend.unseen_msgs = 0


	def redraw(self, force_redraw=False):
		"""\
		Redraw chat window.
		"""
		curses.curs_set(True)
		self.gui.print_topwin()
		self.wMsg.redraw(force_redraw)
		self.wIn.redraw()
#		self.gui.audioCallWindow.redraw(force_redraw)

	def reset_cursor(self):
		""" Reset text edit cursor """
		self.wIn.update_cursor()


	def add_msg(self, msg):
		"""\
		Add text message to chat.
		This will redraw the chatmsgview.
		"""
		self.wMsg.add_msg(msg)
		self.wMsg.reset_view()
		self.wMsg.redraw()
		self.wIn.update_cursor()


	# --- PRIVATE ------------------------------------------

	def __send_msg(self, text):
		"""\
		Send message.
		1) Check if given text is valid
		2) Check if connected to server
		3) Encrypt message
		4) Send message
		5) Store message
		6) Add message to ChatMsgWindow
		"""

		if not text or text == '':
			return False

		if not self.gui.connected:
			self.gui.log_msg("Not connected!",
				error=True)
			return False

		# Encrypt message
		msg,e2e_buf = self.msgHandler.make_msg(
				self.friend, text,
				Proto.T_CHATMSG)

		# Send message
		self.gui.cli.send_packet(
				Proto.T_CHATMSG,
				e2e_buf)

		# Store message to database
		self.msgStore.add_msg(self.friend, msg)

		# Add message to chat-message-view and
		# update view.
		self.wMsg.remove_unseen_marker()
		self.wMsg.add_msg(msg)
		self.wMsg.reset_view()

		# Tell event notifier that we sent a message.
		self.gui.evNotifier.on_sent_message(
				self.friend.name,
				is_filemsg=False)
		return True


	def __file_upload(self):
		"""\
		Opens a filebrowser and let user select file
		which later shall be sent to another client.
		"""
		if not self.gui.connected:
			self.gui.log_msg("Not connected to server",
				error=True)
			return

		fileBrowser = FileBrowseWindow(self.W['main'],
				self.gui.winLock, self.keys,
				"Select file to send ...")
		filepath = fileBrowser.select_file()

		self.redraw(True)

		if filepath:
			t = SendFileThread(self.gui,
				self.friend, filepath)
			t.start()


	def __file_download(self):
		"""\
		Dowload file.
		This will only work if selected message is a file
		message and the file hasn't been downloaded yet.
		"""
		msg = self.wMsg.get_selected()
		if not msg or msg['type'] != Proto.T_FILEMSG:
			return
		elif msg['downloaded']:
			self.gui.log_msg("File was already downloaded",
				error=True)
			return
		elif not self.gui.connected:
			self.gui.log_msg("Not connected", error=True)
			return

		t = RecvFileThread(self.gui,
				self.friend,
				msg['fileid'],
				msg['filename'],
				b64decode(msg['key']))
		t.start()


	def __delete_message(self):
		"""\
		Delete currently selected message.
		Let user confirm before deleting...
		"""
		msg = self.wMsg.get_selected()
		if not msg: return

		dia = DialogWindow(
			self.gui.stdscr,
			self.gui.winLock,
			self.gui.keys,
			"Delete message?",
			"Do you really want to delete this "\
			"message? This can not be undone!",
			["no", "yes"], "no")
		res = dia.show()
		self.wMsg.changed = True

		if res == "yes":
			self.msgStore.delete_msg(self.friend, msg['id'])
			self.wMsg.delete_selected()
			self.gui.log_msg("Deleted message")


	def __voice_message(self):
		"""\
		Open VoiceMsgWindow.
		"""
		vMW = VoiceMsgWindow(self.gui)
		vMW.show()
		self.wMsg.changed = True
			

	def __handle_command(self, cmd):
		# Handle user given command (starts with '/')
		if cmd == "/help":
			self.__help()
		else:
			#TODO
			pass


	def __help(self):
		# Open help window
		path = path_join(self.gui.uiconf.helpdir, "chat.txt")
		help = TextWindow(self.gui.stdscr, self.gui.winLock,
				self.keys, title="Chat Help")
		if not help.read_textfile(path):
			self.gui.log_msg("Failed to open helpfile '"\
				+path+"'", error=True)
		else:
			help.show()
			self.redraw(True)

		curses.curs_set(True)
