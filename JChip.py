from __future__ import print_function

import socket 
import sys
import time
import datetime
import atexit
import math
import subprocess
import re
from multiprocessing import Process, Queue
from Queue import Empty

DEFAULT_PORT = 53135
DEFAULT_HOST = socket.gethostbyname(socket.gethostname())
if DEFAULT_HOST == '127.0.0.1':
	reSplit = re.compile('[: \t]+')
	try:
		co = subprocess.Popen(['ifconfig'], stdout = subprocess.PIPE)
		ifconfig = co.stdout.read()
		for line in ifconfig.split('\n'):
			line = line.strip()
			try:
				if line.startswith('inet addr:'):
					fields = reSplit.split( line )
					addr = fields[2]
					if addr != '127.0.0.1':
						DEFAULT_HOST = addr
						break
			except:
				pass
	except:
		pass

q = None
listener = None

def socketSend( s, message ):
	sLen = 0
	while sLen < len(message):
		sLen += s.send( message[sLen:] )

def socketByLine(s):
	buffer = s.recv( 4096 )
	while 1:
		nl = buffer.find( '\n' )
		if nl >= 0:
			yield buffer[:nl+1]
			buffer = buffer[nl+1:]
		else:
			more = s.recv( 4096 )
			if more:
				buffer = buffer + more
			else:
				break
	if buffer:
		yield buffer
		
def Server( q, HOST, PORT, startTime ):
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.bind((HOST, PORT))
	
	bufferedSecs = 3	# the time interval that we will ignore a read of the same tag.
	bufferedTags = {}	# all tags read in the last bufferedSecs.
	
	lastTime = datetime.time()
	lastTag = ''
	while 1:
		s.listen(1)
		conn, addr = s.accept()
		
		q.put( ('connected',) )
		
		# Send the command to start sending data.
		socketSend( conn, 'S00000\n' )
			
		for line in socketByLine( conn ):
			if not line:
				continue
			try:
				if line[0] == 'D':
					u = line.find( '_' )
					if u < 0:
						continue
						
					tag = line[u-6:u]
					tStr = line[u+1:u+1+11]
					hh, mm, ssmi = tStr.split(':')
					hh, mm, ssmi = int(hh), int(mm), float(ssmi)
					mi, ss = math.modf( ssmi )
					mi, ss = int(mi * 1000000.0), int(ss)
					t = datetime.time( hour=hh, minute=mm, second=ss, microsecond=mi )
					if t < startTime:
						continue
						
					# Filter the tag if it has already been read in the last bufferedSecs.
					# First, purge all the old tags.
					purgeSecs = (hh * 60.0 * 60.0) + (mm * 60.0) + ss + mi / 1000000.0 - bufferedSecs
					bufferedTags = dict( (bTag, bSecs) for bTag, bSecs in bufferedTags.iteritems()
															if bSecs > purgeSecs )
					# Check if we have see this tag in the last 3 seconds.
					if tag in bufferedTags:
						continue
						
					# Add this tag to the buffer.
					bufferedTags[tag] = purgeSecs + bufferedSecs
					
					if t < lastTime and tag != lastTag:
						# We received two different tags at exactly the same time.
						# Add a small offset to the time so that we preserve the relative order.
						dFull = datetime.datetime.combine( datetime.date(2011,9,27), lastTime )
						dFull += datetime.timedelta( microseconds = 100 )
						t = dFull.time()
					lastTime, lastTag = t, tag
					q.put( ('data', tag, t) )
				elif line[0] == 'N':
					q.put( ('name', line[5:].strip()) )
			except (ValueError, KeyError):
				pass
				
		q.put( ('disconnected',) )
		
	print( 'closing...' )
	s.close()

def GetData():
	data = []
	while 1:
		try:
			data.append( q.get_nowait() )
		except (Empty, AttributeError):
			break
	return data

def StopListener():
	global q
	global listener

	# Terminate the server process if it is running.
	if listener:
		listener.terminate()
	listener = None
	
	# Purge the queue.
	if q:
		while 1:
			try:
				q.get_nowait()
			except Empty:
				break
			
		q = None
		
def StartListener( startTime = datetime.time(),
					HOST = DEFAULT_HOST, PORT = DEFAULT_PORT ):
	global q
	global listener
	
	StopListener()
		
	q = Queue()
	listener = Process( target = Server, args=(q, HOST, PORT, startTime) )
	listener.start()
	
@atexit.register
def Cleanuplistener():
	if listener:
		listener.terminate()
	
if __name__ == '__main__':
	StartListener()
	count = 0
	while 1:
		time.sleep( 1 )
		sys.stdout.write( '.' )
		messages = GetData()
		if messages:
			sys.stdout.write( '\n' )
		for m in messages:
			if m[0] == 'data':
				count += 1
				print( '%d: %s, %s' % (count, m[1], m[2]) )
			elif m[0] == 'name':
				print( 'receiver name="%s"' % m[1] )
			elif m[0] == 'connected':
				print( 'connected' )
			elif m[0] == 'disconnected':
				print( 'disconnected' )
		sys.stdout.flush()
		