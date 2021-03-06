#!/usr/bin/env python

import sys
import os
import os.path
import socket
import thread
import time
import httplib
import BaseHTTPServer
import SimpleHTTPServer


if __name__ != "__main__":
    raise "This must be run as a command, not used as a module!"

#import tlslite
#from tlslite.constants import AlertDescription, Fault

#from tlslite.utils.jython_compat import formatExceptionTrace
#from tlslite.X509 import X509, X509CertChain

from tlslite.api import *

def parsePrivateKey(s):
    try:
        return parsePEMKey(s, private=True)
    except Exception, e:
        print e
        return parseXMLKey(s, private=True)


def clientTest(address, dir):

    #Split address into hostname/port tuple
    address = address.split(":")
    if len(address)==1:
        address.append("4443")
    address = ( address[0], int(address[1]) )

    def connect():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if hasattr(sock, 'settimeout'): #It's a python 2.3 feature
            sock.settimeout(5)
        sock.connect(address)
        c = TLSConnection(sock)
        return c

    test = 0

    badFault = False

    print "Test 23 - throughput test"
    for implementation in implementations:
        for cipher in ["aes128", "aes256", "3des", "rc4"]:
            if cipher == "3des" and implementation not in ("openssl", "cryptlib", "pycrypto"):
                continue

            print "Test 23:",
            connection = connect()

            settings = HandshakeSettings()
            settings.cipherNames = [cipher]
            settings.cipherImplementations = [implementation, "python"]
            connection.handshakeClientSharedKey("shared", "key", settings=settings)
            print ("%s %s:" % (connection.getCipherName(), connection.getCipherImplementation())),

            startTime = time.clock()
            connection.write("hello"*10000)
            h = connection.read(min=50000, max=50000)
            stopTime = time.clock()
            print "100K exchanged at rate of %d bytes/sec" % int(100000/(stopTime-startTime))

            assert(h == "hello"*10000)
            connection.close()
            connection.sock.close()

    print "Test 24 - Internet servers test"
    try:
        i = IMAP4_TLS("cyrus.andrew.cmu.edu")
        i.login("anonymous", "anonymous@anonymous.net")
        i.logout()
        print "Test 24: IMAP4 good"
        p = POP3_TLS("pop.gmail.com")
        p.quit()
        print "Test 24: POP3 good"
    except socket.error, e:
        print "Non-critical error: socket error trying to reach internet server: ", e

    if not badFault:
        print "Test succeeded"
    else:
        print "Test failed"


def serverTest(address, dir):
    #Split address into hostname/port tuple
    address = address.split(":")
    if len(address)==1:
        address.append("4443")
    address = ( address[0], int(address[1]) )

    #Connect to server
    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lsock.bind(address)
    lsock.listen(5)

    def connect():
        return TLSConnection(lsock.accept()[0])

    print "Test 23 - throughput test"
    for implementation in implementations:
        for cipher in ["aes128", "aes256", "3des", "rc4"]:
            if cipher == "3des" and implementation not in ("openssl", "cryptlib", "pycrypto"):
                continue

            print "Test 23:",
            connection = connect()

            settings = HandshakeSettings()
            settings.cipherNames = [cipher]
            settings.cipherImplementations = [implementation, "python"]

            connection.handshakeServer(sharedKeyDB=sharedKeyDB, settings=settings)
            print connection.getCipherName(), connection.getCipherImplementation()
            h = connection.read(min=50000, max=50000)
            assert(h == "hello"*10000)
            connection.write(h)
            connection.close()
            connection.sock.close()

    print "Test succeeded"












if len(sys.argv) == 1 or (len(sys.argv)==2 and sys.argv[1].lower().endswith("help")):
    print ""
    print "Version: 0.3.8"
    print ""
    print "RNG: %s" % prngName
    print ""
    print "Modules:"
    if cryptlibpyLoaded:
        print "  cryptlib_py : Loaded"
    else:
        print "  cryptlib_py : Not Loaded"
    if m2cryptoLoaded:
        print "  M2Crypto    : Loaded"
    else:
        print "  M2Crypto    : Not Loaded"
    if pycryptoLoaded:
        print "  pycrypto    : Loaded"
    else:
        print "  pycrypto    : Not Loaded"
    if gmpyLoaded:
        print "  GMPY        : Loaded"
    else:
        print "  GMPY        : Not Loaded"
    print ""
    print "Commands:"
    print ""
    print "  clientcert      <server> [<chain> <key>]"
    print "  clientsharedkey <server> <user> <pass>"
    print "  clientsrp       <server> <user> <pass>"
    print "  clienttest      <server> <dir>"
    print ""
    print "  serversrp       <server> <verifierDB>"
    print "  servercert      <server> <chain> <key> [req]"
    print "  serversrpcert   <server> <verifierDB> <chain> <key>"
    print "  serversharedkey <server> <sharedkeyDB>"
    print "  servertest      <server> <dir>"
    sys.exit()

cmd = sys.argv[1].lower()

class Args:
    def __init__(self, argv):
        self.argv = argv
    def get(self, index):
        if len(self.argv)<=index:
            raise SyntaxError("Not enough arguments")
        return self.argv[index]
    def getLast(self, index):
        if len(self.argv)>index+1:
            raise SyntaxError("Too many arguments")
        return self.get(index)

args = Args(sys.argv)

def reformatDocString(s):
    lines = s.splitlines()
    newLines = []
    for line in lines:
        newLines.append("  " + line.strip())
    return "\n".join(newLines)

try:
    if cmd == "clienttest":
        address = args.get(2)
        dir = args.getLast(3)
        clientTest(address, dir)
        sys.exit()

    elif cmd.startswith("client"):
        address = args.get(2)

        #Split address into hostname/port tuple
        address = address.split(":")
        if len(address)==1:
            address.append("4443")
        address = ( address[0], int(address[1]) )

        def connect():
            #Connect to server
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if hasattr(sock, "settimeout"):
                sock.settimeout(5)
            sock.connect(address)

            #Instantiate TLSConnections
            return TLSConnection(sock)

        try:
            if cmd == "clientsrp":
                username = args.get(3)
                password = args.getLast(4)
                connection = connect()
                start = time.clock()
                connection.handshakeClientSRP(username, password)
            elif cmd == "clientsharedkey":
                username = args.get(3)
                password = args.getLast(4)
                connection = connect()
                start = time.clock()
                connection.handshakeClientSharedKey(username, password)
            elif cmd == "clientcert":
                certChain = None
                privateKey = None
                if len(sys.argv) > 3:
                    certFilename = args.get(3)
                    keyFilename = args.getLast(4)

                    s1 = open(certFilename, "rb").read()
                    s2 = open(keyFilename, "rb").read()

                    #Try to create X.509 cert chain
                    if not certChain:
                        x509 = X509()
                        x509.parse(s1)
                        certChain = X509CertChain([x509])
                        privateKey = parsePrivateKey(s2)

                connection = connect()
                start = time.clock()
                connection.handshakeClientCert(certChain, privateKey)
            else:
                raise SyntaxError("Unknown command")

        except TLSLocalAlert, a:
            if a.description == AlertDescription.bad_record_mac:
                if cmd == "clientsharedkey":
                    print "Bad sharedkey password"
                else:
                    raise
            elif a.description == AlertDescription.user_canceled:
                print str(a)
            else:
                raise
            sys.exit()
        except TLSRemoteAlert, a:
            if a.description == AlertDescription.unknown_psk_identity:
                if cmd == "clientsrp":
                    print "Unknown username"
                else:
                    raise
            elif a.description == AlertDescription.bad_record_mac:
                if cmd == "clientsrp":
                    print "Bad username or password"
                else:
                    raise
            elif a.description == AlertDescription.handshake_failure:
                print "Unable to negotiate mutually acceptable parameters"
            else:
                raise
            sys.exit()

        stop = time.clock()
        print "Handshake success"
        print "  Handshake time: %.4f seconds" % (stop - start)
        print "  Version: %s.%s" % connection.version
        print "  Cipher: %s %s" % (connection.getCipherName(), connection.getCipherImplementation())
        if connection.session.srpUsername:
            print "  Client SRP username: %s" % connection.session.srpUsername
        if connection.session.sharedKeyUsername:
            print "  Client shared key username: %s" % connection.session.sharedKeyUsername
        if connection.session.clientCertChain:
            print "  Client fingerprint: %s" % connection.session.clientCertChain.getFingerprint()
        if connection.session.serverCertChain:
            print "  Server fingerprint: %s" % connection.session.serverCertChain.getFingerprint()
        connection.close()
        connection.sock.close()

    elif cmd.startswith("server"):
        address = args.get(2)

        #Split address into hostname/port tuple
        address = address.split(":")
        if len(address)==1:
            address.append("4443")
        address = ( address[0], int(address[1]) )

        verifierDBFilename = None
        sharedKeyDBFilename = None
        certFilename = None
        keyFilename = None
        sharedKeyDB = None
        reqCert = False

        if cmd == "serversrp":
            verifierDBFilename = args.getLast(3)
        elif cmd == "servercert":
            certFilename = args.get(3)
            keyFilename = args.get(4)
            if len(sys.argv)>=6:
                req = args.getLast(5)
                if req.lower() != "req":
                    raise SyntaxError()
                reqCert = True
        elif cmd == "serversrpcert":
            verifierDBFilename = args.get(3)
            certFilename = args.get(4)
            keyFilename = args.getLast(5)
        elif cmd == "serversharedkey":
            sharedKeyDBFilename = args.getLast(3)
        elif cmd == "servertest":
            address = args.get(2)
            dir = args.getLast(3)
            serverTest(address, dir)
            sys.exit()

        verifierDB = None
        if verifierDBFilename:
            verifierDB = VerifierDB(verifierDBFilename)
            verifierDB.open()

        sharedKeyDB = None
        if sharedKeyDBFilename:
            sharedKeyDB = SharedKeyDB(sharedKeyDBFilename)
            sharedKeyDB.open()

        certChain = None
        privateKey = None
        if certFilename:
            s1 = open(certFilename, "rb").read()
            s2 = open(keyFilename, "rb").read()

            #Try to create X.509 cert chain
            if not certChain:
                x509 = X509()
                x509.parse(s1)
                certChain = X509CertChain([x509])
                privateKey = parsePrivateKey(s2)



        #Create handler function - performs handshake, then echos all bytes received
        def handler(sock):
            try:
                connection = TLSConnection(sock)
                settings = HandshakeSettings()
                connection.handshakeServer(sharedKeyDB=sharedKeyDB, verifierDB=verifierDB, \
                                           certChain=certChain, privateKey=privateKey, \
                                           reqCert=reqCert, settings=settings)
                print "Handshake success"
                print "  Version: %s.%s" % connection.version
                print "  Cipher: %s %s" % (connection.getCipherName(), connection.getCipherImplementation())
                if connection.session.srpUsername:
                    print "  Client SRP username: %s" % connection.session.srpUsername
                if connection.session.sharedKeyUsername:
                    print "  Client shared key username: %s" % connection.session.sharedKeyUsername
                if connection.session.clientCertChain:
                    print "  Client fingerprint: %s" % connection.session.clientCertChain.getFingerprint()
                if connection.session.serverCertChain:
                    print "  Server fingerprint: %s" % connection.session.serverCertChain.getFingerprint()

                s = ""
                while 1:
                    newS = connection.read()
                    if not newS:
                        break
                    s += newS
                    if s[-1]=='\n':
                        connection.write(s)
                        s = ""
            except TLSLocalAlert, a:
                if a.description == AlertDescription.unknown_psk_identity:
                    print "Unknown SRP username"
                elif a.description == AlertDescription.bad_record_mac:
                    if cmd == "serversrp" or cmd == "serversrpcert":
                        print "Bad SRP password for:", connection.allegedSrpUsername
                    else:
                        raise
                elif a.description == AlertDescription.handshake_failure:
                    print "Unable to negotiate mutually acceptable parameters"
                else:
                    raise
            except TLSRemoteAlert, a:
                if a.description == AlertDescription.bad_record_mac:
                    if cmd == "serversharedkey":
                        print "Bad sharedkey password for:", connection.allegedSharedKeyUsername
                    else:
                        raise
                elif a.description == AlertDescription.user_canceled:
                    print "Handshake cancelled"
                elif a.description == AlertDescription.handshake_failure:
                    print "Unable to negotiate mutually acceptable parameters"
                elif a.description == AlertDescription.close_notify:
                    pass
                else:
                    raise

        #Run multi-threaded server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(address)
        sock.listen(5)
        while 1:
            (newsock, cliAddress) = sock.accept()
            thread.start_new_thread(handler, (newsock,))


    else:
        print "Bad command: '%s'" % cmd
except TLSRemoteAlert, a:
    print str(a)
    raise





