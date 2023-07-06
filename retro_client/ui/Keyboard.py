import curses
import json

"""\
This class handles keyboard keys/shortcuts required by retro.
Example1:
	# Start curses screen and read keys from user.
	# Then store all keys to json file.
	kb = Keyboard()
	kb.read_keys_interactive('foo/bar/keys.json')
Example2:
	# Load json file (created by Example1) and use it...
	kb = Keyboard()
	try:
		kb.load_json('foo/bar/keys.json')
		print("CTRL+X : " + str(kb['CTRL_X']))
	except ...
"""

class Keyboard:
	CTRL_CHARS = "ABDEFGHIKLNOPRTUVWXY"
	CTRL_KEYS  = [] #['ENTER', 'SPACE']
	SHIFT_KEYS = ['ENTER'] #, 'PUP', 'PDOWN']
	OTHER_KEYS = [
		'ENTER', 'BACKSPACE', 'DELETE',
		'UP', 'DOWN', 'LEFT', 'RIGHT',
		'PUP', 'PDOWN']

	def __init__(self):
		# All curses 'special' keys.
		# The dictionary keys are the keynames as strings
		# the values are the numeric identifier of the key.
		self.keys = {}

	def exists(self, keyname):
		return True if keyname in self.keys\
			else False


	def __getitem__(self, keyname):
		"""\
		Get key identifier by name using [].
		Call this like:
			keys['CTRL_A']
		"""
		return self.keys[keyname]\
			if self.exists(keyname)\
			else None


	def load_json(self, path):
		"""\
		Load keys from json file.
		"""
		dct = json.load(open(path, "r"))
		self.keys = dct


	def save_json(self, path):
		"""\
		Save keys to json file.
		"""
		json.dump(self.keys, open(path, 'w'),
			indent=' ')


	def read_keys_interactive(self, save_path=None):
		"""\
		Creates a curses window and asks the user to type
		all keys required by retro. Theses keys are then
		stored as self.keys. If given save_path is not None,
		the keys are also stored as a json file.

		"""
		std = curses.initscr()
		curses.noecho()
		curses.curs_set(False)
		std.keypad(True)
		self.keys = {}

		def get_key(win, keys, keystr, prefix=None):
			# Ask user to type given key
			if prefix:
				keyname = prefix+" + "+keystr
				dictkey = prefix+"_"+keystr
			else:
				dictkey = keystr
				keyname = keystr

			win.clear()
			win.addstr("Please press '"+keyname+"'\n")
			while True:
				ch = win.getch()
				if ch in keys.values():
					used = [k for k,v in keys.items() if v==ch]
					win.addstr("Key is already used by '{}', "\
						"press another one...\n".format(
						used[0]))
					win.refresh()
				else:
					keys[dictkey] = ch
					break
			win.refresh()


		std.clear()
		std.addstr("In the following you are asked to enter some "\
			"keybord keys/shortcuts.\n")
		std.addstr("Please just do what you're told to do!!! ;-)\n")
		std.addstr("Press any key to start ...\n")
		std.refresh()

		try:
			std.getch()

			for c in Keyboard.CTRL_CHARS:
				get_key(std, self.keys, c, 'CTRL')

			for k in Keyboard.CTRL_KEYS:
				get_key(std, self.keys, k, 'CTRL')

			for k in Keyboard.SHIFT_KEYS:
				get_key(std, self.keys, k, 'SHIFT')

			for k in Keyboard.OTHER_KEYS:
				get_key(std, self.keys, k)

			curses.endwin()

			if save_path:
				self.save_json(save_path)
				print("Created keyboard file at " + save_path)

		except KeyboardInterrupt:
			curses.endwin()
			print("Interrupted")



#k = Keyboard()
#k.load_json('/home/peilnix/.retro/res/keyboard.json')

#print(k['ENTER'])
#print(ord('\n'))
#k.read_keys_interactive('keys.json')

#if k['CTRL_A']:
#	print(k['CTRL_A'])

