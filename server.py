##@package Server.py
#Create a server and enable REST API for firmware updates

import socket
import re
import os

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

TIMEOUT = 30 #Timeout for open sockets
HOST = '' #The server hostname or IP address
PORT = 4000 #Port selected from server side to run communication

#Standard dataframes 
allowedUpdate = "@4#" #Frame sent from server to ack MCUID provided by client
bannedUpdate = "@0#"  #Frame sent from server to deny update to client that requested it
ackClient = "@"

bufferSizeFile = 15 # Number of lines per file to buffered by server
maxBytes = 1024     #Bytes to be received by connection
pathBinaryFiles = "./bin"

##Choose debug level of server
# 0 Disabled 
# 1 Error
# 2 Alert
# 3 Log
debugLevel = 3

#Database name file 
databaseName = "./database/devices2update.txt"

def printDebugL1(message):
     if (debugLevel >= 1):
          print("Error: "+ message)
     return SUCCESSFUL
          
def printDebugL2(message):
     if (debugLevel >= 2):
          print("Alert: "+ message)
     return SUCCESSFUL

def printDebugL3(message):
     if (debugLevel >= 3):
          print("Log: "+ message)
     return SUCCESSFUL

def createServer(connectionsList, clientsList):
     ## Create server
     # AF_INET: For Ipv4 connections
     # SOCK_STREAM: For use of TCP/IP stack
     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
     host = socket.gethostname()
     printDebugL3("Hostname {}".format(host))
     #Cleaning previous connections
     sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
     #For binding address and port
     # 0.0.0.0 because that makes our server available over any IP address
     sock.bind((HOST,PORT))
    
     #Listen argument: Maximum in queue pendings
     sock.listen(5)
     printDebugL3("Server ready to listen")
     acceptConnections(connectionsList, clientsList, sock)

def acceptConnections(connectionsList, clientsList, sock):
     while True:
          #Accept the connection from the address
          sock.setblocking(1)
          connection, address = sock.accept() 
          printDebugL1("Accepted connection from {}".format(connection))
          if (verifyStartedConnection(connectionsList, connection) == NOT_STARTED_CONNECTION):
               #Verify if id client belongs to database
               mcuid = getMCUID(connection, address)
               statusIdClient, clientInfo = verifyClientId(connection, mcuid)
               if (statusIdClient == SUCCESSFUL):
                    connection.send(allowedUpdate)
                    printDebugL3("Allowing update to {}".format(mcuid))
                    printDebugL3("Starting update to {}".format(mcuid))
                    prepareUpdate(clientInfo, clientsList)
                    sendUpdate(connection, address, mcuid, clientsList, sock)
               else:
                    printDebugL2("Banned connection from {}".format(address))
                    connection.send(bannedUpdate)
                    connection.close()

def verifyStartedConnection(connections, connection):
     for conn in connections:
          if(conn == connection):
               return ALREADY_STARTED_CONNECTION
     connections.append(connection)
     return NOT_STARTED_CONNECTION

def getMCUID(connection, address):
     receivedData = connection.recv(maxBytes)
     printDebugL3("Server has received data from {}".format(address))
     mcuid = re.findall("^\@(\d{25})[0-9]*#$", receivedData)
     if(len(mcuid) == 1):
          return mcuid[0]
     else:
          return UNFORMATTED_MCUID

def verifyClientId(connection, mcuid):
     ## Verify client trying connection
     clientInfo = []
     statusClient, clientInfo = lookForClientInDatabase(mcuid)
     if(statusClient== SUCCESSFUL):
          printDebugL3("Client Info {}".format(clientInfo))
          printDebugL3("Client {} exists in database".format(mcuid))
          return SUCCESSFUL, clientInfo
     else:
          printDebugL1("Client {} does not exist in database".format(mcuid))
          printDebugL1("Closing connection")
          closeConnection(connection)
          return CLIENT_UNVERIFIED, clientInfo
                   
def lookForClientInDatabase(mcuid):
     ##Verify existence of client in database for firmware update
     clientInfo = []
     printDebugL3("Opening file {}, to verify MCUID {}".format(databaseName,mcuid))
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
          printDebugL1("Error opening file")
     return CLIENT_UNVERIFIED, clientInfo

def closeConnection(connection):
     printDebugL3("Close of connection has been requested")
     connection.close()
     return SUCCESSFUL

def prepareUpdate(clientInfo, clientsList):
     printDebugL3("Preparing update for {}".format(clientInfo))
     #Buffer data from file to be sent to specific client
     binaryFileLines = []
     bufferingStatus = bufferData(clientInfo[1], binaryFileLines)
     printDebugL3("Status prepare update {}".format(bufferingStatus))
     if (bufferingStatus == SUCCESSFUL):
          FWVersion = re.findall(r"([0-9A-F]+)", clientInfo[2])
          binaryFileLines.append("@{}##".format(FWVersion[0]))
          printDebugL3("Buffered code {}".format(binaryFileLines))
          printDebugL3("Code buffer done successfully") 
          clientsList.append({"mcuid":clientInfo[0], "filename":clientInfo[1], "codelines": binaryFileLines, "status": READY_TO_UPDATE})                 
          return SUCCESSFUL
     if (bufferingStatus == BUFFERING_CODE_INCOMPLETE):
          ##Pending development
          printDebugL3("Incomplete buffering code")
          return BUFFERING_CODE_INCOMPLETE
     else:
          return UNABLE_BUFFERING_CODE

def bufferData(filename, binaryFileLines):
     countLines = 0
     path = pathBinaryFiles+"/"+ filename
     if (os.path.exists(path)== False):
          printDebugL1("Required file does not exist {}".format(path))
          return UNABLE_BUFFERING_CODE
     with open(path, 'r') as file:
          printDebugL3("Opening file {}".format(path))
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

def sendUpdate(connection, address, mcuid, clientToUpdate, sock):
     sock.settimeout(TIMEOUT)
     for codechunk in clientToUpdate[0]['codelines']:
          if (validateCodeChunk(codechunk) == SUCCESSFUL):
               printDebugL3("Data from server {}".format(codechunk))
               connection.send(bytes(codechunk))
               try:
                    receivedData = connection.recv(1024)
                    printDebugL3("Data from client: {}".format(receivedData))
                    if (receivedData == ackClient):
                         continue
                    else:
                         connection.close()
                         return TIMEOUT_CONNECTION
               except socket.timeout as e:
                         printDebugL1("Timeout exceed {}".format(e))
          else:
               continue 
     printDebugL3("Update finished")
     closeConnection(connection)
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
     connectionsList = [] # List of client connections being attended by the server in one moment
     clientsList = [] #List of mcuid, name of file and firmware version from devices being updated
     createServer(connectionsList, clientsList)
   
