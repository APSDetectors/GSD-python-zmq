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
        #fd = open(filename+str(curframe).rjust(3,'0')+'.dat','wb')
        fd = open(filename+str(curframe).rjust(4,'0')+'.dat','wb')
		
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

	if (len(sys.argv) != 7):
	  print "Usage ./maia_zclient2 numframes_x  numframes_y eventsperframe motorstepsize_x(mm)  motorstepsize_y(mm) filename"
	  sys.exit();

	numframes_x = int(sys.argv[1])
	numframes_y = int(sys.argv[2])
	framelen  = int(sys.argv[3])
	motorstep_x = float(sys.argv[4]) 
	motorstep_y= float(sys.argv[5])
	filename  = sys.argv[6]


	print "Starting Run...   NumFrame: %d    EventsPerFrame:  %d     MotorStepSize-x:   %d" % (numframes_x,framelen, motorstep_x) 
	vertmotpos = caget("6bma1:m17")  #scale to mm
	print "Inital Motor Position: %6.3f" % (vertmotpos) 
	rotpos = caget("6bma1:m22")

	# original positions
	vertmotpos0 = vertmotpos
	rotpos0 = rotpos

	ip_addr = "tcp://172.16.0.214"

	zc = zclient(ip_addr)
	print "Starting ZClient..."
	fpgaver = zc.read(0x0C)
	print "FPGA ver = %d" % fpgaver;
    
    #zc.set_framelen(framelen)
    #zc.fifo_reset()
	count=124
	for y in range(0,numframes_y): 

		for x in range(0,numframes_x): 
		  count=count+1
		  totallen = zc.get_frame(filename,count,framelen)
		  print "%d" % (count)
		  caput("6bma1:m17",vertmotpos) # translate
		  print vertmotpos
		  while caget("6bma1:m17.DMOV") == 0: 
			 time.sleep(0.1)
		  vertmotpos = vertmotpos + motorstep_x;
		  
		 # go to original translation position
		caput("6bma1:m17",vertmotpos0) # translation  
		vertmotpos = vertmotpos0
		
		while caget("6bma1:m17.DMOV") == 0: 
			 time.sleep(0.1)
			 
		print "Events in Frame  = %d" % totallen
		rotpos = rotpos + motorstep_y;
		print rotpos
		print "Moving Motor to %6.3f mm" % (rotpos)
		caput("6bma1:m22",rotpos)	
		while caget("6bma1:m22.DMOV") == 0: 		
			 time.sleep(0.1)
		print ("Move Complete");
		print 

	# go to original rotation position
	caput("6bma1:m22",rotpos0) # rotation         
	while caget("6bma1:m22.DMOV") == 0: 
		time.sleep(0.1)


