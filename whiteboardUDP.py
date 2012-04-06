"""
SHARED WHITEBOARD V 1.0

used protocol:
		cxxyyttttttttttttt
	xx - 1 and 2 bits of x coord.
	yy - 1 and 2 bits of y coord.
	ttttttttttttt - time in sec at which point was made
	broadcasted by: everyone who paints
	received by: everyone
	
		mclear
	is broadcasted to ask others when peer pressed 
	"Clear everyone's canvas" button to find clear_nr
	number of people that are agree to clear it
	sent by: person who pressed the button
	received by: everyone
	
		mc111
	is broadcasted as a response on mclear in case if
	peer agreed to clear it
	sent by: person who agreed to clear
	received by: everyone
	
		mc000
	is broadcasted as a response on mclear in case if
	peer didn't agree to clear it
	sent by: person who didn't agree to clear
	received by: everyone
	
		mctrue
	is broadcasted by person who pressed the button
	if he/she get >=clear_nr number of people who agreed
	to clear the canvas
	sent by: person who didn't agree to clear
	received by: everyone
	
		n#xxxxxx
	xxxxxx - color in hex
	is broadcasted by new commer as soon as the user started
	program. is need to show list of connected peers and to
	reply whether new commer's color is valid or not
	sent by: new commer
	received by: everyone
	
		bad
	received if new commer's color is not valid, causes
	regeneration of color
	sent by: person who already has this color
	received by: new commer with not valid color
	
		#xxxxxx
	xxxxxx - color in hex
	used for color synchronization in all current opened and
	working programs
	sent by: everyone if no color repetition occured
	received by: new commer with valid color
	
		exit
	used for eliminating from list user that closed the program
	by pressing X button and confirmed closing
	sent by: user that leaved the program
	received by: everyone
"""

import socket
import struct
import traceback
from Tkinter import *
from Tkinter import Tk
import time
import threading
import thread
import random as rn
import re
import tkMessageBox
 
lastx, lasty = 0, 0
tempX, tempY = 0, 0
canvasWidth = 300
canvasHeight = 300

peersData = {}		#dict of key=perrs' ip, val=[x, y, last point time, color]
clear_request_received_time = 0		#time when question about 
									#clearing canvas received
delta_clear = 5 	#seconds to wait till canvas will be cleared (if will)
clear = False		#can i clear everyones' canvas?
clear_count = 0		#nr of people who agreed
clear_nr = 1    	#min nr of people that should agree to clear canvas
my_color = ''		#my color
                      
port = 6666			#wow, it's port
my_ip = socket.gethostbyname(socket.gethostname())
print my_ip			#my IP
host = "224.1.1.1"	#'<broadcast>'

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
s.bind(('', port))
mreq = struct.pack("4sl", socket.inet_aton(host), socket.INADDR_ANY) 
#packs a 32-bit packet ipv4 IP address and INADDR_ANY. INADDR_ANY is used for binding to all interfaces.
s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq) 
# Used to join a multicast group. mreq contains the addresses of the group
s.settimeout(1.0)


def xy(event):
    global lastx, lasty
    lastx, lasty = event.x, event.y

#returns hex color
def color_rand():
	peer_color = '#' + "".join(["%02x"%rn.randrange(256) for n in range(3)])
	return peer_color	
	

#broadcasting at each mouse movement with clicked button
def addLine(event):
	global lastx, lasty, my_ip, s
	canvas.create_line(lastx, lasty, event.x, event.y, fill=my_color)
	lastx, lasty = event.x, event.y
	lastx %= 9024
	lasty %= 9024
	x1 = lastx/95+32
	x2 = lastx%95+32
	y1 = lasty/95+32
	y2 = lasty%95+32
	time_now = time.time()
	try:
		coord = "c"+chr(x1)+chr(x2)+chr(y1)+chr(y2)+str(time_now)
		#print coord
		s.sendto(coord, (host, port))
	except (ValueError, UnboundLocalError):
		pass
 


#clears canvas if enough peers agreed to clear,
#otherwise calls function to show message
def clearCanvas():
	global delta_clear, clear, s
	clear_message = "mclear"
	s.sendto(clear_message, (host, port))
	
	start_time = time.time()
	label = "Waiting for {0} answer(s)...".format(clear_nr)
	clearButton.config(state=DISABLED, text=label)
	while ((time.time() - start_time) < float(delta_clear)):		
		if clear:
			canvas.delete('all')
			print "cleared after pressing button"
			clear_confirm = "mctrue"
			s.sendto(clear_confirm, (host, port))
			break
	clearButton.config(state=NORMAL, text="Clear everyone's canvas")
	if not clear:
		print "was rejected"
		root.event_generate('<<sorry>>', when='tail')
	clear = False
	clear_count = 0

#clears only my canvas	
def clearMyPressed():
	canvas.delete('all')
		

def dot(canvas, x, y, peer_color):
	canvas.create_oval(x, y, x+1, y+1, fill=peer_color, outline=peer_color)

#called after pressing close button (X)	
def callback():
	global thread, s, peersData, my_ip, host, port
	if tkMessageBox.askokcancel("Quit", "Do you really wish to quit?"):
		s.sendto("exit", (host, port))
		s.close()
		root.destroy()
		thread.interrupt_main()
	

#displays dialog asking if peer wants to clear canvas,
#sends response	
def myDialog(event):
	global s, clear_request_received_time, delta_clear
	if (tkMessageBox.askyesno(title="Clear message received", \
		message="Do you want to clear everyone's canvas?") == 1):
		clear_answer = "mc111"
	else:
		clear_answer = "mc000"
	clear_request_pressed = time.time()
	delta = clear_request_pressed - clear_request_received_time
	if delta < delta_clear:
		s.sendto(clear_answer, (host, port))
	else: 
		tkMessageBox.showinfo(title="Timeout", \
		message="Your answer will not be considered.")
	

#called if not enough people agreed to clear the canvas
def sorryDialog(event):	
	tkMessageBox.showinfo(title="Clear message received", \
		message="Timeout orn ot enough people agreed to clear the canvas.")
	

#check if new commer has unique color
#see future improvement in report for more info
def newUser(receivedColor, peer_id):
	global s, peersData, my_color
	good = True
	for peer in peersData:
		if peersData[peer][3] == receivedColor:
			print peersData[peer][3]
			print receivedColor
			s.sendto("bad", (peer_id, port))
			good = False
	if good:
		peersData[peer_id] = [0,0,0,receivedColor]
		s.sendto(my_color, (peer_id, port))
	print peersData

#each time we have new peer or connected peer leaves the
#program this is called to refresh message area
def refreshMessage(event):
	global peersData
	dispIP = peersData.keys()
	str=''
	for item in dispIP:
		str+=item
		str+="    "
	ips.config(text=str)
	
#parses receining data
def worker(root, canvas):
	global my_ip, peersData, clear, clear_count, \
		delta_clear, clear_request_received_time, s, my_color
	"""
	This function should read something from the socket and
	plot the dot on the canvas if a message is received.
	"""
	while True:
		try:
			data, address = s.recvfrom(4096)	
		except:
			continue
		else:
			print 'message (%s) from : %s' %(str(data), address[0])
			peer_id = address[0]
			if (peer_id!=my_ip):
				if (data[0]=='c'):
					x = ((ord(data[1])-32)*95+ord(data[2])-32)
					y = ((ord(data[3])-32)*95+ord(data[4])-32)
					time_now = float(data[5:18])
					#if peer exists
					if peer_id in peersData:
						tempX, tempY = peersData[peer_id][0], peersData[peer_id][1]
						time_prev, peer_color = peersData[peer_id][2], peersData[peer_id][3]
						peersData[peer_id] = [x, y, time_now, peer_color] 
						delta = time_now - time_prev
						if delta<0.08:
							try:
								canvas.create_line(tempX, tempY, x, y, fill=peer_color)
							except ValueError, TclError:
								pass
						else:
							dot(canvas, x, y, peer_color)
					else:	
						print "not in dict"

				if (data[0:6]=='mclear'):
					print "clear?"
					clear_request_received_time = time.time()
					root.event_generate('<<openIt!>>', when='tail')
						
				if (data[0:5]=='mc111'):
					clear_request_true_time = time.time()
					delta_true = clear_request_true_time - clear_request_received_time
					print delta_true
					if delta_true < delta_clear:
						clear_count += 1
						print clear_count
					if clear_count >= clear_nr:
						clear = True 
						print clear		
						
				if (data[0:6]=='mctrue'):
					canvas.delete('all')
					print "just cleared"
					clear = False
					clear_count = 0
					
				if (data[0:2]=='n#'):
					receivedColor = data[1:]
					print "new color!----",receivedColor
					newUser(receivedColor, peer_id)
					root.event_generate('<<new>>', when='tail')
					
				if (data[0:3]=='bad'):
					my_color = color_rand()
					peersData[my_ip] = [0,0,0,my_color]
					print "was bad"
					
				if (data[0]=='#'):
					peersData[peer_id] = [0,0,0,data]
					root.event_generate('<<new>>', when='tail')
					print peersData
					
				if (data[0:4]=='exit'):
					del peersData[peer_id]
					root.event_generate('<<new>>', when='tail')

			if (data[0:6]=='mclear' and peer_id==my_ip):
				print "clear?"
				clear_request_received_time = time.time()
					
			
				

#layout initialization, start receiving thread
if __name__ == "__main__":	
	root = Tk()
	root.title('Shared whiteboard')
	root.config(bg='#ddd')
	root.columnconfigure(2, weight=1)
	root.rowconfigure(1, weight=1)
	root.protocol("WM_DELETE_WINDOW", callback)
	root.minsize(width=600, height=340)
		
	root.bind('<<openIt!>>', myDialog)	
	root.bind('<<sorry>>', sorryDialog)
	root.bind('<<new>>', refreshMessage)
	
	canvas = Canvas(root, width=canvasWidth, height=canvasHeight, bg='#fff')
	canvas.grid(column=0, row=1, sticky=(N, W, E, S), columnspan=7)
	
	clearButton = Button(root, text="Clear everyone's canvas",
		width = 20, command=clearCanvas)
	clearButton.grid(column=0, row=0, padx=5, pady=5)
	
	clearMyCanvas = Button(root, text="Clear my canvas", command=clearMyPressed,
		width = 14)
	clearMyCanvas.grid(column=1, row=0, pady=5)
		
	my_color = color_rand()	
	s.sendto("n"+my_color, (host, port))
	peersData[my_ip] = [0,0,0,my_color]

	dispIP = peersData.keys()
	ips = Message(root, text=dispIP, fg='#000', width=365,bg='#ddd')
	ips.grid( column=2, row=0,  sticky=(N, W), pady=6)

	#start another thread, it will read stuff from the socket
	#and update the canvas if needed	
	t = threading.Thread(target=worker, args=(root, canvas) )
	t.start()
	
	canvas.bind("<Button-1>", xy) #event, mouse-click
	canvas.bind("<B1-Motion>", addLine) #event, move mouse with a clicked button
	 
	#drawing the canvas itself
	root.mainloop()
	