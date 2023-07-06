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

	packages=['retro_client'],

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

	python_requires='>=3.6',
)
