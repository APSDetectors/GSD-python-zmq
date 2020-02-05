#!/usr/bin/python2.6

###!/usr/bin/python2.7
import zmq
import numpy as np
#from zclient import zclient
import datetime, time
import sys

class zclient(object):
    ZMQ_DATA_PORT = "5556"
    ZMQ_CNTL_PORT = "5555"
    TOPIC_DATA = "data"
    TOPIC_META = "meta"
    def __init__(self, connect_str):
        self.__context = zmq.Context();
        self.data_sock = self.__context.socket(zmq.SUB);
        self.ctrl_sock = self.__context.socket(zmq.REQ);

        self.data_sock.connect(connect_str + ":" + zclient.ZMQ_DATA_PORT)
        self.data_sock.setsockopt(zmq.SUBSCRIBE, zclient.TOPIC_DATA)
        self.data_sock.setsockopt(zmq.SUBSCRIBE, zclient.TOPIC_META)

        self.ctrl_sock.connect(connect_str + ":" + zclient.ZMQ_CNTL_PORT)

    def __cntrl_recv(self):
        msg = self.ctrl_sock.recv()
        dat = np.frombuffer(msg, dtype=np.uint32)
        return dat

    def __cntrl_send(self, payload):
        self.ctrl_sock.send(np.array(payload, dtype=np.uint32))

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

    def set_frametime(self, value):
	    self.write(0xD4,value)
		print "FrameTime set to %i x 40ns" % value


    def trigger_data(self):
        self.__cntrl_send([0x2, 0x0, 0x0])
        self.__cntrl_recv()


    def get_data(self, filename, maxevents):
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
                np.savetxt("meta.txt",meta_data,fmt="%x")
            if (address == zclient.TOPIC_DATA):
                print "Event data received"
                data = np.frombuffer(msg, dtype=np.uint32)
                fd.write(data)
                totallen = totallen + len(data)
                print "Msg Num: %d, Msg len: %d, Tot len: %d" % (self.nbr,len(data),totallen)
                #print data
                if totallen > maxevents:
                    break;
                self.nbr += 1

        stop = datetime.datetime.now()

        fd.close()
        elapsed = stop - start
        sec = elapsed.seconds + elapsed.microseconds*1.0e-6
        print "Processing time:", elapsed, sec;

        print "Total Image Size: %d (%d bytes)" % (totallen,totallen*4)
        bitrate = (float(totallen*4)/float(sec)/1024/1024)
        print ('Received %d frames at %f MBps' % (self.nbr, bitrate))


        return totallen, bitrate


if __name__ == "__main__":

    if (len(sys.argv) != 3):
        print "Usage ./maia_zclient2 numevents filename"
        sys.exit();
    maxevents = int(sys.argv[1])
    filename = sys.argv[2]

    ip_addr = "tcp://10.0.143.160"
    zc = zclient(ip_addr)
    print "Starting ZClient..."
    zc.read(0)

    print "MaxEvents = %d" % (maxevents)
    totallen, bitrate = zc.get_data(filename,maxevents)

