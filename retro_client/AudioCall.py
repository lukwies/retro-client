import json
import threading


from pyaudio import PyAudio, paInt16
from audioop import avg   as audioop_avg
from math    import sqrt  as math_sqrt
from time    import sleep as time_sleep
from io      import BytesIO
from base64  import b64encode

from libretro.protocol import Proto
from libretro.crypto   import random_buffer
from libretro.net      import TCPSocket


AUDIO_FORMAT    = paInt16 # Audio format
AUDIO_CHANNELS  = 1	  # Number of channels (1,2)
AUDIO_CHUNKSIZE = 1024	  # Number of chunks per buffer
AUDIO_FPS       = 16000  # Frame rate per second


"""\
Audio call handler.

"""
class AudioCall:
	"""\
	Implements audio calls.

	All methods, starting with "on_" are called by the
	main receive thread (RecvThread.py)
	"""

	# Size of call-id
	CALLID_SIZE   = 16  # In bytes
	CALLID_STRLEN = 32  # As string

	# Diffent states of an audiocall
	CLOSED  = 0     # Callwindow closed
	RINGING = 1     # Our 'phone' is ringing
	CALLING = 2     # We are calling someone
	TALKING = 3     # Call is established

	def __init__(self, gui):

		self.gui        = gui
		self.cli        = gui.cli
		self.evNotifier = gui.evNotifier

		self.friend  = None
		self.callid  = None
		self.callkey = None

		self.state       = self.CLOSED
		self.audioThread = None


	def closed(self):
		"""\
		Returns true if there's no audio call
		"""
		return self.state == self.CLOSED


	def on_incoming_call(self, friend, callid, callkey):
		"""\
		A Friend is calling us.
		This is called after receiving 'start-call'.
		Open the call window in RINGING state.
		"""
		if not self.closed():
			# Reject call if currently calling
			self.gui.info("Missed call from " + friend.name)
			self.cli.send_packet(Proto.T_REJECT_CALL, friend.id)
			return

		self.gui.info("Incoming call from " + friend.name)

		self.friend  = friend
		self.callid  = callid
		self.callkey = callkey
		self.state   = self.RINGING

		self.evNotifier.on_incoming_call(friend.name)
		self.gui.audioCallWindow.open(friend)


	def on_call_stopped(self, friend):
		"""\
		Friend stopped the call, let's close the
		audio call window.
		"""
		if not self.closed() and friend.id == self.friend.id:
			self.evNotifier.on_incoming_call(self.friend.name,
					start=False)
			self.gui.audioCallWindow.close()
			self.state = self.CLOSED
			self.gui.info("Call ended")


	def on_call_rejected(self, friend):
		"""\
		Friend rejected our call attempt, let's close
		the audio call window.
		"""
		if not self.closed() and friend.id == self.friend.id:
			self.evNotifier.on_outgoing_call(self.friend.name,
					start=False)
			self.gui.info(friend.name + " rejected your call")
			self.gui.audioCallWindow.close()
			self.state = self.CLOSED


	def on_call_accepted(self, friend):
		"""\
		Friend accepted our call, connect to audio server
		and start the audio/network thread.
		"""
		if not self.closed() and friend.id == self.friend.id:
			self.evNotifier.on_outgoing_call(self.friend.name,
					start=False)
			self.gui.info(friend.name + " accepted your call")
			self.gui.audioCallWindow.set_state(self.TALKING)
			self.__run_audio_call()


	def start_call(self, friend):
		"""\
		Send a 'start-call' message to given friend and
		open the AudioCallWindow in 'CALLING' state.
		This also generates the call credentials like
		callid and callkey.
		"""
		if not self.closed():
			return
			
		self.friend  = friend
		self.callid  = random_buffer(Proto.CALLID_SIZE*2, True)
#		self.callid  = random_buffer(self.CALLID_STRLEN, True)
		self.callkey = random_buffer(Proto.AES_KEY_SIZE)

		# Send e2e-encrypted 'start-call' message
		# containing the call-id and call-key.
		# NOTE: The callkey is base64 encoded
		call_data = {
			'callid'  : self.callid,
			'callkey' : b64encode(self.callkey)\
					.decode()
		}
		_,msg = self.cli.msgHandler.make_msg(friend,
				json.dumps(call_data),
				Proto.T_START_CALL)
		self.cli.send_packet(Proto.T_START_CALL, msg)
#		self.cli.send_dict(msg)
		self.gui.info("Calling "+friend.name+" ...")

		# Open the audio call window.
		self.state = self.CALLING
		self.gui.audioCallWindow.open(friend)
		self.evNotifier.on_outgoing_call(friend.name)


		# Start timeout thread to close call
		# afre
		th = CallTimeoutThread(self)
		th.start()
			


	def accept_call(self):
		"""\
		Accept current call attempt.
		Set the audio call window state to TALKING and
		run audio/network thread.
		"""
		if not self.closed():
			self.gui.info("Accepted call from "+self.friend.name)
			self.cli.send_packet(Proto.T_ACCEPT_CALL,
					self.cli.account.id,
					self.friend.id)
			self.gui.audioCallWindow.set_state(self.TALKING)
			self.evNotifier.on_incoming_call(self.friend.name, False)
			self.__run_audio_call()


	def stop_call(self):
		"""\
		Stop calling friend.
		Closes the audio/network thread if is running.
		"""
		if self.closed():
			return

		if self.state == self.CALLING:
			# We are calling someone, hang up!
			self.cli.send_packet(Proto.T_STOP_CALL,
				self.cli.account.id, self.friend.id)
			self.evNotifier.on_outgoing_call(self.friend.name, False)

		elif self.state == self.TALKING:
			# We are talking with someone,
			# stop the audio thread.
			if self.audioThread:
				self.audioThread.stop()
				self.audioThread.join()
				self.audioThread = None

		self.gui.audioCallWindow.close()
		self.state = self.CLOSED
		self.gui.info("Stopped call with " + self.friend.name)

	def reject_call(self):
		"""\
		Reject a friend's call and close audio call window.
		"""
		if not self.closed():
			self.cli.send_packet(Proto.T_REJECT_CALL,
				self.cli.account.id, self.friend.id)
			self.gui.audioCallWindow.close()
			self.evNotifier.on_incoming_call(self.friend.name, False)
			self.state = self.CLOSED
			self.gui.info("Rejected call from "+self.friend.name)


	def __run_audio_call(self):
		"""\
		Connect to the audio server and run the
		audio/network IO thread.
		"""
		if self.closed():
			return

		self.audioThread = AudioCallThread(self)
		self.audioThread.start()
		self.state = self.TALKING



class CallTimeoutThread(threading.Thread):
	"""\
	Montitor an audio call attempt and quits it if a
	wasn't accepted, rejected or stopped after 20 sec.
	"""
	def __init__(self, audioCall):
		super().__init__()
		self.audioCall = audioCall
		self.gui = audioCall.gui

	def run(self):
		"""\
		Check if someone accepted, rejected or stopped the call
		within 20 seconds. If not, close the call.
		"""
		for t in range(0, 20):
			if self.audioCall.state != AudioCall.CALLING:
				return

			time_sleep(1)
			if t > 13:
				with self.gui.winLock:
					w = self.gui.W['log']
					w.clear()
					w.bkgd(' ', self.gui.colors['Wb'])
					w.addstr("Stopping call in "\
						"{} seconds".format(20-t-1))
					w.refresh()

		# Timeout exceeded, stop call
		self.audioCall.stop_call()


class AudioCallThread(threading.Thread):
	"""\
	The AudioCallThread handles the audio recording,
	playing and transmission of audio calls.

	It is responsible for:

	- Recording audio data from microphone
	- Playing back audio data
	- Sending audio data
	- Receiving audio data
	- Encrypting audio data
	- Decrypting audio data

	Once it's started this thread will spawn two other
	threads: One for recording/sending audio data and
	another one for receiving/playing the audio data.

	Stop the thread with audioCallThread.stop()
	"""
	def __init__(self, audioCall):
		super().__init__()

		self.audioCall = audioCall
		self.gui = audioCall.gui

		self.fd         = TCPSocket()	# Network connection
		self.audio      = PyAudio()	# PyAudio instance
		self.recvThread = None		# Recv/play Thread
		self.sendThread = None		# Record/send Thread


	def run(self):
		"""\
		Connect to audioserver and start the record/send
		and the receive/play thread.
		"""
		if not self.__handshake():
			self.__cleanup()
			return

		self.sendThread = RecordSendThread(self)
		self.recvThread = ReceivePlayThread(self)

		self.sendThread.start()
		self.recvThread.start()

		# Waiting for threads to end
		self.recvThread.join()
		self.sendThread.join()

		# Causes exception?
		self.audio.terminate()

		self.__cleanup()
		self.fd.close('rw')


	def stop(self):
		"""\
		Stop the audio threads
		"""
		if self.recvThread:
			self.recvThread.done = True
		if self.sendThread:
			self.sendThread.done = True


	def __handshake(self):
		"""\
		Connects to the audio server and performs the
		handshake. We send the callid (16 bytes) to
		the audio server and wait for a response...
		The response is a 2 byte value being:

		  1  If calling partner joined and
		     the call can be started,

		  2  Nobody joined th call :(

		Return:
		   True on success, False on error
		"""

		self.gui.debug("Connecting to audio server {}:{}"\
				.format(self.gui.conf.server_address,
					self.gui.conf.server_audioport))
		try:
			self.fd = TCPSocket()
			self.fd.connect(
				self.gui.conf.server_address,
				self.gui.conf.server_audioport)
		except Exception as e:
			self.gui.error("Failed to connect to "\
				"audioserver, " + str(e))
			return False

		try:
			callid_bytes = bytes.fromhex(
					self.audioCall.callid)
			self.fd.send(callid_bytes)

			self.gui.debug("Sent callid {}...".format(
					self.audioCall.callid[:8]))

			res = self.fd.recv(1, timeout_sec=10)
			if not res: return False

			if res == b'1':
				self.gui.info("Calling partner joined,"\
					" call started ...")
				return True
			elif res == b'2':
				self.gui.warn("Calling partner didn't"\
					" join call within 10 seconds")
				return False
			else:
				self.gui.error("Got invalid response"\
					" ({})".format(res))
				return False

		except Exception as e:
			self.gui.error("Failed to do handshake "\
				"with audioserver: " + str(e))
			return False


	def __cleanup(self):
		"""\
		- Close the AudioCallWindow
		- Cleanup thread
		- Closing TCPSocket
		"""
		self.gui.info("Call with {} ended"\
			.format(self.audioCall.friend.name))

		self.gui.audioCallWindow.close()
		self.audioCall.state = AudioCall.CLOSED
		self.audioCall.audioThread = None



						

class RecordSendThread(threading.Thread):
	"""\
	Records and sends audio data.
	TODO: We only send audio data that is above agiven
	loudness level.
	"""
	def __init__(self, audioCallThread):
		super().__init__()
		self.parent    = audioCallThread
		self.fd        = self.parent.fd
		self.stream    = None
		self.done      = False


	def run(self):
		"""\
		Start record/send thread.
		"""
		self.audioCall.gui.debug("RecordSendThread started")

		try:
			self.stream = self.parent.audio.open(
					format=AUDIO_FORMAT,
					channels=AUDIO_CHANNELS,
					frames_per_buffer=AUDIO_CHUNKSIZE,
					rate=AUDIO_FPS,
					input=True)
		except Exception as e:
			self.parent.gui.error("RecordSendThread:"\
				" Failed to open stream: "+str(e))
			return

		while not self.done and not self.parent.recvThread.done:
			try:
				# Record and send audio chunk
				data = self.stream.read(AUDIO_CHUNKSIZE)
				self.fd.send(data)
			except Exception as e:
				self.parent.gui.error(
					"RecordSendThread: "+str(e))
				break

		self.parent.gui.debug("RecordSendThread stopped")
		self.parent.recvThread.done = True
		self.done = True

		self.stream.stop_stream()
		self.stream.close()



class ReceivePlayThread(threading.Thread):
	"""\
	Receives and plays audio data.
	"""
	def __init__(self, parent:AudioCallThread):
		super().__init__()
		self.parent    = parent
		self.fd        = parent.fd
		self.stream    = None
		self.done      = False

	def run(self):
		"""\
		Start receive/play thread.
		"""
		self.parent.gui.debug("ReceivePlayThread started")

		try:
			self.stream = self.parent.audio.open(
					format=AUDIO_FORMAT,
					channels=AUDIO_CHANNELS,
					frames_per_buffer=AUDIO_CHUNKSIZE,
					rate=AUDIO_FPS,
					output=True)
		except Exception as e:
			self.parent.gui.error("RecvPlayThread: "\
				"Failed to open stream: "+ str(e))
			return

		sndbuf  = BytesIO()
		silence = chr(0)*AUDIO_CHUNKSIZE*2


		while not self.done and not self.parent.sendThread.done:
			# Receive audio chunks and play them ...

			data = self.fd.recv(
					max_bytes=AUDIO_CHUNKSIZE*2,
					timeout_sec=1)

			if data == None:
				break
			elif data == False:
				continue
			elif data:
				sndbuf.write(data)

				if len(sndbuf.getvalue()) >= AUDIO_CHUNKSIZE*2:
					self.stream.write(
						sndbuf.read(AUDIO_CHUNKSIZE*2))
				else:
					self.stream.write(silence)

		self.parent.gui.debug("ReceivePlayThread stopped")
		self.parent.sendThread.done = True
		self.done = True

		self.stream.stop_stream()
		self.stream.close()


