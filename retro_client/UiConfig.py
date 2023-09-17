import configparser
from os.path import join   as path_join
import logging


LOG = logging.getLogger(__name__)

"""\

This file contains all the User Interface settings.
There also is a file at ~/.retro/res/ui.conf holding
theses settings.


UiSettings uses the following files:

~/.retro/res/
   |__ ui.conf
   |__ img/
   |   |__ recv-message.png
   |   |__ friend-online.png
   |   |__ friend-offline.png
   |__ sounds/
       |__ recv-message.wav
       |__ sent-message.wav
       |__ recv-filemessage.wav
       |__ sent-filemessage.wav
       |__ friend-online.wav
       |__ friend-offline.wav



~/.retro/res/ui.conf

  [sounds]
  recv-message = True
  sent-message = True
  friend-online = True
  friend-offline = True

  [notify]
  enabled = True
  timeout = 5

"""
class UiConfig:

	# Directory/File names
	BASEDIR_NAME  = "res"
	HELPDIR_NAME  = "help"
	SOUNDDIR_NAME = "sounds"
	IMGDIR_NAME   = "img"
	CONFFILE_NAME = "ui.conf"

	# Used to access helpfiles
	HELP_NAMES = [	"main", "chat" ]

	# Used to access soundfiles
	SOUND_NAMES = [	"recv-message",
			"recv-filemessage",
			"sent-message",
			"sent-filemessage",
			"friend-online",
			"friend-offline" ]

	# Used to access images
	IMG_NAMES = [	"recv-message",
			"recv-filemessage",
			"friend-online",
			"friend-offline" ]

	def __init__(self, config):
		"""\
		Args:
		  config: libretro.Config
		"""
		self.resdir   = path_join(config.basedir, self.BASEDIR_NAME)
		self.helpdir  = path_join(self.resdir, self.HELPDIR_NAME)
		self.sounddir = path_join(self.resdir, self.SOUNDDIR_NAME)
		self.imgdir   = path_join(self.resdir, self.IMGDIR_NAME)
		self.conffile = path_join(self.resdir, self.CONFFILE_NAME)

		# [sounds]
		# This dictionary is to keep track if a a sound
		# should be played or not. Keys are the name of
		# the sound and the values are True or False.
		# By default, all sounds are enabled.
		self.snd_enabled = {
			key:True\
			for key in self.SOUND_NAMES
		}

		# [notify]
		# This dict is to keep track if a notification
		# shall be shown or not.
		self.notes_enabled = {
			key:True\
			for key in self.IMG_NAMES
		}
		self.notify_enabled = True
		self.notify_timeout = 5


	def load(self):
		"""\
		Read config file "resdir/ui.conf"

		Raises:
		  Exception: If failed to open/read config file
		"""
		try:
			LOG.debug("Loading UI configfile " + self.conffile)
			conf = configparser.ConfigParser()
			conf.read(self.conffile)

			# [sounds]
			for snd,enabled in self.snd_enabled.items():
				self.snd_enabled[snd] =\
					conf.getboolean('sounds', snd,
						fallback=enabled)
			# [notify]
			self.notify_timeout = conf.getint('notify', 'timeout',
					fallback=self.notify_timeout)
			self.notify_enabled = conf.getboolean('notify',
					'enabled', fallback=self.notify_enabled)

			return True
		except configparser.NoOptionError as e:
			raise Exception("UiConfig.load: "+str(e))
		except Exception as e:
			raise Exception("UiConfig.load: "+str(e))
			return False


	def res_path(self, file):
		"""\
		Return a path with the res path as prefix.
		"""
		return path_join(self.resdir, file)


	def help_path(self, name):
		"""\
		Get path to helpfile.
		Args:
		  name: One of the names in self.HELP_NAMES
		"""
		if name not in self.HELP_NAMES:
			raise ValueError("UiConfig: Unknown "\
				"help identifier '"+name+"'")
		return path_join(self.helpdir, name+".txt")


	def sound_path(self, name):
		"""\
		Get path to soundfile.
		Args:
		  name: One of the names in self.SOUND_NAMES
		"""
		if name not in self.SOUND_NAMES:
			raise ValueError("UiConfig: Unknown "\
				"sound '" + name + "'")
		return path_join(self.sounddir, name+".wav")


	def img_path(self, name):
		"""\
		Get path to imgfile.
		Args:
		  name: One of the names in self.IMG_NAMES
		"""
		if name not in self.IMG_NAMES:
			raise ValueError("UiConfig: Unknown "\
				"img '" + name + "'")
		return path_join(self.imgdir, name+".png")


	def is_sound_enabled(self, name):
		"""\
		Is given sound enabled?
		"""
		if not name in self.snd_enabled:
			return False
		else:	return self.snd_enabled[name]


	def set_sound_enabled(self, name, on=True):
		"""\
		En/disable playing sound with given name.
		Attr:
		  name: Name of sound (see self.SOUND_NAMES)
		  on:   True=On, False=Off, None=Set opposite
			of current state
		"""
		if name in self.snd_enabled:
			if on == None:
				self.snd_enabled[name] = \
					not self.snd_enabled[name]
			else:	self.snd_enabled[name] = on


	def is_notify_enabled(self, name):
		"""\
		Is enabled to send notification for given
		name (self.IMG_NAMES) ?
		"""
		if not name in self.notes_enabled:
			return False
		else:	return self.notes_enabled[name]


	def set_notify_enabled(self, name, on=True):
		"""\
		En/disable showing note with given name.
		Attr:
		  name: Name of note (see self.IMG_NAMES)
		  on:   True=On, False=Off, None=Set opposite
			of current state
		"""
		if name in self.notes_enabled:
			if on == None:
				self.notes_enabled[name] = \
					not self.notes_enabled[name]
			else:	self.notes_enabled[name] = on
