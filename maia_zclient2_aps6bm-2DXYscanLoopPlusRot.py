#!/usr/bin/python2.7
import zmq
import numpy as np
import datetime, time
import sys
from epics import caget, caput

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


    def set_framelen(self,value):
        self.write(0xD4,value*25000000)
        print "Frame length set to %d secs" % value

    def start_frame(self):
        self.write(0xD0,1)
        print "New Frame Initiated..." 

    def get_framenum(self):
        val = self.read(0xD8)
        print "Frame Num=%d" % val
        return val

    def fifo_reset(self):
        print "Resetting FIFO.."
        self.write(0x68,4)
        self.write(0x68,1)

    def get_frame(self, filename, framenum, framelen):
        self.nbr = 0
        totallen = 0

        #curframe = self.get_framenum()
        curframe = framenum;
        fd = open(filename+str(curframe).rjust(3,'0')+'.dat','wb')

        #self.start_frame()
        #print "In Get Data"
        while True:
            [address, msg] = self.data_sock.recv_multipart()

            if (address == zclient.TOPIC_META):
                print "Ooops...  Meta data received"
                #meta_data = np.frombuffer(msg, dtype=np.uint32)
                #print "Frame #:  %d complete" % (meta_data - 1)
                #fd.close()
                #break

            if (address == zclient.TOPIC_DATA):
                #print "Event data received"
                data = np.frombuffer(msg, dtype=np.uint32)
                fd.write(data)
                totallen = totallen + len(data)
                #print "Events: %d" % (totallen/2)
                if totallen >= (framelen*2):
                    print "Frame #:  %d complete" % framenum
                    fd.close()
                    eventsinframe = totallen
                    totallen = 0;
                    break;
                #print "Msg Num: %d, Msg len: %d, Tot len: %d" % (self.nbr,len(data),totallen)
                #print data


        return eventsinframe/2
        

if __name__ == "__main__":

	if (len(sys.argv) != 8):
	  print "Usage ./maia_zclient2 numframes_x  numframes_y eventsperframe motorstepsize_x(mm) motorstepsize_y(mm) loops filename"
	  sys.exit();

	numframes_x = int(sys.argv[1])
	numframes_y = int(sys.argv[2])
	framelen  = int(sys.argv[3])
	motorstep_x = float(sys.argv[4]) 
	motorstep_y = float(sys.argv[5])
	loops  = int(sys.argv[6])
	filename  = sys.argv[7]
	
	print "Starting Run... NumFrameX:%d  MotorStepSizeX:%f NumFrameY:%d  MotorStepSizeY:%f    EventsPerFrame:%d  Loops:%d" % (numframes_x, motorstep_x, numframes_y, motorstep_y, framelen, loops) 
	motpos_x = caget("6bma1:m19")
	motpos_y = caget("6bma1:m18")  #scale to mm
	print "Inital Motor Position: X: %6.3f  Y: %6.3f " % (motpos_x,motpos_y) 

	# original positions
	# motpos_y is m18-zr
	motpos_y0 = motpos_y
	# motpos_x is m19-yr
	motpos_x0 = motpos_x

	ip_addr = "tcp://10.0.143.160"
	zc = zclient(ip_addr)
	print "Starting ZClient..."
	fpgaver = zc.read(0x0C)
	#zc.fifo_reset()
	
	count=0
	for l in range(0,loops):
		for x in range(0,numframes_x): 
			for y in range(0,numframes_y): 
				count=count+1
				print "count: %d motpos_y: %f" % (count,motpos_y)
				caput("6bma1:m18",motpos_y) # move Y
				#time.sleep(14.0)
				totallen = zc.get_frame(filename,count,framelen) # take data
				while caget("6bma1:m18.DMOV") == 0: 
					time.sleep(0.2)
				motpos_y = motpos_y + motorstep_y;
			  
			# go to original Y position
			caput("6bma1:m18",motpos_y0) 
			while caget("6bma1:m18.DMOV") == 0: 
				 time.sleep(0.2)
			motpos_y = motpos_y0
			print "go to original Y position: %f" % (motpos_y0)
			
			# move X
			motpos_x = motpos_x + motorstep_x;
			print "Moving X Motor to %6.3f mm" % (motpos_x)
			caput("6bma1:m19",motpos_x) 
			while caget("6bma1:m19.DMOV") == 0: 
				 time.sleep(0.2)
			print ("X Move Complete");
			print 

		# go to original X position
		caput("6bma1:m19",motpos_x0) # trans
		while caget("6bma1:m19.DMOV") == 0: 
			time.sleep(0.2)
		motpos_x = motpos_x0
		print "go to original X position: %f" % (motpos_x0)
		caput("6bmpreci:m1",90) # move precr to 90
	print "count: %d" % (count)

