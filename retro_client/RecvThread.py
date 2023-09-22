import curses
import logging
import threading
import select
import time

from libretro.protocol import *
from libretro.Friend import *

LOG = logging.getLogger(__name__)


class RecvThread(threading.Thread):
	"""\
	After connecting to the retro server, the receive thread is
	started. It handles all incoming messages.
	"""
	def __init__(self, gui):
		super().__init__()

		self.gui          = gui
		self.cli          = gui.cli
		self.msgHandler   = gui.cli.msgHandler
		self.msgStore     = gui.cli.msgStore
		self.recv_timeout = gui.conf.recv_timeout
		self.done         = False
		self.start_time   = 0

		# Sometimes the receive thread needs information
		# - about how do deal with some packet types -
		# from the outside. This is done using a dictionary.
		self.info = {}


	def add_info(self, key, data):
		"""\
		Add information to the info 'pipe'.

		Args:
		  key:  Info key
		  data: Info data
		"""
		self.info[key] = data


	def get_info(self, key):
		"""\
		Get info data by key.
		NOTE: This will delete the info entry.

		Args:
		  key: Info key
		Return:
		  Info data or None if key not found
		"""
		if key not in self.info:
			self.gui.error("RecvThread.get_info: "\
				"No such key '{}'".format(key))
			return None
		return self.info.pop(key)


	def run(self):
		"""\
		Run the receive thread.
		To stop the thread set recvThread.done=True
		and call recvThread.join().
		"""
		self.start_time = time.time()

		while not self.done:

			try:
				# Wait for incoming messages. If pckt is
				# None, receive timeout exceeded.
				pckt = self.cli.recv_packet(
					timeout_sec=self.recv_timeout)
			except Exception as e:
				self.gui.error(str(e))
				break

			if pckt == False:
				continue
			elif not pckt:
				break
			elif pckt[0] == Proto.T_CHATMSG or\
			   pckt[0] == Proto.T_FILEMSG:
				# Chat/File message
				self.__handle_chat_msg(pckt)

			elif pckt[0] in (Proto.T_FRIEND_ONLINE,
					 Proto.T_FRIEND_OFFLINE,
					 Proto.T_FRIEND_UNKNOWN):
				# Friend status (online/offline/..)
				self.__set_friend_status(pckt)

			elif pckt[0] == Proto.T_PUBKEY:
				# Incoming public key (add new friend)
				self.__add_friend(pckt)

			elif pckt[0] == Proto.T_ERROR:
				# Server error message
				self.gui.error("Server: {}"\
					.format(pckt[1].decode()))
			else:
				# Invalid msg type
				self.gui.error("RecvThread: "\
					"Got invalid msgtype "\
					"("+str(pckt[1])+")")

		# We are not connected anymore, update status.
		self.gui.error("Server closed connection")
		self.gui.connected = False
		self.cli.close()
		self.gui.redraw()


	def __handle_chat_msg(self, pckt):
		"""\
		Called after message type 'message' or 'file-message'
		received. This will decrypt the message, store it into
		the message database and refresh the ui.
		"""
		if not pckt[1]:
			LOG.error("handle_chat_msg: No payload!")
			return False

		try:
			friend,msg = self.msgHandler.decrypt_msg(pckt[0],pckt[1])
		except Exception as e:
			self.gui.error("MsgHandler: "+str(e))
			return False

		# Store message to sqlite db. Set unseen=1.
		msg['unseen'] = 1
		msg['id'] = self.msgStore.add_msg(friend, msg)
		friend.unseen_msgs += 1

		if self.gui.chatView:
			# If user is currently chatting with sender,
			# update the chatmessage view.
			cV = self.gui.chatView
			if cV.friend and cV.friend.name == friend.name:
				cV.add_msg(msg)
		else:
			# We are in mainview, update the sidebar
			self.gui.sidebar.changed = True
			self.gui.sidebar.redraw()

		# Execute message receive event
		if pckt[0] == Proto.T_CHATMSG:
			self.gui.evNotifier.on_recv_message(friend)
		elif pckt[0] == Proto.T_FILEMSG:
			self.gui.evNotifier.on_recv_filemessage(
				friend, msg['filename'], msg['size'])


	def __set_friend_status(self, pckt):
		"""\
		Handle received 'friend-status' message and set
		the according friends status (ONLINE|OFFLINE).
		This will update the sidebar window since it shows
		the online/offline state of a friend.
		"""
		friend_id  = pckt[1]
		status_str = Proto.friend_status_str(pckt[0])

		# Check if user is one of our friends.
		friend = self.cli.account.get_friend_by_id(friend_id)
		if not friend:
			self.gui.warn("Got status of unknown "\
				"user '{}' ({})".format(
				friend_id.hex(), status_str))
			return

		# Update friend status
		if pckt[0] == Proto.T_FRIEND_UNKNOWN:
			friend.status = Friend.UNKNOWN
			self.gui.sidebar.changed = True
			self.gui.warn("Server doesn't know your "\
				"friend '{}' ({})".format(
				friend.name, friend.id))

		else:
			if pckt[0] == Proto.T_FRIEND_OFFLINE:
				friend.status = Friend.OFFLINE
				self.gui.sidebar.changed = True

			elif pckt[0] == Proto.T_FRIEND_ONLINE:
				friend.status = Friend.ONLINE
				self.gui.sidebar.changed = True

			# Execute friend status notification.
			# We'll only notify if the recvthread is
			# already running more than 5 seconds to
			# avoid getting a lot of events each time
			# starting the retro-client.
			if time.time() - self.start_time > 5:
				self.gui.evNotifier.on_friend_status_changed(
						friend, status_str)


		# If we're in mainview, redraw the sidebar
		if not self.gui.chatView:
			self.gui.sidebar.redraw()


	def __add_friend(self, pckt):
		"""\
		Add a new friend to current retro account.
		This method is called after receiving T_PUBKEY.

		NOTE: Requires the friends name to be set
		      in self.info (key='friendname').

		Args:
		  pckt: T_PUBKEY, data=userid,pembuf
		"""
		if not pckt[1]:
			self.gui.error("RecvThread.add_friend:"\
				" No data in T_PUBKEY")
			return

		username = self.get_info('friendname')
		if not username: return

		userid = pckt[1][:8]
		pembuf = pckt[1][8:]

		try:
			# Add friend to account
			self.cli.account.add_friend(
				userid,	username, pembuf)

		except Exception as e:
			self.gui.error("Failed to add friend"\
				" '{}', {}".format(username, e))
			LOG.error("__add_friend: "+str(e))
			return

		# Update user interface
		self.gui.sidebar.reset_friends()
		self.gui.info("You have a new friend ({})"\
			.format(username))
		self.gui.redraw(force=True)


	def __get_friend_from_msg(self, pckt):
		"""\
		Get friend instance referring to userid in given
		packet (first 8 bytes).
		"""
		if not pckt[1]:
			return None
		else:
			friend_id = pckt[1][:8]
			return self.cli.account.get_friend_by_id(friend_id)

