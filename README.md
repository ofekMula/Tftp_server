# tftp_server
tftp server written in python - based on RFC 1350 (octet mode only):https://tools.ietf.org/html/rfc1350 

1. you can run it in linux OS via terminal.

2. command for execution :
   python3 tftp_server.py [port]
  (port is a known number for the client).
  
3. in order to recieve/send files between client and tftp_server you need a tftp_client.
    
    you can use the built in TFTP client of linux :https://linux.die.net/man/1/tftp.

4. commands for TFTP client:

    a. tftp
    
    b. mode octet
    
    c. connect [ip address of TFTP server] [PORT number]
    
    d.put [filepath]
    
    e.get [file path]
