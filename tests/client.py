#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 22 21:50:52 2019

@author: andreamontes
"""
import socket
import re
import time
import threading

ackClient = b"@"
approvedUpdate = b"@4#"
#HOST = '192.168.1.105' #Localhost in local network
HOST = '127.0.0.1' #Localhost in laptop
#HOST = '209.97.145.137' #The server hostname or IP address
PORT = 4000 #Port selected from server side to run communication

binaryCode = []

def verifyFinishedUpdate(data):
     match = re.search(r'^@0#$', data)
     if match:
          return 0
     else:
          return 1

def receiveData():
     data = s.recv(1024)
     print ("Received data {}".format(data))
		
def sleepSending():
     time.sleep(35)

sleepThread = threading.Thread(target=sleepSending, args=())
receivingThread = threading.Thread(target=receiveData, args=())

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))

#sleepThread.start()
#receivingThread.start()
#time.sleep(35)
s.sendall("@0001100023593110965955141#")
#s.sendall("@0001200049152150965955141#")
data = s.recv(1024)
print ("First data {}".format(data))
if (data == approvedUpdate):
     print ("Update has been approved")
     s.send(ackClient)
     data = ""
     finishedUpdate = verifyFinishedUpdate(data)
     while (finishedUpdate !=0):
          data = s.recv(1024)
          binaryCode.append(data)
          finishedUpdate = verifyFinishedUpdate(data)
          print ("Received data {}".format(data))
          s.send(ackClient)
          time.sleep(1)
     print("Closing connection")
     s.close()
