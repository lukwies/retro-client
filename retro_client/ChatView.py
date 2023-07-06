import curses
import logging as LOG

from libretro.RetroClient import RetroClient

from . ui.TextEditWindow import *
from . ui.FileBrowseWindow import *
from . ui.ConfirmWindow import *
from . ui.FileDownloadWindow import *
from . ui.TextWindow import *

#from InputWindow import InputWindow
from . ChatMsgWindow import ChatMsgWindow

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
[ctrl]+F                 Send file

[return]		Send message
[shift]+[return]	Newline


/help
/sendfile
"""

class ChatView:
	def __init__(self, gui):
		"""
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
		self.fileTrans  = gui.fileTransfer


	def load_chat(self, friend):
		"""
		Load last 100 messages from message database.
		"""
		self.friend      = friend
		self.wMsg.friend = friend

		try:
			msgs = self.msgStore.get_msgs(friend, 50)
			self.wMsg.set_msgs(msgs)
			return True
		except Exception as e:
			self.gui.error(str(e))
			return False


	def loop(self):

		self.__resize()
		self.gui.log_msg("Press ^H for help")

		# All these will lock self.gui.winLock
		self.wIn.clear()
		self.wIn.redraw()
		self.wMsg.reset_view()
		self.wMsg.redraw()
		curses.curs_set(True)


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
				self.__resize()
			else:
				# Handle text input
				self.wIn.handle_event(ch)

			self.wMsg.redraw()
			self.wIn.redraw()

		# Clear everything
		self.wIn.clear()
		self.wMsg.close()
		curses.curs_set(False)

		# If closing the chatview, we assume the user
		# has read all messages and set unseen=0 to all
		# of them.
		self.msgStore.set_all_seen(self.friend)
		self.friend.unseen_msgs = 0


	def add_msg(self, msg):
		"""
		Add text message to chat.
		This will redraw the chatmsgview.
		"""
		self.wMsg.add_msg(msg)
		self.wMsg.reset_view()
		self.wMsg.redraw()
		self.wIn.update_cursor()


	def __send_msg(self, text):
		"""
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
			self.gui.log_msg("Not connected!", error=True)
			return False

		# Encrypt message
		msg,e2emsg = self.msgHandler.make_msg(
				self.friend, text,
				'message')

		# TODO try/catch ?
		self.gui.cli.send_dict(e2emsg)

		# Store message in database
		self.msgStore.add_msg(self.friend, msg)

		# Add message to chat-message-view and
		# update view.
		self.wMsg.remove_unseen_marker()
		self.wMsg.add_msg(msg)
		self.wMsg.reset_view()

		return True


	def __file_upload(self):
		# Opens a filebrowser and let user select file
		# which later shall be sent to another client.
		if not self.gui.connected:
			self.gui.log_msg("Not connected to server",
				error=True)
			return

		fileBrowser = FileBrowseWindow(self.W['main'],
				self.gui.winLock, self.keys,
				"Select file to send ...")
		filepath = fileBrowser.select_file()
		del fileBrowser

		self.wMsg.changed = True
		self.wMsg.redraw()
		curses.curs_set(True)

		if filepath:
			# Upload file ...
			thread = threading.Thread(
				target=self.fileTrans.upload_file,
				args=(self.friend,filepath))
			thread.start()


	def __file_download(self):
		# Get all file messages and remove the once that are
		# already downloaded.
		msgs = self.msgStore.get_not_downloaded_files(
				self.friend)
		if not msgs:
			# No files to download!
			self.gui.log_msg("No files to download!", True)
			return

		# Open window to let user select filename
		win = FileDownloadWindow(self.W['main'],
				self.gui.winLock, self.keys)
		msg = win.select_file(msgs)
		del win

		curses.curs_set(True)
		self.wMsg.changed = True
		self.wMsg.redraw()

		if msg:
			# Download file ...
			thread = threading.Thread(
				target=self.fileTrans.download_file,
				args=(self.friend,
				      msg['fileid'],
				      msg['filename'],
				      msg['key']))
			thread.start()


	def __handle_command(self, cmd):
		# Handle user given command (starts with '/')
		if cmd == "/help":
			self.__help()

		elif cmd.startswith("/sendfile"):
			self.__file_upload()

		elif cmd.startswith("/download"):
			#TODO
			pass


	def __resize(self):
		# Resize windows
		h,w = self.gui.stdscr.getmaxyx()

		self.gui.print_topwin()
		self.gui.winLock.acquire()
		try:
			self.W['top'].resize(1, w)
			self.W['top'].mvwin(0, 0)

			# Hide sidebar
			self.W['left'].clear()

			# Main and main2 will fill whole window width
			self.W['main'].resize(h-2-self.gui.W_MAIN2_H, w)
			self.W['main'].mvwin(1, 0)
			self.W['main2'].resize(self.gui.W_MAIN2_H, w)
			self.W['main2'].mvwin(h-1-self.gui.W_MAIN2_H, 0)

			# Log window
			self.W['log'].resize(1, w)
			self.W['log'].mvwin(h-1, 0)

			[win.refresh() for win in self.gui.W.values()]

			self.wMsg.changed = True
		except:
			# Screen too small
			pass
		finally:
			self.gui.winLock.release()


	def __help(self):
		# Open help window
		path = path_join(self.gui.resdir, "help/chat.txt")
		help = TextWindow(self.gui.stdscr, self.gui.winLock,
				self.keys, title="Chat Help")
		if not help.read_textfile(path):
			self.gui.log_msg("Failed to open helpfile '"\
				+path+"'", error=True)
		else:
			help.show()
			self.wMsg.changed = True
			self.wMsg.redraw()
			self.wIn.redraw()
		del help
		curses.curs_set(True)
