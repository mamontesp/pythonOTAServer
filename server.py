#!/usr/bin/env python

##@package Server.py
#Create a server and enabling it for firmware updates

from customlogger import CustomLogger
import socket
import re
import os
import datetime
import sys
import argparse
import errno
import threading
import time

##Login libraries
import logging
import logging.handlers

##Enable 1 Disable 0 Debug
DEBUG_ON = 1
MAX_CLIENTS = 5

##Defaults files to log
LOG_PATH_DEFAULT="/tmp"
LOG_FILENAME_DEFAULT = "/otaserver.log"
LOG_LEVEL = logging.INFO #Could be e.g "DEBUG" or "WARNING"

#Constant definitions for returns
SUCCESSFUL = 0
CLIENT_UNVERIFIED = 1
MISSED_FILENAME = 2
VALID_MCUID = 3
UNFORMATTED_MCUID = 4
ALREADY_STARTED_CONNECTION = 5
NOT_STARTED_CONNECTION = 6
UNABLE_BUFFERING_CODE = 7
UNPROPER_FILE_FORMAT = 8
TIMEOUT_CONNECTION = 9
INVALID_CODE_CHUNK = 10
BUFFERING_CODE_INCOMPLETE = 11
READY_TO_UPDATE = 12
CONNECTION_CLOSED_BY_CLIENT = 13
FINISHED_UPDATE = 14
BANNED_CONNECTION = 15
CONNECTION_CLOSED_BY_SERVER = 16


TIMEOUT = 30 #Timeout for open sockets
HOST_DEFAULT = '' #The server hostname or IP address
PORT_DEFAULT = 4000 #Port selected from server side to run communication

PATH_BINARY_FILE_DEFAULT = "/root/fota/otaserver/bin"
PATH_DATABASE_DEFAULT = "/root/fota/otaserver/database/devices2update.txt"

#Standard dataframes 
allowedUpdate = b'@4#' #Frame sent from server to ack MCUID provided by client
bannedUpdate = b'@0#'  #Frame sent from server to deny update to client that requested it
ackClient = b'@'

def readArgs():
     parser = argparse.ArgumentParser(description="OTA server in python")
     parser.add_argument("-db", "--dbname", help="Database file name (path included)", default=PATH_DATABASE_DEFAULT)
     parser.add_argument("-pbf", "--pathbinaryfiles", help="Binary files path", default=PATH_BINARY_FILE_DEFAULT)
     parser.add_argument("-ho", "--host", help="Host IP", default=HOST_DEFAULT)
     parser.add_argument("-p", "--port", help="Port to establish communication", default=PORT_DEFAULT)
     parser.add_argument("-lp", "--logpath", help="Path to save logging", default=LOG_PATH_DEFAULT)
     args = parser.parse_args()
     return args

def validateCodeChunk(codechunk):
     match1 = re.search(r'^S1+[0-9A-F]+\w|^S2+[0-9A-F]+\w|^S3+[0-9A-F]+\w', codechunk)
     match2 = re.search(r'^@([0-9A-F]{1,2})##$', codechunk)
     if match1 or match2:
          return SUCCESSFUL
     else:
          return INVALID_CODE_CHUNK
     
class CustomThread(threading.Thread):
     def __init__(self, target, connection, address):
          threading.Thread.__init__(self, target=target, args=(connection, address))

def threadKiller(threadsList):
     logging.error("Hunting...")
     while True:
          for thd in threadsList:
               if not thd.is_alive():
                    logging.error("Killing client {}".format(threadsList.index(thd) + 1))
                    threadsList.remove(thd)
                    break
          time.sleep(1)

class Server:
     def __init__(self, logFile, pathBinaryFiles, databaseName, host, port, logPath):
          self.bufferSizeFile = 300 # Number of lines per file to buffered by server
          self.maxBytes = 1024     #Bytes to be received by connection
          self.logFile = logFile
          self.pathBinaryFiles = pathBinaryFiles
          self.databaseName = databaseName
          self.host = host
          self.port = port
          self.logPath = logPath
          
           # AF_INET: For Ipv4 connections
          # SOCK_STREAM: For use of TCP/IP stack
          self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
          self.configureLogger(self.logFile)
          self.connectionsList = [] # List of client connections being attended by the server in one moment
          self.clientsList = [] #List of mcuid, name of file and firmware version from devices being updated
          self.threadsList = []
                    
     def configureLogger(self, logFile):
          self.logger = logging.getLogger()
          self.logger.setLevel(logging.ERROR)
          
          formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
          handler2 = logging.StreamHandler(sys.stdout)
          handler2.setFormatter(formatter)
          self.logger.addHandler(handler2)
     """ # Logger name
          self.logger = logging.getLogger(self.logFile)
          # Set the log level to LOG_LEVEL
          self.logger.setLevel(LOG_LEVEL)
          #Remove previous handlers
          while (len(self.logger.handlers) > 0):
               h = self.logger.handlers[0]
               self.logger.removeHandler(h)
          # Make a handler that writes to a file, making a new file at midnight and keeping
          # 3 backups
          #handler = logging.handlers.TimedRotatingFileHandler(logFile, when="midnight", backupCount =3)
          #handler.setLevel(logging.INFO)
          
          handler2 = logging.StreamHandler(sys.stdout)
          handler2.setLevel(logging.DEBUG)
          
          #Format each log message like this
          formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
          #Attach the formatter to the handler
          #handler.setFormatter(formatter)
          handler2.setFormatter(formatter)
          
          #Attach the handler to the logger
          #self.logger.addHandler(handler)
          self.logger.addHandler(handler2)
          #Replacement of stdout with logging to file at INFO level
          sys.stdout = CustomLogger(self.logger, logging.INFO)
          #Replacement of stdout with logging to file at ERROR level
          sys.stderr = CustomLogger(self.logger, logging.ERROR)
     """
     def changeLogFile(self, logFile):
          self.logger.info("Changing log file")
          self.logFile = logFile
          self.configureLogger(logFile)
          
     def startServer(self):          
          #Cleaning previous connections
          self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
          #For binding address and port
          # 0.0.0.0 because that makes our server available over any IP address
          self.sock.bind((self.host, self.port))
          #Listen argument: Maximum in queue pendings
          self.sock.listen(5)
          self.logger.info("Server ready to listen")
          self.sock.setblocking(1)
          killer = threading.Thread(target=threadKiller, args=(self.threadsList,))
          killer.start()
          
          while True:
               # Accept the connection from the address       
               if (len(self.threadsList) < MAX_CLIENTS):
                    try:
                         connection, address = self.sock.accept()
                    except KeyboardInterrupt:
                         self.logger.error("Trying to escape by keyboard")
                         continue
                    except socket.timeout as e:
                         continue
                    self.threadsList.append(CustomThread(self.acceptConnections, connection, address))
                    self.threadsList[-1].start()
                    logging.error("There are {}".format(len(self.threadsList)))
                    
     
     def acceptConnections(self, connection, address):
          self.changeLogFile(self.logPath + LOG_FILENAME_DEFAULT)
          self.logger.info("Accepted connection from {}".format(connection))
          
          if (self.verifyStartedConnection(connection) == NOT_STARTED_CONNECTION):
               #Verify if id client belongs to database
               mcuid, statusMCUID = self.getMCUID(connection, address)
               
               if (statusMCUID == UNFORMATTED_MCUID):
                    self.closeConnection(connection)
                    return UNFORMATTED_MCUID
                    
               date = datetime.datetime.now().strftime("%d-%m-%y_%H-%M")
               self.configureLogger(self.logPath + "/" + mcuid + "-" + date +".txt")
               statusIdClient, clientInfo = self.verifyClientId(connection, mcuid)
               if (statusIdClient == SUCCESSFUL):
                    connection.send(allowedUpdate)
                    self.logger.info("Allowing update to {}".format(mcuid))
                    self.logger.info("Starting update to {}".format(mcuid))
                    self.prepareUpdate(clientInfo)
                    self.sendUpdate(connection, address, mcuid)
                    self.closeConnection(connection)
                    return FINISHED_UPDATE
               else:
                    self.logger.warning("Banned connection from {}".format(address))
                    self.logger.error("Closing connection")
                    connection.send(bannedUpdate)
                    self.closeConnection(connection)
                    return BANNED_CONNECTION
          
          
     def verifyStartedConnection(self, connection):
          for conn in self.connectionsList:
               if(conn == connection):
                    return ALREADY_STARTED_CONNECTION
          self.connectionsList.append(connection)
          return NOT_STARTED_CONNECTION
     
     def getMCUID(self, connection, address):
          receivedData = connection.recv(self.maxBytes).decode("utf8")
          self.logger.info("Server has received data {} from {}".format(receivedData, address))
          #mcuid = re.findall("^\@(\d{25})[0-9]*#$", receivedData.decode("utf-8"))
          mcuid = re.findall("^\@([0-9A-F]*)#$", receivedData)
          self.logger.info("MCUID {} ".format(mcuid))
          if(len(mcuid) == 1):
               self.logger.info("MCUID {} valid format ".format(mcuid[0]))
               return mcuid[0], VALID_MCUID
          else:
               self.logger.info("MCUID {} invalid format ".format(receivedData))
               return receivedData, UNFORMATTED_MCUID
     
     
     def verifyClientId(self, connection, mcuid):
          ## Verify client trying connection
          clientInfo = []
          statusClient, clientInfo = self.lookForClientInDatabase(mcuid)
          if(statusClient== SUCCESSFUL):
               self.logger.info("Client Info {}".format(clientInfo))
               self.logger.info("Client {} exists in database".format(mcuid))
               return SUCCESSFUL, clientInfo
          else:
               self.logger.error("Client {} does not exist in database".format(mcuid))
               return CLIENT_UNVERIFIED, clientInfo
                        
     def lookForClientInDatabase(self, mcuid):
          ##Verify existence of client in database for firmware update
          clientInfo = []
          self.logger.info("Opening file {}, to verify MCUID {}".format(self.databaseName,mcuid))
          try:
               with open(self.databaseName, 'r') as file:
                    for line in file:
                         clientInfo = line.split(',')
                         if (len(clientInfo) == 3):
                              if (clientInfo[0] == mcuid):
                                  return SUCCESSFUL, clientInfo
                              else:
                                   continue
                         else:
                              return UNPROPER_FILE_FORMAT, clientInfo
               file.close()
          except:
               self.logger.error("Error opening file")
          return CLIENT_UNVERIFIED, clientInfo
     
     def closeConnection(self, connection):
          self.logger.info("Close of connection has been requested")
          connection.close()
          return SUCCESSFUL
     
     def prepareUpdate(self, clientInfo):
          self.logger.info("Preparing update for {}".format(clientInfo))
          #Buffer data from file to be sent to specific client
          binaryFileLines = []
          bufferingStatus = self.bufferData(clientInfo[1], binaryFileLines)
          self.logger.info("Status prepare update {}".format(bufferingStatus))
          if (bufferingStatus == SUCCESSFUL):
               FWVersion = re.findall(r"([0-9A-F]+)", clientInfo[2])
               binaryFileLines.append("@{}##".format(FWVersion[0]))
               self.logger.info("Code buffer done successfully") 
               self.clientsList.append({"mcuid":clientInfo[0], "filename":clientInfo[1], "codelines": binaryFileLines, "status": READY_TO_UPDATE})                 
               return SUCCESSFUL
          if (bufferingStatus == BUFFERING_CODE_INCOMPLETE):
               ##Pending development
               self.logger.info("Incomplete buffering code")
               return BUFFERING_CODE_INCOMPLETE
          else:
               return UNABLE_BUFFERING_CODE
     
     def bufferData(self, filename, binaryFileLines):
          countLines = 0
          path = self.pathBinaryFiles+"/"+ filename
          if (os.path.exists(path)== False):
               self.logger.error("Required file does not exist {}".format(path))
               return UNABLE_BUFFERING_CODE
          with open(path, 'r') as file:
               self.logger.info("Opening file {}".format(path))
               line = file.readline()
               countLines += 1
               while (line and countLines < self.bufferSizeFile):
                    line = file.readline()
                    chunk = re.findall(r'^S1+[0-9A-F]+\w|^S2+[0-9A-F]+\w|^S3+[0-9A-F]+\w', line)
                    if (len(chunk)>0):
                         binaryFileLines.append(chunk[0])
                    countLines += 1
               if(file.readline() == ''):
                    file.close()
                    return SUCCESSFUL
               file.close()
               return BUFFERING_CODE_INCOMPLETE
          return UNABLE_BUFFERING_CODE
     
     def sendUpdate(self, connection, address, mcuid):
          self.sock.settimeout(TIMEOUT)
          for codechunk in self.clientsList[0]['codelines']:
               if (validateCodeChunk(codechunk) == SUCCESSFUL):
                    self.logger.info("Data from server {}".format(codechunk))
                    try:
                         connection.send(codechunk.encode())
                         receivedData = connection.recv(1024)
                         self.logger.info("Data from client: {}".format(receivedData))
                         if (receivedData == ackClient):
                              continue
                         else:
                              return TIMEOUT_CONNECTION
                    except socket.timeout as e:
                              self.logger.error("Timeout exceed {}".format(e))
                              return TIMEOUT_CONNECTION
                    except socket.error as e:
                         self.logger.error("Error receiving data: {}".format(e))
                         return CONNECTION_CLOSED_BY_CLIENT
                    except IOError as e:
                         self.logger.error("IOError: {}".format(e))
                         if e.errno == errno.EPIPE:
                              self.logger.error("Broken pipe by client side")
                              return CONNECTION_CLOSED_BY_CLIENT
                    except KeyboardInterrupt:
                         return CONNECTION_CLOSED_BY_SERVER
                         
                              
               else:
                    continue 
          self.logger.info("Update finished")
          self.closeConnection(connection)
          self.sock.setblocking(0)
          return SUCCESSFUL
     
if __name__ == "__main__":
     """myThreadsList = []
     for i in range(5):
          myThreadsList.append(CustomThread(i, rn.random()*10, rn.random()*5, printer))
          myThreadsList[-1].start()"""
          
     args = readArgs()
     databaseNameArg = args.dbname
     pathBinaryFilesArg = args.pathbinaryfiles
     hostArg=args.host
     portArg=int(args.port)
     logPathArg = args.logpath
     logFileArg = logPathArg + LOG_FILENAME_DEFAULT
     
     myServer = Server(logFileArg, pathBinaryFilesArg, databaseNameArg, 
                            hostArg, portArg, logPathArg)
     myServer.startServer()
     
   
