import logging
import threading

from libretro.protocol import *
from libretro.Friend import Friend
from libretro.FileTransfer import FileTransfer
from libretro.FileTransfer import filesize_to_string

LOG = logging.getLogger(__name__)

"""\
File Transmitting.

"""

class SendFileThread(threading.Thread):
	"""\
	Upload file to fileserver and send file message (T_FILEMSG)
	to friend (receiver of file).
	"""
	def __init__(self, gui, friend:Friend, filepath:str):
		"""\
		Args:
		  gui:      RetroGui instance
		  friend:   File receiver (Friend)
		  filepath: Path to file that should be sent
		"""
		super().__init__()
		self.gui       = gui
		self.cli       = gui.cli
		self.friend    = friend
		self.filepath  = filepath
		self.fileTrans = FileTransfer(self.cli)

	def run(self):
		# Upload file to fileserver.
		try:
			filename,filesize = self.fileTrans\
				.upload_file(self.friend,
					self.filepath)
		except Exception as e:
			self.gui.error("Upload file: "+str(e),
					on_logwin=True)
			return

		self.gui.info("Sent file to '"+self.friend.name+"'")

		# Create message and store it to db.
		msg = self.cli.msgHandler.get_message(
			self.cli.account.name,
			self.friend.name,
			"Sent file '{}' ({})".format(
			filename, filesize_to_string(filesize)))
		self.cli.msgStore.add_msg(self.friend, msg)

		# Add message to conversation view
		if self.gui.chatView:
			self.gui.chatView.add_msg(msg)



class RecvFileThread(threading.Thread):
	"""\
	Download file from fileserver.
	"""
	def __init__(self, gui, friend:Friend, fileidx:str,
			filename:str, key:bytes):
		"""\
		Args:
		  gui:      RetroGui
		  friend:   Sender of file (Friend)
		  fileidx:  Fileid as hex string (len=32)
		  filename: Name of file to download
		  key:      File decryption key (32 byte)
		"""
		super().__init__()
		self.gui       = gui
		self.cli       = gui.cli
		self.friend    = friend
		self.fileidx   = fileidx
		self.filename  = filename
		self.key       = key
		self.fileTrans = FileTransfer(self.cli)


	def run(self):
		# Download file from fileserver
		try:
			filename,filesize = self.fileTrans\
				.download_file(
					self.friend,
					bytes.fromhex(self.fileidx),
					self.filename,
					self.key)

		except Exception as e:
			self.gui.error("Download file: "+str(e),
					on_logwin=True)
			return


		self.gui.info("Downloaded '{}' ({})".format(
			filename, filesize_to_string(filesize)),
			on_logwin=True)

		try:
			# Set file to downloaded=1 in message store
			self.cli.msgStore.set_file_downloaded(
					self.friend, self.fileidx)
		except Exception as e:
			self.gui.error("MsgStore: "+str(e))
			return

		# Reload chatview
		if self.gui.chatView:
			self.gui.chatView.load_chat(self.friend)
			self.gui.chatView.wMsg.redraw()
			self.gui.chatView.wIn.update_cursor()
