#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 22 21:50:52 2019

@author: andreamontes
"""
import socket
import re
import time

ackClient = b"@"
approvedUpdate = b"@4#"

HOST = '127.0.0.1' #The server hostname or IP address
PORT = 4000 #Port selected from server side to run communication

binaryCode = []

def verifyFinishedUpdate(data):
     match = re.search(r'^@([0-9A-F]{1,2})##$', data)
     if match:
          return 0
     else:
          return 1
     
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
s.sendall(b'@000110002359311096595514111415#')
data = s.recv(1024)
if (data == approvedUpdate):
     print ("Update has been approved")
     s.send(ackClient)
     data = ""
     finishedUpdate = verifyFinishedUpdate(data)
     while (finishedUpdate !=0):
          data = s.recv(1024)
          binaryCode.append(data)
          finishedUpdate = verifyFinishedUpdate(data)
          time.sleep(5)
          s.send(ackClient)  
          print ("Received data {}".format(data))
          
     print ("Binary code{}".format(binaryCode))
     s.close()
