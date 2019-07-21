##@package Server.py
#Create a server and enable REST API for firmware updates

import socket
import re

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

#Standard dataframes 
allowedUpdate = "@4#" #Frame sent from server to ack MCUID provided by client
bannedUpdate = "@0#"  #Frame sent from server to deny update to client that requested it
ackClient = "@"

bufferSizeFile = 10 # Number f lines per file to buffered by server
port = 4000 #Port selected from server side to run communication
maxBytes = 1024     #Bytes to be received by connection
pathBinaryFiles = "./../bin"

##Choose debug level of server
# 0 Disabled 
# 1 Error
# 2 Alert
# 3 Log
debugLevel = 3

#Database name file 
databaseName = "./../Database/devices2update.txt"

#Timeout for open sockets
timeout = 30

def printDebugL1(message):
     if (debugLevel >= 1):
          print(message)
     return SUCCESSFUL
          
def printDebugL2(message):
     if (debugLevel >= 2):
          print(message)
     return SUCCESSFUL

def printDebugL3(message):
     if (debugLevel >= 3):
          print(message)
     return SUCCESSFUL

def createServer(connectionsList, clientsList):
     ## Create server
     # AF_INET: For Ipv4 connections
     # SOCK_STREAM: For use of TCP/IP stack
     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
     sock.settimeout(timeout)
     host = socket.gethostname()
     printDebugL3("Hostname {}".format(host))
     
     #For binding address and port
     # 0.0.0.0 because that makes our server available over any IP address
     sock.bind(('127.0.0.1',4000))
    
     #Listen argument: Maximum in queue pendings
     sock.listen(5)
     printDebugL1("Server ready to listen")
     acceptConnections(connectionsList, clientsList, sock)

def acceptConnections(connectionsList, clientsList, sock):
     while True:
          #Accept the connection from the address
          connection, address = sock.accept() 
          printDebugL1("Accepted connection from {}".format(connection))
          if (verifyStartedConnection(connectionsList, connection) == NOT_STARTED_CONNECTION):
               #Verify if id client belongs to database
               mcuid = getMCUID(connection, address)
               if (verifyClientId(connection, address, mcuid, clientsList) == SUCCESSFUL):
                    connection.send(allowedUpdate)
                    printDebugL3("Allowing update to {}".format(mcuid))
                    printDebugL3("Starting update to {}".format(mcuid))
                    sendUpdate(connection,address, mcuid, clientsList)
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
          return int(mcuid[0])
     else:
          return UNFORMATTED_MCUID

def verifyClientId(connection, address, mcuid, clientsList):
     ## Verify client trying connection
     if(lookForClientInDatabase(mcuid, clientsList)== SUCCESSFUL):
          printDebugL1("Client {} exists in database".format(mcuid))
          return SUCCESSFUL
     else:
          printDebugL3("Client {} does not exist in database".format(mcuid))
          printDebugL3("Closing connection")
          closeConnection(connection)
          return CLIENT_UNVERIFIED

                   
def lookForClientInDatabase(mcuid, clientsList):
     ##Verify existence of client in database for firmware update
     printDebugL3("Opening file to verify MCUID {}".format(mcuid))
     with open("databaseName", 'r') as file:
          for line in file:
               clientInfo = line.split(',')
               if (len(clientInfo) == 3):
                    if (clientInfo[0] == mcuid):
                         binaryFileLines = []
                         if (bufferData(clientInfo[1], binaryFileLines) == SUCCESSFUL):
                              clientsList.append({"mcuid":clientInfo[0], "filename":clientInfo[1], "FWVersion": clientInfo[2], "codelines": binaryFileLines})
                              file.close()
                              return SUCCESSFUL
                         else:
                              return UNABLE_BUFFERING_CODE
                    else:
                         return CLIENT_UNVERIFIED
               else:
                    return UNPROPER_FILE_FORMAT
     file.close()
     return CLIENT_UNVERIFIED


def closeConnection(connection):
     printDebugL1("Close of connection has been requested")
     connection.close()
     return SUCCESSFUL
     
def bufferData(filename, binaryFileLines):
     countLines = 0
     with open(pathBinaryFiles+"/"+ filename, 'r') as file:
          line = file.readline()
          countLines += 1
          while (line and countLines < bufferSizeFile):
               line = file.readline()
               binaryFileLines.append(line)
               countLines += 1
          file.close()
          return SUCCESSFUL
     return UNABLE_BUFFERING_CODE


def sendUpdate(connection, address, mcuid, clientsList):
     clientToUpdate = filter (lambda client: client['mcuid']==mcuid, clientsList)
     for codechunk in clientToUpdate[0]['codelines']:
          if (validateCodeChunk(codechunk) == SUCCESSFUL):
               connection.send(bytes(codechunk))
               receivedData = connection.recv(1024)
               if (receivedData == ackClient):
                    continue
               else:
                    connection.close()
                    return TIMEOUT_CONNECTION
          else:
               continue
     return SUCCESSFUL

def  validateCodeChunk(codechunk):
     match = re.search(r'^S1|^S2|^S3+[0-9A-F]+\w', codechunk)
     if match:
          return SUCCESSFUL
     else:
          return INVALID_CODE_CHUNK
     

if __name__ == "__main__":
     connectionsList = [] # List of client connections being attended by the server in one moment
     clientsList = [] #List of mcuid, name of file and firmware version from devices being updated
     createServer(connectionsList, clientsList)
   