
import wx
import socket
import threading
import json
import datetime
import time

now = datetime.datetime.now
delimiter = '\n\n\n'
minDelay = 0.2

def postRequests( requests, qRequest ):
	# If we process a message too early, it is possible that the before and after frame are
	# not processed yet and could be missed.
	# So, we delay a little to give time for some frames to accumulate.
	time.sleep( minDelay )
	for kwargs in requests:
		qRequest.put( kwargs )

def SocketListener( s, qRequest, qMessage, qRename ):
	while 1:
		client, addr = s.accept()
		
		messageStrs = []
		while 1:
			data = client.recv( 4096 )
			if not data:
				break
			messageStrs.append( data )
		client.close()
		
		messages = ''.join( messageStrs )
		del messageStrs
		
		# Collect the photo messages.
		tNow = now()
		requests = []
		for message in messages.split( delimiter ):
			if not message:
				continue
			
			try:
				kwargs = json.loads( message )
			except Exception as e:
				qMessage.put( ('error', 'Bad request format: "{}": {}'.format(message, e)) )
				continue
				
			try:
				kwargs['time'] = datetime.datetime( *kwargs['time'] )
			except KeyError:
				pass
			except Exception as e:
				qMessage.put( ('error', 'Bad time format: "{}": {}'.format(kwargs['time'], e)) )
				continue
			
			cmd = kwargs.get('cmd', None)
			if cmd == 'photo':
				if (tNow - kwargs['time']).total_seconds() < minDelay:
					requests.append( kwargs )
				else:
					qRequest.put( kwargs )
					
			elif cmd == 'rename':
				qRename.put( kwargs )

		# Post the messages in a thread to add a delay.
		if requests:
			thread = threading.Thread( target=postRequests, args=(requests, qRequest) )
			thread.daemon = True
			thread.name = 'PostRequestDelay'
			thread.start()
