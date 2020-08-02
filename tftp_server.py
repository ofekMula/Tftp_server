#! /usr/bin/python3
import socket
import sys
import time
import struct
#####finals#########


#opCodes for packets
RRQ = 1
WRQ = 2
DATA = 3
ACK = 4
ERROR = 5
UNKNOWN = 6

#error codes
UNDEFINED = 0
FILE_NOT_FOUND = 1
ACCESS_VIOLATION = 2
DISK_FULL_OR_ALLOCATION_EXCEEDED = 3
ILLEGAL_TFT_OPERATION = 4
UNKNOWN_TRANSFER_ID = 5
FILE_ALREADY_EXISTS = 6
NO_SUCH_USER = 7

#error content
FILE_NOT_FOUND_CONTENT ="File not found."
ACCESS_VIOLATION_CONTENT ="Access violation."
DISK_FULL_OR_ALLOCATION_EXCEEDED_CONTENT ="Disk full or allocation exceeded."
ILLEGAL_TFT_OPERATION_CONTENT = "Illegal TFTP operation."
UNKNOWN_TRANSFER_ID_CONTENT = "Unknown transfer ID."
FILE_ALREADY_EXISTS_CONTENT = "File already exists"
NO_SUCH_USER_CONTENT = "No such user."

BLOCK_DATA_SIZE=512
BLOCK_SIZE=1024
MAX_PORT_NUMBER=65535
MIN_PORT_NUMBER=1024


MODE_OCTET='octet'
connectionFlag=True
stillSending=True
ackFlag=True
leftToWrite=True
TIME_SLEEP=10
FIRST_PACKET_INDEX_WRITE=0
FIRST_PACKET_INDEX_READ=1





def unpackPacket(packet):
	try:
	    opcode=struct.unpack(">h",packet[0:2])
        #case read or write command
	    if opcode[0]==RRQ or opcode[0]==WRQ:
		    stringEnd=packet.find(b'\0',2)
		    #print(stringEnd)
		    fileName=packet[2:stringEnd].decode("utf-8")
		    #print(fileName)
		    firstZero,mode,secondZero=struct.unpack(">c5sc",packet[stringEnd:])
		    if firstZero ==b'\x00' and secondZero== b'\x00' and mode.decode("utf-8")==MODE_OCTET:
			    return (opcode[0],fileName)
		    else:
			   #error!
			    raise struct.error(ILLEGAL_TFT_OPERATION_CONTENT+ ":" +"incorrectly formed packet")
		#case DATA
	    elif opcode[0]==DATA:
		    opcode,blockNumber=struct.unpack(">hh",packet[:4])
		    packetDataLength=len(packet[4:])
		    if packetDataLength>BLOCK_DATA_SIZE :
		        raise struct.error(ILLEGAL_TFT_OPERATION_CONTENT+":incorrectly formed packet") 
		    elif packetDataLength<=BLOCK_DATA_SIZE and packetDataLength>=0 :#left file data to read
			    packetData=packet[4:]
			    if packetDataLength==BLOCK_DATA_SIZE :#left bytes to read from file 
				    #True is for knowing that we need to make another iteration of reading bytes 
			        #print("got here DATA")
				    return(opcode,blockNumber,packetData,True)
			    else:# packetData<512
				    #False for knowing that this is the last data packet
				    return(opcode,blockNumber,packetData,False)
	    #error case
	    elif opcode[0]==ERROR:
		    opcode,errorcode=struct.unpack(">hh",packet[:4])
		    stringEnd=packet.find(b'\0',4)
		    #print(packet.decode("utf-8") + " "+ packet)
            #verifying that the last char is '\0' which means the packet is ending with string
		    if(stringEnd==-1 or stringEnd==len(packet)-1):
		        errorContent=packet[4:].decode("utf-8")
			    #False here is to verify that we got the ERROR packet from client.
		        return(opcode,errorcode,errorContent,False)
		    else:
			    raise struct.error(ILLEGAL_TFT_OPERATION_CONTENT+ ":" +"incorrectly formed packet")

	    #case ACK
	    elif opcode[0]==ACK:
	        opcode,blockNumber=struct.unpack(">hh",packet)
	        return (opcode,blockNumber)
	        	
	#we got and exception and need to send an ERROR packet . True here is for knowing that we send to client an error
	except FileNotFoundError as e:
		return (ERROR,FILE_NOT_FOUND,FILE_NOT_FOUND_CONTENT,True)

	except PermissionError:
		return (ERROR,ACCESS_VIOLATION,ACCESS_VIOLATION_CONTENT,True)
	
	except MemoryError :
		return (ERROR,DISK_FULL_OR_ALLOCATION_EXCEEDED,DISK_FULL_OR_ALLOCATION_EXCEEDED_CONTENT,True)
	
	
	except FileExistsError:
		return (ERROR,FILE_ALREADY_EXISTS,FILE_ALREADY_EXISTS_CONTENT,True)	
	
	except NameError as e:
		return (ERROR,NO_SUCH_USER,NO_SUCH_USER_CONTENT,True)
	

def makeACKPacket(opCode,blockNumber):
	packet=struct.pack(">hh",opCode,blockNumber)
	return packet
def makeErrorPacket(opCode,errorcode,errorContent):
	packet= struct.pack(">hh",opCode,errorcode)
	packet=packet+errorContent.encode("utf-8")
	return packet
#we assume that the data is in bytes
def makeDataPacket(opCode,blocknumber,data):
    packet= struct.pack(">hh",opCode,blocknumber)+data
    return packet

def compareAdresses(clientAddress,address):
	if address is None:
		return False
	elif clientAddress[0]!=address[0] or clientAddress[1]!=address[1] :
		return False
	return True
#make validation of the command argument  server need only port number
def validCommandArg(argv):
	try:
	    if len(argv)!=2:
		    print("the server demands available PORT number")
		    return False
	    if int(argv[1]) < 0 or int(argv[1])>MAX_PORT_NUMBER :
		    print("the server demands port number between 0 to 65535")
		    return False
	    return True
	except Exception as e:
		print("the server demands port number between 0 to 65535")
		return False

# running the tftp server
def main(PORT):
	# need to make ERROR 
    #serverPort=random(MIN_PORT_NUMBER,MAX_PORT_NUMBER)
    serverTFTPSocket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    serverTFTPSocket.bind(('',PORT))
  	#gets a connection
    while(connectionFlag==True):
        #getting request from connected user
        try:
            clientRequest,clientAddress=serverTFTPSocket.recvfrom(BLOCK_SIZE)
            #need to unpack clientReques
            packet=unpackPacket(clientRequest)
            ##need to treat get(write)/put(read)/quit (exit)
            #get case - send file to client
            #for receiving file WRQ
            if(packet[0]==WRQ):
                blockNumber=FIRST_PACKET_INDEX_WRITE
                file=open(packet[1],"ab")
                #retransmission try number
                retryNumber=0
                timeBegin=time.time()
                ackPacket=makeACKPacket(ACK,blockNumber)
                serverTFTPSocket.sendto(ackPacket,clientAddress)
                #NEED TO ADD TIMER
                leftToWrite=True
                while(leftToWrite ):
        	        #check if the packet is lost6
        	        timeSample=time.time()
        	        #still got time to try again
        	        if timeSample-timeBegin>=10 :
        		        #we havent retransmitted packet more than 2 times
        		        if retryNumber< 2:
        			        #sample begin time again
        			        timeBegin=time.time()
        			        #making retransmission
        			        serverTFTPSocket.sendto(makeACKPacket(ACK,blockNumber),clientAddress)
        			        retryNumber=retryNumber+1 
        			        continue
        	            #time out - close connection

        		        else:
        		            serverTFTPSocket.sendto(makeErrorPacket(ERROR,ILLEGAL_TFT_OPERATION,ILLEGAL_TFT_OPERATION_CONTENT),clientAddress)
        		            print("connection timed out")
        		            leftToWrite=False
        		            continue   
        	        dataPacket,address=serverTFTPSocket.recvfrom(BLOCK_SIZE)
        	        #the data is from the connected client
        	        if address is None:
        	        	leftToWrite=False
        	        	serverTFTPSocket.sendto(makeErrorPacket(ERROR,UNKNOWN_TRANSFER_ID,UNKNOWN_TRANSFER_ID_CONTENT),clientAddress)
        	        	continue

        	        if compareAdresses(clientAddress,address):
        		        packet=unpackPacket(dataPacket)
        		        #by using the unpack func we promised that if the tuple contains the right opcode then the packet is build right
        		        if packet[0]==DATA:
        		            if packet[1]==blockNumber+1:
        		                blockNumber=blockNumber+1
        		                file.write(packet[2])
        		                #left to right is in index 3 in packet tuple
        		                leftToWrite=packet[3]
        		                if not leftToWrite:
        		                    file.close()
        		                # we appended the data to the file. now we need to send an ACK packet
        		                serverTFTPSocket.sendto(makeACKPacket(ACK,blockNumber),clientAddress)
        		                '''
        		                print("we sent packet type ", ACK)
        		                print("we sent packet number ", packet[1])
        		        	    '''
        		            #we got packet with different block number.
        		            else:
        		            	serverTFTPSocket.sendto(makeErrorPacket(ERROR,ILLEGAL_TFT_OPERATION,ILLEGAL_TFT_OPERATION_CONTENT),clientAddress)
        		    	        print("got a packet with the same previous block number")
        		    	        leftToWrite=False
        		    	        continue	
        		        # we got an ERROR PACKET. CLOSE CONNNECTION
        		        elif packet[0]==ERROR:
        		            leftToWrite=False
        		            if packet[3]:
        		                print("an error has raised in server:"+ packet[2])
        		                errorPacket=makeErrorPacket(packet[0],packet[1],packet[2])
        		                serverTFTPSocket.sendto(errorPacket,clientAddress)
        		                continue
        		            else:
        		                print(" client sent an error package. connection terminated with client"+ packet[1]+packet[2])
        		                continue

        		    #we got packet from another client. ned to close him and send him an error packet
        	        else:
        		        print("an error has raised in server:"+ packet[2])
        		        errorPacket=makeErrorPacket(packet[0],packet[1],packet[2])
        		        serverTFTPSocket.sendto(errorPacket,address)

			#case packet is READ. - write to client
            elif(packet[0]==RRQ):
                blockNumber=FIRST_PACKET_INDEX_READ
                file=open(packet[1],"rb")
                tosend=file.read(BLOCK_DATA_SIZE)
                #retransmission try number
                retryNumber=0
                timeBegin=time.time()
                DataPacket=makeDataPacket(DATA,blockNumber,tosend) 
                serverTFTPSocket.sendto(DataPacket,clientAddress)
                leftToRead=True
                lastACK=False
                while(leftToRead):
                    #check if the packet is lost
                    timeSample=time.time()
                    #still got time to try again
                    if timeSample-timeBegin>=10 :
                        #we havent retransmitted packet more than 2 times
                        if retryNumber< 2:
                            #sample begin time again
                            timeBegin=time.time()
                            #making retransmission
                            serverTFTPSocket.sendto(makeDataPacket(DATA,blockNumber,tosend),clientAddress)
                            retryNumber=retryNumber+1 
                            continue
                        #time out - close connection

                        else:
                            serverTFTPSocket.sendto(makeErrorPacket(ERROR,ILLEGAL_TFT_OPERATION,ILLEGAL_TFT_OPERATION_CONTENT),clientAddress)
                            print("connection timed out")
                            leftToRead=False
                            continue   
                    dataPacket,address=serverTFTPSocket.recvfrom(BLOCK_SIZE)
                    if lastACK:#we now getting the last ACK...closing the file
                        leftToRead=False
                        continue
                    #the data is from the connected client
                    if compareAdresses(clientAddress,address):
                        packet=unpackPacket(dataPacket)
                        #by using the unpack func we promised that if the tuple contains the right opcode then the packet is build right
                        if packet[0]==ACK:
                            if packet[1]==blockNumber:
                                blockNumber=blockNumber+1
                                tosend=file.read(BLOCK_DATA_SIZE)
                                #left to right is in index 3 in packet tuple
                                
                                if len(tosend)<BLOCK_DATA_SIZE:
                                    packet=makeDataPacket(DATA,blockNumber,tosend)
                                    serverTFTPSocket.sendto(packet,clientAddress)
                                    lastACK=True
                                    continue
                                else:
                                    serverTFTPSocket.sendto(makeDataPacket(DATA,blockNumber,tosend),clientAddress)

                                # we appended the data to the file. now we need to send an ACK packet

                                
                                '''
                                print("we sent packet type ", ACK)
                                print("we sent packet number ", packet[1])
                                '''
                            #we got packet with different block number.
                            else:
                                serverTFTPSocket.sendto(makeErrorPacket(ERROR,ILLEGAL_TFT_OPERATION,ILLEGAL_TFT_OPERATION_CONTENT),clientAddress)
                                print("got a packet with the same previous block number")
                                leftToRead=False
                                continue    
                        # we got an ERROR PACKET. CLOSE CONNNECTION
                        elif packet[0]==ERROR:
                            leftToRead=False
                            if packet[3]:
                                print("an error has raised in server:"+ packet[2])
                                errorPacket=makeErrorPacket(packet[0],packet[1],packet[2])
                                serverTFTPSocket.sendto(errorPacket,clientAddress)
                                continue
                            else:
                                print("client sent an error package. connection terminated with client")
                                continue



                    #we got packet from another client. ned to close him and send him an error packet
                    else:
                        print("an error has raised in server1:"+ packet[2])
                        errorPacket=makeErrorPacket(packet[0],packet[1],packet[2])
                        serverTFTPSocket.sendto(errorPacket,address)

                file.close()        

            elif packet[0]==ERROR:
                leftToRead=False
                if packet[3]:
                    print("an error has raised in server2:"+ packet[2])
                    errorPacket=makeErrorPacket(packet[0],packet[1],packet[2])
                    serverTFTPSocket.sendto(errorPacket,clientAddress)
                    continue
                else:
                    print("client sent an error package. connection terminated with client")
                    continue
            
            else:#case client sent garbage information
                print(packet)
                leftToWrite=False
                print("client sent an unrecognized package. connection terminated with client")
                serverTFTPSocket.sendto(makeErrorPacket(ERROR,ILLEGAL_TFT_OPERATION,ILLEGAL_TFT_OPERATION_CONTENT),clientAddress)
                continue
		#an exception has raised.need to send to client exception and terminate connection
        
        except FileNotFoundError :
        	serverTFTPSocket.sendto(makeErrorPacket(ERROR,FILE_NOT_FOUND,FILE_NOT_FOUND_CONTENT),clientAddress)

        except PermissionError:
            serverTFTPSocket.sendto(makeErrorPacket(ERROR,ACCESS_VIOLATION,ACCESS_VIOLATION_CONTENT),clientAddress)
	
        except MemoryError :
           serverTFTPSocket.sendto(makeErrorPacket(ERROR,DISK_FULL_OR_ALLOCATION_EXCEEDED,DISK_FULL_OR_ALLOCATION_EXCEEDED_CONTENT),clientAddress)
	
        except FileExistsError:
            serverTFTPSocket.sendto(makeErrorPacket(ERROR,FILE_ALREADY_EXISTS,FILE_ALREADY_EXISTS_CONTENT),clientAddress)
	   
        except NameError as e:
            print(e)
            serverTFTPSocket.sendto(makeErrorPacket(ERROR,NO_SUCH_USER,NO_SUCH_USER_CONTENT),clientAddress)


    #close resources
    serverTFTPSocket.close()
#execute tftp_server.py file 
#validy check- if valid we start the server and go main
if validCommandArg(sys.argv):
    try:
        main(int(sys.argv[1]))
    except socket.error as e:
    	print(e)
    except FileNotFoundError:
    	print(FILE_NOT_FOUND_CONTENT)



