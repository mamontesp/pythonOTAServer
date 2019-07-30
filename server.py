#!/usr/bin/env python

##@package Server.py
#Create a server and enable REST API for firmware updates

from customlogger import CustomLogger
import socket
import re
import os

##Login libraries
import logging
import logging.handlers
import datetime
import sys
import argparse
import errno

##Enable 1 Disable 0 Debug
DEBUG_ON = 1

##Defaults files to log
LOG_PATH_DEFAULT="/tmp"
LOG_FILENAME_DEFAULT = "/otaserver.log"
LOG_LEVEL =logging.INFO #Could be e.g "DEBUG" or "WARNING"

#Constant definitions for returns
SUCCESSFUL = 0
CLIENT_UNVERIFIED = 1
MISSED_FILENAME = 2
UNFORMATTED_MCUID = 3
ALREADY_STARTED_CONNECTION = 4
NOT_STARTED_CONNECTION = 4
UNABLE_BUFFERING_CODE = 5
UNPROPER_FILE_FORMAT = 6
TIMEOUT_CONNECTION = 7
INVALID_CODE_CHUNK = 8
BUFFERING_CODE_INCOMPLETE = 9
READY_TO_UPDATE = 10
CONNECTION_CLOSED_BY_CLIENT = 11

TIMEOUT = 30 #Timeout for open sockets
HOST_DEFAULT = '' #The server hostname or IP address
PORT_DEFAULT = 4000 #Port selected from server side to run communication

PATH_BINARY_FILE_DEFAULT = "/root/fota/otaserver/bin"
PATH_DATABASE_DEFAULT = "/root/fota/otaserver/database/devices2update.txt"

#Standard dataframes 
allowedUpdate = b'@4#' #Frame sent from server to ack MCUID provided by client
bannedUpdate = b'@0#'  #Frame sent from server to deny update to client that requested it
ackClient = b'@'

bufferSizeFile = 300 # Number of lines per file to buffered by server
maxBytes = 1024     #Bytes to be received by connection

#Binary file location
pathBinaryFiles = ""

#Database name file 
databaseName = ""

#Host
host = ""

#Port 
port = ""

#Log path
logPath = ""

#List of socket inputs
inputs = []

def readArgs():
     parser = argparse.ArgumentParser(description="OTA server in python")
     parser.add_argument("-db", "--dbname", help="Database file name (path included)", default=PATH_DATABASE_DEFAULT)
     parser.add_argument("-pbf", "--pathbinaryfiles", help="Binary files path", default=PATH_BINARY_FILE_DEFAULT)
     parser.add_argument("-ho", "--host", help="Host IP", default=HOST_DEFAULT)
     parser.add_argument("-p", "--port", help="Port to establish communication", default=PORT_DEFAULT)
     parser.add_argument("-lp", "--logpath", help="Path to save logging", default=LOG_PATH_DEFAULT)
     args = parser.parse_args()
     return args

def configureLogger(logFile):
     # Logger name
     logger = logging.getLogger(logFile)
     # Set the log level to LOG_LEVEL
     logger.setLevel(LOG_LEVEL)
     # Make a handler that wirtes to a file, making a new file at midnight and keeping
     # 3 backups
     handler = logging.handlers.TimedRotatingFileHandler(logFile, when="midnight", backupCount =3)
     #Format each log message like this
     formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
     #Attach the formatter to the handler
     handler.setFormatter(formatter)
     #Attach the handler to the logger
     logger.addHandler(handler)
     #Replacement of stdout with loggin to file at INFO level
     sys.stdout = CustomLogger(logger, logging.INFO)
     #Replacement of stdout with loggin to file at ERROR level
     sys.stderr = CustomLogger(logger, logging.ERROR)
     return logger
 
def createServer(connectionsList, clientsList):
     ## Create server
     # AF_INET: For Ipv4 connections
     # SOCK_STREAM: For use of TCP/IP stack
     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
     hostname = socket.gethostname()
     logger.info("Hostname {}".format(hostname))
     #Cleaning previous connections
     sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
     #For binding address and port
     # 0.0.0.0 because that makes our server available over any IP address
     sock.bind((host,port))
     #Listen argument: Maximum in queue pendings
     sock.listen(5)
     inputs.append(sock)
     logger.info("Server ready to listen")
     acceptConnections(connectionsList, clientsList, sock, logger)

def acceptConnections(connectionsList, clientsList, sock, logger):
     while True:
          #Accept the connection from the address
          sock.setblocking(1)
          connection, address = sock.accept()
          logger.info("Accepted connection from {}".format(connection))
          if (verifyStartedConnection(connectionsList, connection) == NOT_STARTED_CONNECTION):
               #Verify if id client belongs to database
               mcuid = getMCUID(connection, address, logger)
               date = datetime.datetime.now().strftime("%d-%m-%y_%H-%M")
               logFile = logPath + "/" + str(mcuid) + "-" + date +".txt"
               print("logfile {}".format(logFile))
               logger = configureLogger(logFile)
               statusIdClient, clientInfo = verifyClientId(connection, mcuid, logger)
               if (statusIdClient == SUCCESSFUL):
                    connection.send(allowedUpdate)
                    logger.info("Allowing update to {}".format(mcuid))
                    logger.info("Starting update to {}".format(mcuid))
                    prepareUpdate(clientInfo, clientsList, logger)
                    sendUpdate(connection, address, mcuid, clientsList, sock, logger)
               else:
                    logger.warning("Banned connection from {}".format(address))
                    logger.error("Closing connection")
                    connection.send(bannedUpdate)
                    closeConnection(connection, logger)
     
     
def verifyStartedConnection(connections, connection):
     for conn in connections:
          if(conn == connection):
               return ALREADY_STARTED_CONNECTION
     connections.append(connection)
     return NOT_STARTED_CONNECTION

def getMCUID(connection, address, logger):
     receivedData = connection.recv(maxBytes)
     logger.info("Server has received data from {}".format(address))
     mcuid = re.findall("^\@(\d{25})[0-9]*#$", receivedData.decode("utf-8"))
                        
     if(len(mcuid) == 1):
          return mcuid[0]
     else:
          return UNFORMATTED_MCUID

def verifyClientId(connection, mcuid, logger):
     ## Verify client trying connection
     clientInfo = []
     statusClient, clientInfo = lookForClientInDatabase(mcuid, logger)
     if(statusClient== SUCCESSFUL):
          logger.info("Client Info {}".format(clientInfo))
          logger.info("Client {} exists in database".format(mcuid))
          return SUCCESSFUL, clientInfo
     else:
          logger.error("Client {} does not exist in database".format(mcuid))
          return CLIENT_UNVERIFIED, clientInfo
                   
def lookForClientInDatabase(mcuid, logger):
     ##Verify existence of client in database for firmware update
     clientInfo = []
     logger.info("Opening file {}, to verify MCUID {}".format(databaseName,mcuid))
     try:
          with open(databaseName, 'r') as file:
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
          logger.error("Error opening file")
     return CLIENT_UNVERIFIED, clientInfo

def closeConnection(connection, logger):
     logger.info("Close of connection has been requested")
     connection.close()
     logFile = logPath + LOG_FILENAME_DEFAULT
     logger = configureLogger(logFile)
     return SUCCESSFUL

def prepareUpdate(clientInfo, clientsList, logger):
     logger.info("Preparing update for {}".format(clientInfo))
     #Buffer data from file to be sent to specific client
     binaryFileLines = []
     bufferingStatus = bufferData(clientInfo[1], binaryFileLines, logger)
     logger.info("Status prepare update {}".format(bufferingStatus))
     if (bufferingStatus == SUCCESSFUL):
          FWVersion = re.findall(r"([0-9A-F]+)", clientInfo[2])
          binaryFileLines.append("@{}##".format(FWVersion[0]))
          logger.info("Buffered code {}".format(binaryFileLines))
          logger.info("Code buffer done successfully") 
          clientsList.append({"mcuid":clientInfo[0], "filename":clientInfo[1], "codelines": binaryFileLines, "status": READY_TO_UPDATE})                 
          return SUCCESSFUL
     if (bufferingStatus == BUFFERING_CODE_INCOMPLETE):
          ##Pending development
          logger.info("Incomplete buffering code")
          return BUFFERING_CODE_INCOMPLETE
     else:
          return UNABLE_BUFFERING_CODE

def bufferData(filename, binaryFileLines, logger):
     countLines = 0
     path = pathBinaryFiles+"/"+ filename
     if (os.path.exists(path)== False):
          logger.error("Required file does not exist {}".format(path))
          return UNABLE_BUFFERING_CODE
     with open(path, 'r') as file:
          logger.info("Opening file {}".format(path))
          line = file.readline()
          countLines += 1
          while (line and countLines < bufferSizeFile):
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

def sendUpdate(connection, address, mcuid, clientToUpdate, sock, logger):
     sock.settimeout(TIMEOUT)
     for codechunk in clientToUpdate[0]['codelines']:
          if (validateCodeChunk(codechunk) == SUCCESSFUL):
               logger.info("Data from server {}".format(codechunk))
               try:
                    connection.send(codechunk.encode())
                    receivedData = connection.recv(1024)
                    logger.info("Data from client: {}".format(receivedData))
                    if (receivedData == ackClient):
                         continue
                    else:
                         closeConnection(connection, logger)
                         return TIMEOUT_CONNECTION
               except socket.timeout as e:
                         logger.error("Timeout exceed {}".format(e))
                         closeConnection(connection, logger)
                         return TIMEOUT_CONNECTION
               except socket.error as e:
                    logger.error("Error receiving data: {}".format(e))
                    closeConnection(connection, logger)
                    return CONNECTION_CLOSED_BY_CLIENT
               except IOError as e:
                    logger.error("IOError: {}".format(e))
                    if e.errno == errno.EPIPE:
                         logger.error("Broken pipe by client side")
                         closeConnection(connection, logger)
                         return CONNECTION_CLOSED_BY_CLIENT
                         
          else:
               continue 
     logger.info("Update finished")
     closeConnection(connection, logger)
     sock.setblocking(0)
     return SUCCESSFUL

def  validateCodeChunk(codechunk):
     match1 = re.search(r'^S1+[0-9A-F]+\w|^S2+[0-9A-F]+\w|^S3+[0-9A-F]+\w', codechunk)
     match2 = re.search(r'^@([0-9A-F]{1,2})##$', codechunk)
     if match1 or match2:
          return SUCCESSFUL
     else:
          return INVALID_CODE_CHUNK
     
if __name__ == "__main__":
     args = readArgs()
     databaseName = args.dbname
     pathBinaryFiles = args.pathbinaryfiles
     host=args.host
     port=int(args.port)
     logPath=args.logpath
     logFile = logPath + LOG_FILENAME_DEFAULT
     logger = configureLogger(logFile)
     
     connectionsList = [] # List of client connections being attended by the server in one moment
     clientsList = [] #List of mcuid, name of file and firmware version from devices being updated
     createServer(connectionsList, clientsList)
   
