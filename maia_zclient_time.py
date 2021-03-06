#!/usr/bin/python2.6





'''

execfile('maia_zclient.py')


maxevents = 100
filename = 'testfile.bin'

ip_addr = "tcp://10.0.143.160"
zc = zclient(ip_addr)
print "Starting ZClient..."
zc.read(0)

print "MaxEvents = %d" % (maxevents)
totallen, bitrate = zc.get_data(filename,maxevents)

totallen, bitrate = zc.get_data('test')

zc.context.destroy()

zc.fifo_reset()

zc.get_framenum()


REG_STARTFRAME=0xD0


FIFORDCNTREG=0x19
zc.read(FIFORDCNTREG)

REG_SWDEBUG=0xE1
zc.write(REG_SWDEBUG,1)


zc.write(REG_STARTFRAME,1)

zc.read(REG_STARTFRAME)

zc.set_bufsize(10)

 zc.fifo_reset()




zc.set_framelen(0.02)

zc.start_frame()

totallen, bitrate = zc.get_data('test')

parseFile('test.dat',numbytes=1000000,isprint = False)



zc.monitor_data()


'''







###!/usr/bin/python2.7
import zmq
import numpy as np
#from zclient import zclient
import datetime, time
import sys
import struct





def parseFile(fname,numbytes=-1,isprint = False):

    fd = open(fname,'rb')
    if numbytes==-1:
        rawdat = fd.read()
    else:
       rawdat = fd.read(numbytes)
        
    fd.close()

    nints = len(rawdat)/4;
    
    intdat = struct.unpack('I'*nints ,rawdat)
    
    pds = np.zeros(nints/2)
    tds = np.zeros(nints/2)
    
    
    for i in range(0,nints,2):       
        quad = (intdat[i] & 0x60000000) >> 29;
        chipnum = (intdat[i] & 0x18000000) >> 27;
        chan = (intdat[i] & 0x07C00000) >> 22;
        
        
        pd = (intdat[i] & 0xFFF);
        td = (intdat[i] & 0x3FF000) >> 12; 
        
        pds[i/2]=pd
        tds[i/2] = td
        
        ts = (intdat[i+1] & 0x1FFFFFFF);
        if isprint:
            print "Address: Quad=%d\tChipNum=%d\tChan=%d"%(quad,chipnum,chan)
            print "PD: %d"%pd
            print "TD: %d"%td
            print "Timestamp: %u"%ts


    figure(1)
    clf()
    hist(pds)
    
    figure(2)
    clf()
    hist(tds)
    
    
    #return(intdat)
    #pdh = np.histogram(pds,bins=10)
    #tdh = np.histogram(tds,bins=10)
    #return(pdh)
    
    #clf()
    #plot(pdh[1],pdh[0])
    #plot(tdh[1],tdh[0])
    


        




class zclient(object):
    ZMQ_DATA_PORT = "5556"
    ZMQ_CNTL_PORT = "5555"
    TOPIC_DATA = "data"
    TOPIC_META = "meta"
    TOPIC_STRT = "strt"
    TOPIC_FNUM = "fnum"
    def __init__(self, connect_str):
        self.context = zmq.Context();
        self.data_sock = self.context.socket(zmq.SUB);
        self.ctrl_sock = self.context.socket(zmq.REQ);

        self.data_sock.connect(connect_str + ":" + zclient.ZMQ_DATA_PORT)
        self.data_sock.setsockopt(zmq.SUBSCRIBE, zclient.TOPIC_DATA)
        self.data_sock.setsockopt(zmq.SUBSCRIBE, zclient.TOPIC_META)
        self.data_sock.setsockopt(zmq.SUBSCRIBE, zclient.TOPIC_STRT)
        self.data_sock.setsockopt(zmq.SUBSCRIBE, zclient.TOPIC_FNUM)

        self.ctrl_sock.connect(connect_str + ":" + zclient.ZMQ_CNTL_PORT)

    def __cntrl_recv(self):
        msg = self.ctrl_sock.recv()
        dat = np.frombuffer(msg, dtype=np.uint32)
        return dat

    def __cntrl_send(self, payload):
        print payload
        self.ctrl_sock.send(np.array(payload, dtype=np.uint32))


    def destroy(self):
        self.context.destroy()

    def write(self, addr, value):
        self.__cntrl_send([0x1, int(addr), int(value)])
        self.__cntrl_recv()

    def read(self, addr):
        self.__cntrl_send([0x0, int(addr), 0x0])
        return int(self.__cntrl_recv()[2])

    def set_burstlen(self,value):
        self.write(0x8C,value)
        print "Burst length set to %d transfers" % value

    def set_bufsize(self,value):
        self.write(0x90,value)
        print "Buffer size set to %d bytes" % value

    def set_rate(self,rate):
        n = int(400e6 / (rate*1e6) - 1)
        self.write(0x98,n)
        print "Rate set to %.2f MHz" % (400e6/(n+1) / 1e6)

    def set_framelen(self,value):
        # 40ns firmware - old
		#print "framelen: %d" %  (value*25000000)
    	# self.write(0xD4,value*25000000)
		# 1 us firmware - new
		print "framelen: %d" %  (value*1000000)
		self.write(0xD4,value*1000000)
		print "Frame length set to %d secs" % value

    def start_frame(self):
        self.write(0xD0,1)
        print "New Frame Initiated..." 

    def get_framenum(self):
        val = self.read(0xD8)
        print "Frame Num=%d" % val
        return val
		
    def set_framemode(self,value):
        self.write(0xDC,value) #0=normal mode, 1=infinite
        print "setting frame mode..."
		
    def fifo_reset(self):
        print "Resetting FIFO.."
        self.write(0x68,4)
        self.write(0x68,1)


    def trigger_data(self):
        self.__cntrl_send([0x2, 0x0, 0x0])
        self.__cntrl_recv()






    def monitor_data2(self):


        while True:
            [address, msg] = self.data_sock.recv_multipart()
            print '%s'%(address)





    def monitor_data(self):


        while True:
            [address, msg] = self.data_sock.recv_multipart()

            if msg == b'END':
                print "Message END received"
            if (address == zclient.TOPIC_META):
                print "Meta data received"
                meta_data = np.frombuffer(msg, dtype=np.uint32)
                print meta_data

            if (address == zclient.TOPIC_STRT):
                print "START FRAME received"
                meta_data = np.frombuffer(msg, dtype=np.uint32)
                print meta_data
            if (address == zclient.TOPIC_FNUM):
                print "fnum received"
                meta_data = np.frombuffer(msg, dtype=np.uint32)
                print meta_data


            if (address == zclient.TOPIC_DATA):
                print "Event data received"
                data = np.frombuffer(msg, dtype=np.uint32)













    def get_data(self, filename, maxevents=-1):
        self.nbr = 0
        totallen = 0

        start = datetime.datetime.now()

        fd = open(filename,'wb')
        print "In Get Data"
        while True:
            [address, msg] = self.data_sock.recv_multipart()

            if msg == b'END':
                print "Received %s messages" % str(self.nbr)
                print "Message END received"
                break
            if (address == zclient.TOPIC_META):
                print "Meta data received"
                meta_data = np.frombuffer(msg, dtype=np.uint32)
                print meta_data
                np.savetxt("%s.txt"%filename,meta_data,fmt="%x")
                break

            if (address == zclient.TOPIC_STRT):
                print "START FRAME received"
                meta_data = np.frombuffer(msg, dtype=np.uint32)
                print meta_data
            if (address == zclient.TOPIC_FNUM):
                print "fnum received"
                meta_data = np.frombuffer(msg, dtype=np.uint32)
                print meta_data


            if (address == zclient.TOPIC_DATA):
                print "Event data received"
                data = np.frombuffer(msg, dtype=np.uint32)
                fd.write(data)
                totallen = totallen + len(data)
                print "Msg Num: %d, Msg len: %d, Tot len: %d" % (self.nbr,len(data),totallen)
                #print data
                if maxevents!=-1 and totallen > maxevents:
                    break;

                self.nbr += 1

        stop = datetime.datetime.now()

        fd.close()
        elapsed = stop - start
        sec = elapsed.seconds + elapsed.microseconds*1.0e-6
        print "Processing time:", elapsed, sec;

        bitrate = (float(totallen*4)/float(sec)/1024/1024)
        print ('Received %d frames at %f MBps' % (self.nbr, bitrate))
        print "Total Image Size: %d (%d bytes)" % (totallen,totallen*4) 
        print "Total Number of Events: %d" % (totallen/2)

        return totallen, bitrate



if __name__ == "__main__":
#def runmain():

    if (len(sys.argv) != 3):
        print "Usage: python maia_zclient_Madden.py exposureTime(sec) filename"
        sys.exit();
    exposureTime = int(sys.argv[1])
    filename = sys.argv[2]

    ip_addr = "tcp://10.0.143.160"
    zc = zclient(ip_addr)
    print "Starting ZClient..."
    zc.read(0)

    zc.set_framemode(0) # Normal mode; Frame starts on FRAME_SOFTTRIG and completes after FRAME_TIME
    zc.fifo_reset()
    zc.set_framelen(exposureTime)
    zc.start_frame()
	
    totallen, bitrate = zc.get_data(filename)

