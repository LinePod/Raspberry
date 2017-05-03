from bluetooth import *
import sys, os, time, threading
from silhouette import *
from Queue import Queue
import time
import usb.core
import usb.util
import struct
import time
LOGFILE_PATH = "logfile"
TEST = True
if len(sys.argv) == 2 and sys.argv[1] == '-t':
    TEST = True
#eventRegistered1 = 0
#eventRegistered2 = 0
#lastSent = time.time()

def restart():
    log("Restarting...")
    os.system("sudo /home/pi/linespace/restart.sh")

def log(content):
    print(content)
    with open(LOGFILE_PATH,"a+") as output_file:
        output_file.write(time.strftime('%m.%d.%y %H:%M:%S:')+ ' {0}\n'.format(content))
        output_file.close()

def saveSVGToFile(svgString, uuid):
    svgFile = open("svgs/" + uuid + ".svg")
    svgFile.write(svgString)
    svgFile.close()

class mySilhouette (Silhouette):
    def __init__(self):
        super(mySilhouette, self).__init__()

    def config(self):
        if not TEST:
            try:
                self.connect()
                self.init()
                self.write("!3\x03")
            except:
                log("Cannot connect to plotter")
                time.sleep(1)
                restart()

    def write(self, command):
        if not TEST:
            log("Sending to Plotter: " + command)
            super(mySilhouette, self).write(command)

silhouette = mySilhouette()
silhouette.config()

class BtCommunication (object):

    def __init__(self, uuid, name):
        self.server_sock = BluetoothSocket( RFCOMM )
        self.uuid = uuid
        self.config()
        self.name = name
        self.connected = False

        self.establishConnectionThread = EstablishConnectionThread(self)
        self.establishConnectionThread.start()

    def config(self):
        os.system("/home/pi/linespace/establishConnection.sh")
        self.server_sock.bind(("",PORT_ANY))
        self.server_sock.listen(1)
        self.port = self.server_sock.getsockname()[1]

        advertise_service(self.server_sock, "BP_AMAZING",
                service_id = self.uuid,
                service_classes = [ self.uuid, SERIAL_PORT_CLASS ],
                profiles = [ SERIAL_PORT_PROFILE ],)


class EstablishConnectionThread(threading.Thread):

    def __init__(self, btObj):
        self.btObj = btObj
        super(EstablishConnectionThread, self).__init__()

    def run(self):
        log("Waiting for connection on RFCOMM channel " + str(self.btObj.port))
        self.btObj.client_sock, self.btObj.client_info = self.btObj.server_sock.accept()
        log("Accepted connection from " + str(self.btObj.client_info))
        self.btObj.connected = True
        log("###############################")
        log(self.btObj.name + " is connected")
        log("###############################")


class PrintingThread(threading.Thread):

    def __init__(self):
        super(PrintingThread, self).__init__()

    def printGPGLFromUUID(uuid, speed=2):
        filepath = "gpgls/" + uuid + ".gpgl"

        s = Silhouette()
        s.connect()
        s.ep_out.write('!' + speed + '\x03H\x03')

        data = open(filepath, 'r').read()

        for i in range(0, len(data), 1024):
            s.ep_out.write(data[i:i+1024])
            time.sleep(.5)
            while not s.ready:
                time.sleep(.5)

        s.ep_out.write('M0,-2000\x03')

    def run(self):
        while True:
            if(len(printingQueue) != 0):
                uuid = printingQueue.get()
                printGPGLFromUUID(uuid)
            time.sleep(.5)

class ListenThread (threading.Thread):

    def __init__(self, btObj):
        self.btObj = btObj
        super(ListenThread, self).__init__()

    def run(self):

        buffer = ""
        curSvg = ""
        try:
            while True:
                if(self.btObj.connected == True):
                    data = self.btObj.client_sock.recv(1024)
                    if len(data) == 0: break
                    log("received " + str(data))

                    if data[0] == '0' and appCommunication.connected == True:
                        #if tracking data received
                        trackingQueue.put(data[2:])
                        continue

                    if data[0] == 's':
                        #if svg data received
                        curSvg += data[1:]
                        if '\x05' in data:
                            sendToPlotter(curSvg)
                            curSvg = ""
                        continue

                    buffer += data

                    if(data[-1] != '\x04'):
                        silhouette.write(buffer)
                        log("logging " + str(len(buffer)))
                        buffer = ''

                time.sleep(0.01)

        except IOError:
            pass

        log("disconnected")

        self.btObj.client_sock.close()
        self.btObj.server_sock.close()
        return

"""class SendThread(threading.Thread):

    def __init__(self, btObj):
        self.btObj = btObj
        super(SendThread, self).__init__()


    def run(self):

        toSend = ''

        while True:
            startTime = time.time()
            if(self.btObj.connected == True):

                if(toSend == ''):
                     toSend = trackingQueue.get()
                self.btObj.client_sock.send(toSend)
                log("Send: " + toSend)
                toSend = ''

                global lastSent
                global eventRegistered1
                global eventRegistered2
                lastSent = time.time()
                eventRegistered1 = 0
                eventRegistered2 = 0
            time.sleep(0.01)
            log(time.time() -startTime)"""

class TrackingThread(threading.Thread):

    lastEvent1 = -1
    lastEvent2 = -1

    eventTypeDict = {
            0: 'MOVE',
            1: 'DOWN',
            2: 'UP',
            -1: ''}

    def __init__(self,btObj):
        self.btObj=btObj
        super(TrackingThread,self).__init__()
        self.dev=usb.core.find(idVendor=0x1536, idProduct=0x101)
        self.interface=0
        #self.endpoint=self.dev[0](0,0)[0]
        print self.dev
        if self.dev.is_kernel_driver_active(self.interface) is True:
            self.dev.detach_kernel_driver(self.interface)
            usb.util.claim_interface(self.dev,self.interface)



    def getEventType(self, newEvent1,newEvent2):
        event1=-1
        event2=-1

        diff1=newEvent1-self.lastEvent1
        diff2=newEvent2-self.lastEvent2

        if self.lastEvent1==-1:
            event1=1
        elif diff1==-1:
            event1=2
        elif diff1>=3:
            event1=1
        elif diff1==0:
            event1=0

        if diff2==-1:
            event2=2
        elif diff2>=3:
            event2=1
        elif diff2==0:
            event2=0

        self.lastEvent1=newEvent1
        self.lastEvent2=newEvent2
        print self.eventTypeDict[event1]+":"+str(diff1)  + "  \t" + self.eventTypeDict[event2] +":"+str(diff2)
        return [event1,event2]

    def run(self):
        count=0
        while True:
            try:
                if (self.btObj.connected==True):
                    data=self.dev.read(0x81,0x40)
                    finger_left_x1=data[5]
                    finger_left_x2=data[6]
                    finger_left_y1=data[7]
                    finger_left_y2=data[8]
                    x_left=finger_left_x2*256+finger_left_x1
                    y_left=finger_left_y2*256+finger_left_y1

                    finger_right_x1=data[14]
                    finger_right_x2=data[15]
                    finger_right_y1=data[16]
                    finger_right_y2=data[17]
                    x_right=finger_right_x2*256+finger_right_x1
                    y_right=finger_right_y2*256+finger_right_y1

                    eventTypes = self.getEventType(data[4],data[13])

                    bytesToSend = struct.pack(">6i",x_left,y_left,x_right,y_right,eventTypes[0],eventTypes[1])

                    self.btObj.client_sock.send(bytesToSend)
                    log("Sent bytes")

                    print str(x_left) + "  " + str(y_left)
                    """if count >5:
                            count=0
                            #trackingQueue.put_nowait(str(x_left)+","+str(y_left)+","+str(x_right)+","+str(y_right))
                            trackingQueue.put_nowait(bytesToSend)"""

            except usb.core.USBError as e:
                data = None
                continue
                count+=1

uuidDict = {'app' : '00001101-0000-1000-8000-00805F9B34FB',
            'tracking' : '00001101-9999-1000-8000-00805F9B34FB'}

trackingQueue = Queue()
appCommunication = BtCommunication(uuidDict['app'], 'app')
trackingCommunication = BtCommunication(uuidDict['tracking'], 'tracking')

appListenThread = ListenThread(appCommunication)
#trackingListenThread = ListenThread(trackingCommunication)
log("starting")
appListenThread.start()
#appSendThread = SendThread(appCommunication)
#appSendThread.start()
trackingGatherThread= TrackingThread(appCommunication)
trackingGatherThread.start()
#trackingListenThread.start()

trackingGatherThread.join()
appListenThread.join()
appSendThread.join()
#trackingListenThread.join()
