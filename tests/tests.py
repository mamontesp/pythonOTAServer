import sys
sys.path.insert(0, './../')
import server

def testLookForClientInDatabaseExist():
     mcuid = "0001100023593110965955141"
     clientInfo = []
     if (server.lookForClientInDatabase(mcuid, clientInfo) == server.SUCCESSFUL):
          server.printDebugL1("Successful test")
     else:
          server.printDebugL1("Unsuccessfull test")

def testLookForClientInDatabaseDoesNotExist():
     mcuid = "00000000000000000000000000"
     clientInfo = []
     if (server.lookForClientInDatabase(mcuid, clientInfo) != server.SUCCESSFUL):
          server.printDebugL1("Successful test")
     else:
          server.printDebugL1("Unsuccessfull test")

def testPrepareUpdateNonExistingClient():
     clientInfo = ['0001100023593110965955141','AN2295_TWR_K60.S19','16']
     clientsList= []
     if (server.prepareUpdate(clientInfo, clientsList) == server.SUCCESSFUL):
          server.printDebugL1("{} Successful test".format(testPrepareUpdateNonExistingClient.__name__))
     else:
          server.printDebugL1("{} Unsuccessful test".format(testPrepareUpdateNonExistingClient.__name__))

def testValidateCodeChunkEmpty():
     codechunk = ""
     if (server.validateCodeChunk(codechunk) == server.INVALID_CODE_CHUNK):
          server.printDebugL1("ChunkEmpty Successful test")
     else:
          server.printDebugL1("ChunkEmpty Unsuccessful test")

def testValidateCodeChunkValid():
     codechunk = "S197AAKA9779"
     if (server.validateCodeChunk(codechunk) == server.SUCCESSFUL):
          server.printDebugL1("ChunkValid Successful test")
     else:
          server.printDebugL1("ChunkValid Unsuccessful test")

def testValidateCodeChunkNoValid():
     codechunk = "S786969"
     if (server.validateCodeChunk(codechunk) == server.INVALID_CODE_CHUNK):
          server.printDebugL1("ChunkNoValid Successful test")
     else:
          server.printDebugL1("ChunkNoValid Unsuccessful test")
          
if __name__ == "__main__":
     testLookForClientInDatabaseExist()
     testLookForClientInDatabaseDoesNotExist()
     testPrepareUpdateNonExistingClient()
     testValidateCodeChunkEmpty()
     testValidateCodeChunkValid()
     testValidateCodeChunkNoValid()
     