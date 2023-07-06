import curses
import logging as LOG
import threading
import select
from libretro.Friend import *


class RecvThread(threading.Thread):
	"""\
	After connecting to the retro server, the receive thread is
	started. It handles all incoming messages.
	"""
	def __init__(self, gui):
		super().__init__()

		self.gui  = gui
		self.cli  = gui.cli
		self.recv_timeout = gui.conf.recv_timeout
		self.done = False


	def run(self):
		"""
		Run the receive thread.
		To stop the thread set recvThread.done=True
		and call recvThread.join().
		"""
		while not self.done:

			try:
				# Wait for incoming messages. If res is
				# None, receive timeout exceeded.
				res = self.cli.recv_dict(
					timeout_sec=self.recv_timeout)
				if not res: continue

			except Exception as e:
				self.gui.error("Recv: " + str(e))
				break

			msg_type = res['type']

			if msg_type == 'message' or\
			   msg_type == 'file-message':
				# Chat/File message
				self.__handle_chat_msg(res)
			elif msg_type == 'friend-status':
				# Friend status (online/offline/..)
				self.__set_friend_status(res)
			elif msg_type == 'error':
				# Server error message
				self.gui.error("Server: {}"\
					.format(res['msg']))
			else:
				# Invalid msg type
				self.gui.error("RecvThread: "\
					"Got invalid msgtype "\
					"'"+res['type']+"'")

		# We are not connected anymore, update status.
		self.gui.connected = False
		self.cli.close()
		self.gui.redraw()


	def __handle_chat_msg(self, msg):
		"""
		Called after message type 'message' or 'file-message'
		received.
		"""
		# Get friend by sender name (msg['from'])
		friend = self.cli.account.get_friend_by_id(msg['from'])
		if not friend:
			self.gui.warn("Got message from unknown "\
				"sender '{}'".format(msg['from']))
			return False

		self.gui.info("Got {} from {}".format(
				msg['type'], friend.name))

		# Decrypt message
		try:
			msg = self.cli.msgHandler.decrypt_msg(msg)
		except Exception as e:
			self.gui.error("Failed to decrypt msg "\
				"from {}, {}".format(friend.name, e))
			return False

		# Store message to sqlite db. Set unseen=1.
		msg['unseen'] = 1
		self.cli.msgStore.add_msg(friend, msg)
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


	def __set_friend_status(self, msg):
		"""
		Handle received 'friend-status' message and set
		the according friends status (ONLINE|OFFLINE).
		This will update the sidebar window since it shows
		the online/offline state of a friend.
		"""
		status_str = msg['status']

		# Check if user is one of our friends.
		friend = self.cli.account.get_friend_by_id(msg['user'])
		if not friend:
			self.gui.warn("Got status of unknown "\
				"user '{}' ({})".format(msg['user'],
				status_str))
			return False

		# Update friend status
		if status_str == 'unknown':
			self.gui.warn("Server doesn't know your "\
				"friend '{}' ({})".format(
				friend.name, friend.id))
			friend.status = Friend.UNKNOWN
			self.gui.sidebar.changed = True
		elif status_str == 'offline':
			friend.status = Friend.OFFLINE
			self.gui.sidebar.changed = True
		elif status_str == 'online':
			friend.status = Friend.ONLINE
			self.gui.sidebar.changed = True

		# If we're in mainview, redraw the sidebar
		if not self.gui.chatView:
			self.gui.sidebar.redraw()


