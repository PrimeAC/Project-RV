import socket
import threading 
import struct
import time
import datetime
import ipaddress
import hashlib 


BUFFSIZE = 1024
PORT=5005
SCOPEID = 3 #Change value for your network interface index
loopTime = 1 

table = {}  #creates a dictionary that saves all the neighbors status

f = open("taxi_february.txt", "r")  #opens the file taxi_february.txt on read mode 

class Receiver(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.port = PORT
		self.bufsize = BUFFSIZE
		
		group_bin = socket.inet_pton(socket.AF_INET6, 'ff02::0')
		mreq = group_bin + struct.pack('@I', SCOPEID) 

		self.serverSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
		self.serverSocket.bind(('', PORT))
		print("Server listening for messages on port: " + str(PORT))
		self.serverSocket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)

	def run(self):
		while True:
			(ClientMsg, (ClientIP, ClientPort, ClientFlow, ClientScopeId)) = self.serverSocket.recvfrom (self.bufsize)
			if not ClientMsg:
				continue
			h = hashlib.blake2s(digest_size=2)
			h.update(ClientIP.encode('utf-8'))
			nodeID = h.hexdigest()
			print(h.digest_size)
			print("size  ---  " + str(nodeID))
			print("Message: [" + ClientMsg.decode('utf-8') + "] received on IP/PORT: [" + str(nodeID) + "," + str(ClientPort) + "]")
			check(ClientMsg, nodeID)
			printTable()
	              


class Sender(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.port = PORT
		self.bufsize = BUFFSIZE
		self.msgID = 0   #message ID starts at zero and is incremented every time a user sends a message

		ttl_bin = struct.pack('@i', SCOPEID)
		self.dest_addr = 'ff02::0' 

		self.clientSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
		self.clientSocket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)

	def run(self):
		for line in f:	
			self.message = line.split(";")[2].split("(")[1].split(" ")
			self.latitude = self.message[0]
			self.longitude = self.message[1].split(")")[0]
			self.msgID = self.msgID + 1
			self.message = self.latitude + "|" + self.longitude + "|" + str(datetime.datetime.now().time()) + "|" + str(self.msgID)
			print("Sent: " + self.message)
			self.clientSocket.sendto(self.message.encode(), (self.dest_addr, PORT, 0, SCOPEID))
			time.sleep(5)



class Timer(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.loopTime = loopTime
		

	def run(self):
		while True:
			validateTime()
			time.sleep(self.loopTime)
			

def validateTime():
	timedOut = False
	for key in table:
		lastUpdate = datetime.datetime.strptime(table[key][4], '%H:%M:%S')
		now = datetime.datetime.strptime(str(datetime.datetime.now().time()).split(".")[0], '%H:%M:%S')
		difference = now - lastUpdate
		if difference.total_seconds() > 30:
			timedOut = True
			print("Time out:")
			print(key + "|" + table[key][0] + "|" + table[key][1] + "|" + table[key][2] + "|" + table[key][3] + "|" + table[key][4])
			del table[key]
			break
	if timedOut:
		printTable()



def checkMsgID(msgID, nodeID):
	if table[nodeID][3] < msgID:
		return True
	return False



def check(ClientMsg, nodeID):
	ClientMsg = ClientMsg.decode('utf-8').split("|")
	latitude = ClientMsg[0]
	longitude = ClientMsg[1]
	time = ClientMsg[2].split(".")[0]
	msgID = ClientMsg[3]
	if nodeID in table:   #means that the table already has that node
		if checkMsgID(msgID, nodeID): #valid message id
			table[nodeID] = [latitude, longitude, time, msgID, str(datetime.datetime.now().time()).split(".")[0]]
		else:
			print("Invalid message ID")
	else:
		#else we need to add it to the table	
		table[nodeID] = [latitude, longitude, time, msgID, str(datetime.datetime.now().time()).split(".")[0]]


def printTable():
	print("Neighbor table:")
	for key in table:
		print(str(key) + "|" + table[key][0] + "|" + table[key][1] + "|" + table[key][2] + "|" + table[key][3] + "|" + table[key][4])



receiver = Receiver()
sender = Sender()
timer = Timer()


receiver.start()
sender.start()
timer.start()

threads = []

# Add threads to thread list
threads.append(receiver)
threads.append(sender)
threads.append(timer)


# Wait for all threads to complete
for t in threads:
	t.join()
f.close()  #closes the txt file
print("Exiting Main Thread")
