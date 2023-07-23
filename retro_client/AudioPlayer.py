import logging
import threading
import pyaudio
import wave
import time
import sys

from os      import listdir  as os_listdir
from os.path import splitext as path_splitext
from os.path import exists   as path_exists


LOG = logging.getLogger(__name__)

class AudioPlayer:
	"""\
	Audio Player for playing wav files.
	"""
	def __init__(self, gui):
		"""\
		Init audio player
		Args:
		  gui: RetroGui context
		"""
		super().__init__()
		self.gui    = gui
		self.uiconf = gui.uiconf
		self.snddir = self.uiconf.sounddir

		# A dictionary with the filename (withou extension)
		# as key and the filepath as value.
		self.sounds = {}

		# A dictionary to keep track of currently playing
		# sounds. Keys are soundnames and values are
		# AudioPlayThreads.
		self._playing = {}
		self._playingLock = threading.Lock()

		# Interface to pyaudio
		self._pyaudio = pyaudio.PyAudio()


	def load_sound_files(self):
		"""\
		Load all sound files from the sound directory
		(~/.retro/res/sounds/).

		Raise:
		  Exception: If failed to load any sound
		Return:
		  True:  If soundfiles could be found
		  False: If had any exceptions or no files found
		"""

		LOG.debug("Looking for sounds "\
			"in {}/ ...".format(self.snddir))

		for sound in self.uiconf.SOUND_NAMES:
			try:
				path = self.uiconf.sound_path(sound)
				LOG.debug("Adding sound "+sound)
				self.add_sound(sound, path)

			except FileNotFoundError as e:
				LOG.warning(str(e))

			except Exception as e:
				raise Exception("SoundPlayer: "\
					 + str(e))

		if not self.sounds:
			raise Exception("SoundPlayer: Couldn't"\
				" find any sounds")


	def add_sound(self, snd_name, path):
		"""\
		Add a sound to the player.

		Args:
		  snd_name:  Unique identifier of the sound
		  path:        Path to soundfile

		Raises:
		  KeyError:          soundname already exists
		  ValueError:        invalid file extension (.wav or .wave)
		  FileNotFoundError: soundfile not found
		"""

		_,ext = path_splitext(path)

		if ext.lower() not in ('.wav', '.wave'):
			raise ValueError("Invalid soundfile extension '{}"\
				.format(ext))
		elif snd_name in self.sounds:
			raise KeyError("Sound '{}' already exists"\
				.format(snd_name))
		elif not path_exists(path):
			raise FileNotFoundError("Soundfile '{}' "\
				"not found".format(path))
		else:
			self.sounds[snd_name] = path


	def play(self, snd_name, n_times=1, timeout_sec=None,
			repeat_delay=None):
		"""\
		Play the sound with the given name.

		NOTE: The sound will only be played if given
                      name exists in self.sounds and it's not
		      playing at the moment. otherwise nothing
		      will happen.
		Args:
		  snd_name:	Name of sound (key in self.sounds)
		  n_times:	How many times to replay the sound
				0/None = Forever (Default=1)
		  timeout_sec:  Maximal number of seconds to play this
				sound (None/0=No timeout).
		  repeat_delay: Seconds to wait between single replays.
				None=0 (can be decimal)
		"""
		if snd_name in self.sounds and\
		   snd_name not in self._playing and\
		   self.uiconf.is_sound_enabled(snd_name):

			try:
				play = AudioPlayThread(
					self.gui, self,
					snd_name, n_times,
					timeout_sec,
					repeat_delay)

				with self._playingLock:
					self._playing[snd_name] = play

				play.start()
			except Exception as e:
				self.gui.error("AudioPlayer.play: "+str(e))


	def playing(self, snd_name=None):
		"""\
		Returns True if there's any sound playing.
		If a sound name is given, just look if that
		sound is playing.
		"""
		if snd_name:
			return snd_name in self._playing
		else:	return len(self._playing) > 0


	def stop(self, snd_name):
		"""\
		Stop currently playing sound.
		"""
		if snd_name in self._playing:
			self._playing[snd_name].stop()


	def stop_all(self):
		"""\
		Stop all playing threads.
		"""
		for playThread in self._playing.values():
			playThread.stop()


	def get_sounds(self):
		"""\
		Get names of all stored sounds.
		"""
		return list(self.sounds.keys())


	def get_playing(self):
		"""\
		Get names of currently playing sounds.
		"""
		return list(self._playing.keys())


	def __del__(self):
		"""\
		Make sure pyaudio is terminated properly
		if WavPlayer is detroyed.
		"""
		self._pyaudio.terminate()



class AudioPlayThread(threading.Thread):
	"""\
	Wav sound play thread.

	This thread opens a soundfile and plays it.
	"""
	def __init__(self,
			gui,
			audioPlayer,
			snd_name,
			n_times=1,
			timeout_sec=None,
			repeat_delay=None):
		"""\
		Args:
		  gui:		RetroGui instance
		  audioPlayer:  Instance of AudioPlayer
		  snd_name:	Name of sound (key in self.sounds)
		  n_times:	How many times to replay the sound
				0/None = Forever (Default=1)
		  timeout_sec:  Maximal number of seconds to play this
				sound (None/0=No timeout).
		  repeat_delay: Seconds to wait between single replays.
				None=0 (can be decimal)
		"""
		super().__init__()

		self.gui          = gui
		self.audioPlayer  = audioPlayer
		self.__pyaudio    = audioPlayer._pyaudio
		self.snd_name     = snd_name
		self.snd_file     = audioPlayer.sounds[snd_name]
		self.n_times      = n_times
		self.timeout_sec  = timeout_sec
		self.repeat_delay = repeat_delay
		self.done         = True


	def run(self):
		"""\
		Open soundfile, init stream and play sound.
		"""
		try:
			wf     = wave.open(self.snd_file, 'rb')
			stream = self.__pyaudio.open(
				format=self.__pyaudio.get_format_from_width(
					wf.getsampwidth()),
				channels=wf.getnchannels(),
				rate=wf.getframerate(),
				output=True)
		except Exception as e:
			self.gui.error("AudioPlayThread.run: " + str(e))
			return

		self.done = False
		nplays    = 0
		tstart    = time.time()

		while not self.done:

			try:
				data = wf.readframes(2048)
				while not self.done and data != b'':
					stream.write(data)
					data = wf.readframes(2048)

				nplays += 1
			except Exception as e:
				self.gui.error("AufioPlayThread: "\
					+ str(e))
				break

			if self.n_times and\
				nplays >= self.n_times:
				# Reached max repeats
				break
			elif self.timeout_sec and\
				time.time()-tstart >= self.timeout_sec:
				# Reached timeout
				break
			else:
				# Reset wavfile read pointer and replay.
				# If a repeat delay is set, wait that
				# number of seconds before replaying.
				if self.repeat_delay:
					time.sleep(self.repeat_delay)
				wf.rewind()
		wf.close()
		stream.stop_stream()
		stream.close()

		# Remove this thread from audioPlayer._playing dictionary
		with self.audioPlayer._playingLock:
			self.audioPlayer._playing.pop(self.snd_name)


	def stop(self):
		"""\
		Stop playing thread.
		"""
		self.done = True

"""\
import time
player = AudioPlayer()

player.add_sound('bottle', 'bottle.wav')
player.add_sound('doorbell', 'doorbell.wav')

player.play('bottle', 3, repeat_delay=.5) #, 1)
player.play('doorbell') #, 2)

#print(player.get_playing())
#player.stop('bottle')
#time.sleep(1)
#player.stop_all()
#print(player.get_playing())

while player.playing():
	print(player.get_playing())
	time.sleep(1)

print(player.get_playing())
"""
