from setuptools import setup,find_packages

# TODO classifiers=[]

setup(
	name='retro-client',
	version='0.1.0',
	description='end2end encrypted terminal messenger (client)',
	url='https://github.com/lukwies/retro-client',
	author='Lukas Wiese',
	author_email='luken@gmx.net',
	license='GPLv3+',

	packages=find_packages(),

	install_requires=[
		'libretro',
	],

	# Create a globally accessable console script
	# named 'retro-client'
	entry_points={
		'console_scripts': [
			'retro-client=retro_client.main:main',
		],
	},
	classifiers=[
		"Development Status :: 3 - Alpha",
		"Environment :: Console",
		"Environment :: Console :: Curses",
		"Intended Audience :: Developers",
		"Intended Audience :: Education",
		"Intended Audience :: End Users/Desktop",
		"License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
		"Operating System :: POSIX",
		"Operating System :: POSIX :: Linux",
		"Programming Language :: Python :: 3.11",
		"Topic :: Communications",
		"Topic :: Communications :: Chat",
	]
)

