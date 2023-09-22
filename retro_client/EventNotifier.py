import plyer
import threading
from plyer import notification
from os.path import join as path_join

from libretro.FileTransfer import filesize_to_string

class EventNotifier:
	"""\
	The EventNotifier shows a desktop notification and/or
	plays a sound whenever a certain event occurs.

	The following files are required:

	 ~/.retro/res/
	   |__ img/
	   |   |__ friend-offline.png
	   |   |__ friend-online.png
	   |   |__ recv_filemessage.png
	   |   |__ recv-message.png
	   |__ sounds/
	       |__ friend-offline.wav
	       |__ friend-online.wav
	       |__ recv_filemessage.wav
	       |__ recv-message.wav

	"""

	# Events
	ON_RECV_MSG	  = 0	# Incoming message
	ON_RECV_FILEMSG	  = 1	# Incoming file message
	ON_FRIEND_ONLINE  = 2	# Friend is online
	ON_FRIEND_OFFLINE = 3	# Friend is offline

	# Resolves event id to name
	EV_NAMES = {
		ON_RECV_MSG : "recv-message",
		ON_RECV_FILEMSG : "recv-filemessage",
		ON_FRIEND_ONLINE : "friend-online",
		ON_FRIEND_OFFLINE : "friend-offline"
	}


	def __init__(self, gui):
		self.gui = gui
		self.snd_enabled = True
		self.notes_enabled = True

		resdir       = path_join(gui.conf.basedir, "res")
		self.snd_dir = path_join(resdir, "sounds")
		self.img_dir = path_join(resdir, "img")


	def on_recv_message(self, friend):
		self.__notify(self.ON_RECV_MSG,
			title="Got message from "+friend.name,
			body="...", timeout=8)
		self.__play_sound(self.ON_RECV_MSG)

	def on_recv_filemessage(self, friend, file_name,
				file_size):
		fs = filesize_to_string(file_size)
		self.__notify(self.ON_RECV_FILEMSG,
			title="Got file from "+friend.name,
			body=file_name+" ("+fs+")",
			timeout=30)
		self.__play_sound(self.ON_RECV_FILEMSG)

	def on_friend_status_changed(self, friend, status):
		event = self.ON_FRIEND_ONLINE if status=="online"\
				else self.ON_FRIEND_OFFLINE
		self.__notify(event,
			title=friend.name+" is "+status,
			timeout=5)
		self.__play_sound(event)


	def __notify(self, event, title="", body='', timeout=5):
		"""\
		Send a desktop notification.
		Args:
		  event:    Event (self.ON_...)
		  title:    Notification title text
		  body:     The bodytext of the notification
		  timeout:  Timeout in seconds
		"""
		if self.notes_enabled:
			ev_name = self.EV_NAMES[event]
			imgpath = path_join(self.img_dir, ev_name+".png")
			try:
				notification.notify(
					app_name='retro-client',
					title=title,
					message=body,
					app_icon=imgpath,
					timeout=timeout)
			except Exception as e:
				self.gui.error("Notify: " + str(e))


	def __play_sound(self, event):
		"""\
		Play sound of given event
		"""
		if self.snd_enabled:
			try:
				ev_name = self.EV_NAMES[event]
				sndpath = path_join(self.snd_dir, ev_name+".wav")
				t = PlayAudioThread(self.gui.pyaudio, sndpath)
				t.start()
			except Exception as e:
				self.gui.error("play_sound: "+str(e))


class PlayAudioThread(threading.Thread):
	"""\
	Wav sound play thread.

	This thread opens a soundfile and plays it.
	"""
	def __init__(self, pyAudio, filepath):
		"""\
		Args:
		  pyAudio:  pyaudio instance
		  filepath: Path to wav file
		"""
		super().__init__()
		self.pyaudio  = pyAudio
		self.filepath = filepath


	def run(self):
		wf = wave.open(self.filepath, 'rb')
		stream = self.pyaudio.open(
			format=self.pyaudio.get_format_from_width(
				wf.getsampwidth()),
			channels=wf.getnchannels(),
			rate=wf.getframerate(),
			output=True)

		data = wf.readframes(2048)
		while not self.done and data != b'':
			stream.write(data)
			data = wf.readframes(2048)

		wf.close()
		stream.stop_stream()
		stream.close()

