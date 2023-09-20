import plyer
from plyer import notification

from libretro.FileTransfer import filesize_to_string

class EventNotifier:
	"""\
	The EventNotifier defines some functions that
	are called if certain events occur ...

	The following events are defined:

	  'recv-message'
	  'recv-filemessage'
	  'sent-message'
	  'sent-filemessage'
#	  'incoming-call'
#	  'outgoing-call'
	  'friend-online'
	  'friend-offline'
	"""
	def __init__(self, gui):
		self.gui    = gui
		self.uiconf = gui.uiconf
		self.aplay  = gui.audioPlayer


	def on_recv_message(self, friend_name):
		"""\
		Called after receiving a chat message.
		It plays the 'recv-message' sound and
		raises a desktop notification.
		"""
		body = "<span style='color:red'>HEY</span>"

		self.aplay.play('recv-message')
		self.__notify(
			title="Got message from "+friend_name,
			body="...",
			img_name='recv-message', timeout=10)


	def on_recv_filemessage(self, friend_name, file_name,
				file_size):
		"""\
		Called after receiving a file message.
		It plays the 'recv-filemessage' sound and
		raises a desktop notification.
		"""
		body = file_name + " (" \
			+ filesize_to_string(file_size) \
			+ ")"
		self.aplay.play('recv-message')
		self.__notify(
			title="Got file from "+friend_name,
			body=body, img_name='recv-filemessage',
			timeout=30)


	def on_sent_message(self, friend_name, is_filemsg=False):
		"""\
		Called whenever a chat message has been sent.
		Plays the 'send-message' sound.
		"""
		self.aplay.play(
			'recv-filemessage' \
			if is_filemsg \
			else 'recv-message')


#	def on_incoming_call(self, friend_name, start=True):
#		"""\
#		Called if an incoming audio call is started
#		or ended. If the call started (start=True),
#		play the 'incoming-call' sound and raise a
#		desktop notification. If call ended, stop
#		the sound playing.
#		"""
#		if start:
#			self.aplay.play('incoming-call')
#			self.__notify(
#				title='Incoming call ...',
#				body=friend_name+' is calling you!',
#				img_name='incoming-call',
#				timeout=12)
#		else:	self.aplay.stop('incoming-call')
#
#
#	def on_outgoing_call(self, friend_name, start=True):
#		"""\
#		Called if an outgoing audio call is started
#		or ended. If the call started (start=True),
#		play the 'outgoing-call' sound, if it has
#		ended stop that sound again.
#		"""
#		if start:
#			self.aplay.play('outgoing-call',
#					n_times=99)
#		else:	self.aplay.stop('outgoing-call')


	def on_friend_status_changed(self, friend_name,
			status='online'):
		"""\
		Called if the status of a friend changed to
		online or offline (status). This will play
		the 'friend-online'/'friend-offline' sound
		and send a desktop notification.
		"""
		if status in ('online','offline'):
			ev_name = 'friend-'+status
			self.__notify(
				title=friend_name+" is "+status,
				img_name=ev_name,
				timeout=5)
			self.aplay.play(ev_name)


	def __notify(self, title="", body='',
			img_name='', timeout=5):
		"""\
		Send a desktop notification.
		Args:
		  title:    Notification title text
		  body:     The bodytext of the notification
		  img_name: Imagename to use as notification
			    icon (see UiConfig.py)
		"""
		if self.uiconf.notify_enabled:
			try:
				img_path = self.uiconf.img_path(img_name)
				notification.notify(
					app_name='retro-client',
					title=title,
					message=body,
					app_icon=img_path,
					timeout=timeout)
			except Exception as e:
				self.gui.error("Notify: " + str(e))
