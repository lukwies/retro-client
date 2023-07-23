import sys
import logging

from os.path import join as path_join
from os.path import exists as path_exists
from os.path import expanduser as path_expndusr
from getpass import getpass
from getopt  import getopt, GetoptError

from libretro.RetroClient import *
from libretro.Account import chose_account_name
from libretro.AccountCreator import AccountCreator

from . ui.Keyboard import *
from . RetroGui import RetroGui

LOG = logging.getLogger(__name__)

HELP="""\
  retro-client

  Calling retro without any arguments, the user is asked to select
  an account (if there are more than one) and the client interface
  will be started.

  -h, --help                    Show this helptext
  -v, --version                 Show retrochat version

  -u, --user=NAME		Set username

  --create-account=REGKEYFILE	Create new retro account
  --init-keyboard		Initialize keyboard keys/shortcuts
"""

def check_keyboard_config(client, overwrite=False):
	# Before starting, check if we have a keyboard
	# config file at ~/.retro/res/keyboard.json.
	# If not, open a curses window and ask user to
	# press all of the keys used by retro and
	# create the keyboard config file.
	path = path_join(client.conf.basedir,
			"res/keyboard.json")
	if overwrite or not path_exists(path):
		kb = Keyboard()
		kb.read_keys_interactive(path)


def main():
	argv   = sys.argv[1:]
	client = RetroClient()
	user   = None


	if not path_exists(client.conf.basedir):
		print("Please install retro first")
		return

	check_keyboard_config(client)

	try:
		opts,rem = getopt(argv, 'hu:',
			['help', 'user=', 'create-account=',
			 'init-keyboard'])

	except GetoptError as ge:
		print('Error: {}'.format(ge))
		return

	for opt,arg in opts:
		if opt in ('-h', '--help'):
			print(HELP)
			return True

		elif opt in ('-u', '--user'):
			# Set username
			user = arg

		elif opt == '--create-account':
			# Create a new retro account
			AccountCreator().create_account(arg)
			return True

		elif opt == '--init-keyboard':
			# Init keyboard
			check_keyboard_config(client, True)
			return True


	# If user isn't set, print a list with all available
	# accounts and let the user select one.
	if not user:
		user = chose_account_name()
		if not user:
			print("Run with '--create-account' "\
				"to create one")
			return False

	# Get user account password
	passw = getpass("Password for '{}': ".format(user))


	# Init gui and run
	gui = RetroGui()

	try:
		gui.load(user, passw)
	except Exception as e:
		print(e)
		return False

	gui.run()

	return True


if __name__ == '__main__':
	main()
