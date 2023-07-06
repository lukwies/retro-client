import logging as LOG

from os      import stat     as os_stat
from os.path import join     as path_join
from os.path import basename as path_basename
from base64  import b64encode,b64decode

from libretro.Config import RETRO_MAX_FILESIZE
from libretro.net    import TLSClient
from libretro.crypto import hash_sha256, random_buffer
from libretro.crypto import aes_encrypt_from_file
from libretro.crypto import aes_decrypt_to_file

from . ui.FileDownloadWindow import filesize_to_string

"""\
1) Get filepath
2) Get filesize
3) Calculate encrytped filesize
4) Generate fileid
5) Send 'file-upload', fileid,filesize to server
6) Store fileid,filepath,'upload' to fileevent_queue

"""

class FileInfo:
	"""\
	Temporary representation of file up/download
	"""
	def __init__(self, filepath, fileid=None,
			filesize=0):
		self.filepath = filepath
		self.filename = path_basename(filepath)
		self.fileid   = fileid

		if not self.fileid:
			# Generate fileid if not given
			idbuf = self.filename.encode()+random_buffer(16)
			self.fileid = hash_sha256(idbuf,True)[:32]


	def get_size(self):
		try:
			return os_stat(self.filepath).st_size
		except Exception as e:
			LOG.error("FileInfo.get_size('{}'): {}"\
				.format(self.filepath, e))
			return 0


class FileTransfer:
	"""\
	Handles all the file up/downloading.
	"""

	def __init__(self, gui):
		"""\
		Args:
		  gui: RetroGui
		"""
		self.gui        = gui
		self.cli        = gui.cli
		self.conf       = gui.cli.conf
		self.msgHandler = gui.cli.msgHandler
		self.msgStore   = gui.cli.msgStore


	def upload_file(self, friend, filepath):
		"""\
		Upload file to server and send 'file-message'
		to receiver of file.

		Args:
		  friend:   Receiver Friend object
		  filepath: Path to file

		NOTE: This is a thread function !!!
		"""
		file = FileInfo(filepath)
		filesize = file.get_size()

		self.gui.info("Uploading file {} ..."\
			.format(file.filename), on_logwin=True)

		# Encrypt/compress file
		try:
			key  = random_buffer(32)
			data = aes_encrypt_from_file(key, filepath)
		except Exception as e:
			self.gui.error("Failed to encrypt file '{}', {}"\
				.format(file.filename, e), on_logwin=True)
			return

		# Connect to fileserver
		conn = self.__connect()
		if not conn: return

		# Send initial packet (fileid and filesize)
		conn.send_dict({'type'   : 'file-upload',
				'fileid' : file.fileid,
				'size'   : len(data) })

		if not self.__recv_ok(conn):
			return

		# Upload encrytped file
		conn.send(data)

		if not self.__recv_ok(conn):
			return
		conn.close()

		# Send file-message to user
		file_dict = {
			'fileid'   : file.fileid,
			'filename' : file.filename,
			'key'      : b64encode(key).decode(),
			'size'     : filesize
		}
		msg,e2e_msg = self.cli.msgHandler.make_file_msg(
				friend,	file_dict)
		self.cli.send_dict(e2e_msg)

		self.gui.info("Sent 'file-message' to '"\
			+friend.name+"'")

		# Create message and store it to db.
		msg = self.msgHandler.get_message(
			self.cli.account.name,
			friend.name,
			"Sent file '{}' ({})".format(
			file.filename, filesize_to_string(filesize)))
		self.msgStore.add_msg(friend, msg)

		# Add message to conversation view
		if self.gui.chatView:
			self.gui.chatView.add_msg(msg)


	def download_file(self, friend, fileid, filename, key):
		"""\
		Download file from server, decrypt and store it.

		Args:
		  friend:   Sender Friend object
		  fileid:   Fileid
		  filename: Filename (not path!)
		  key:      Encryption key (base64)
		NOTE: This is a thread function !!!
		"""

		filepath = path_join(self.gui.conf.download_dir,
				filename)

		conn = self.__connect()
		if not conn: return

		# Send initial packet
		conn.send_dict({'type'   : 'file-download',
				'fileid' : fileid })

		# Must receive type=='ok' and 'size'
		res = self.__recv_ok(conn)
		if not res:
			conn.close()
			return

		filesize = res['size']
		data     = b''
		nrecv    = 0

		self.gui.debug("Download file={} id={} size={} sender={}"\
			.format(filename, fileid, filesize, friend.name))

		# Receive file contents
		while nrecv < filesize:
			buf = conn.recv(timeout_sec=self.conf.recv_timeout)
			if not buf: break
			data  += buf
			nrecv += len(buf)
		conn.close()

		if nrecv != filesize:
			self.gui.error("FileTransfer: Failed to download "\
				"'{}', stopped at {}/{}".format(filename,
				nrecv, filesize), on_logwin=True)
			return

		# Decrypt/Decompress and store to file
		try:
			key = b64decode(key)
			aes_decrypt_to_file(key, data, filepath)
		except Exception as e:
			self.gui.error("Failed to decrypt file"\
				" '{}': {}".format(filename, e),
				on_logwin=True)
			return

		self.gui.info("Downloaded '{}' ({})".format(
			filename, filesize_to_string(filesize)),
			on_logwin=True)

		# Set file to downloaded=1 in message store
		self.msgStore.set_file_downloaded(friend, fileid)

		# Reload chatview
		if self.gui.chatView:
			self.gui.chatView.load_chat(friend)
			self.gui.chatView.wMsg.redraw()
			self.gui.chatView.wIn.update_cursor()


	def __connect(self):
		#Connect to fileserver.
		cli = TLSClient(
			self.conf.server_address,
			self.conf.server_fileport,
			self.conf.server_hostname,
			self.conf.server_certfile)
		try:
			cli.connect()
			return cli
		except Exception as e:
			self.gui.error("Connect to fileserver, "\
				+ str(e), on_logwin=True)
			return None


	def __recv_ok(self, conn):
		# Wait for packet type == 'ok'
		# Return:
		#   msg: Received packet on success
		#   None: on error
		try:
			res = conn.recv_dict(['type'],
				timeout_sec=10)
			if not res:
				self.gui.error("FileServer: "\
					"receive timeout",
					on_logwin=True)
			elif res['type'] == 'error':
				self.gui.error("FileServer: "\
					+ res['msg'], on_logwin=True)
			elif res['type'] != 'ok':
				self.gui.error("FileTransfer: "\
					"Invalid response type '"\
					+ res['type'] + "'",
					on_lowin=True)
			else:
				return res
		except Exception as e:
			self.gui.error("FileServer: " + str(e))

		return None

