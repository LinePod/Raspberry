from bluetooth import *
import sys, os, time, threading
import subprocess
from silhouette import *
from Queue import Queue
import time
import usb.core
import usb.util
import struct
import time

LOGFILE_PATH = "logfile"
APP_UUID = '00001101-0000-1000-8000-00805F9B34FB'
TEST = True

if len(sys.argv) == 2 and sys.argv[1] == '-t':
    TEST = True

def restart():
    log("Restarting...")    
    os.system("sudo /home/pi/linespace/restart.sh")

def log(content):
    print(content)
    with open(LOGFILE_PATH,"a+") as output_file:
        output_file.write(time.strftime('%m.%d.%y %H:%M:%S:')+ ' {0}\n'.format(content))
        output_file.close()

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
        else:
            log("Would send to plotter: " + command)

silhouette = mySilhouette()
silhouette.config()

class BtCommunication (object):

    def __init__(self, uuid):
        self.server_sock = BluetoothSocket(RFCOMM)
        self.uuid = uuid
        self.config()
        self.establishConnection()

    def establishConnection(self):
        log("Waiting for connection on RFCOMM channel " + str(self.port))
        self.client_sock, self.client_info = self.server_sock.accept()
        log("Accepted connection from " + str(self.client_info))
        log("###############################")
        log("App is connected")
        log("###############################")

    def config(self):
        os.system("sudo ./establishConnection.sh")
        self.server_sock.bind(("",PORT_ANY))
        self.server_sock.listen(1)
        self.port = self.server_sock.getsockname()[1]

        advertise_service(self.server_sock, "BP_AMAZING",
                service_id = self.uuid,
                service_classes = [ self.uuid, SERIAL_PORT_CLASS ],
                profiles = [ SERIAL_PORT_PROFILE ],)

class PrintingThread(threading.Thread):

    def __init__(self):
        super(PrintingThread, self).__init__()

    def printGPGL(self, data, speed=2):
        
        #Set speed and home
        silhouette.ep_out.write('!' + speed + '\x03H\x03')

        for i in range(0, len(data), 1024):
            silhouette.ep_out.write(data[i:i+1024])
            time.sleep(.5)
            while not silhouette.ready:
                time.sleep(.5)

        #Paper out
        silhouette.ep_out.write('M0,-2000\x03')

    def saveSVGToFile(self, svgString, uuid):
        svgFile = open("svg/" + uuid + ".svg", "w")
        svgFile.write(svgString)
        svgFile.close()

    def convertSVG(self, uuid):
        svgPath = "svg/" + uuid + ".svg"
        out = subprocess.check_output(['linespace-svg-simplifier/build/svg_converter',svgPath])
        print out
        return out

    def run(self):
        while True:
            [uuid, svgString] = printingQueue.get()
            self.saveSVGToFile(svgString, uuid)
            gpglData = self.convertSVG(uuid)
            self.printGPGL(gpglData)
            time.sleep(.5)

class ListenThread (threading.Thread):

    def __init__(self, btObj):
        self.btObj = btObj
        super(ListenThread, self).__init__()

    def run(self):

        try:
            while True:
                uuid = self.btObj.client_sock.recv(36)
                if(len(uuid) == 0) : break
                numBytes = struct.unpack(">I", self.btObj.client_sock.recv(4))[0]
                svgData = self.btObj.client_sock.recv(numBytes)
                printingQueue.put([uuid, svgData])
                
                log("received SVG with uuid: " + uuid + " size: " + str(numBytes))
                time.sleep(0.01)

        except IOError:
            pass

        log("disconnected")

        self.btObj.client_sock.close()
        self.btObj.server_sock.close()
        return

class SendThread(threading.Thread):

    def __init__(self, btObj):
        self.btObj = btObj
        super(SendThread, self).__init__()

    def run(self):

        while True:
            toSend = sendingQueue.get()
            self.btObj.client_sock.send(toSend)
            log("Send: " + toSend)

class TrackingThread(threading.Thread):
    '''
    Receive tracking Data and put into sendingQueue
    '''

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

                if (eventTypes[0] == 1 or eventTypes[0] == 2) or (eventTypes[1] == 1 or eventTypes[1] == 2):
                    sendingQueue.put(bytesToSend)
                else:
                    count +=1

                if count > 10:
                    count = 0
                    sendingQueue.put(bytesToSend)

            except usb.core.USBError as e:
                data = None
                continue
                count+=1


printingQueue = Queue()
sendingQueue = Queue()

appCommunication = BtCommunication(APP_UUID)

listenThread = ListenThread(appCommunication)
sendThread = SendThread(appCommunication)
trackingThread = TrackingThread(appCommunication)
printingThread = PrintingThread()

log("starting")
listenThread.start()
sendThread.start()
trackingThread.start()
printingThread.start()

trackingThread.join()
listenThread.join()
sendThread.join()
printingThread.join()
