import os
import os.path
import struct
import subprocess
import sys
import time
import threading
import usb.core
import usb.util
from silhouette import *
from bluetooth import *
from Queue import Queue

LOGFILE_PATH = "logfile"
APP_UUID = '00001101-0000-1000-8000-00805F9B34FB'
TEST = False

if len(sys.argv) == 2 and sys.argv[1] == '-t':
    TEST = True

def restart():
    log("Restarting...")
    os.system("~/linespace/bluetooth-server/restart.sh")

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
        os.system("./establishConnection.sh")
        self.server_sock.bind(("",PORT_ANY))
        self.server_sock.listen(1)
        self.port = self.server_sock.getsockname()[1]

        advertise_service(self.server_sock, "BP_AMAZING",
                service_id = self.uuid,
                service_classes = [ self.uuid, SERIAL_PORT_CLASS ],
                profiles = [ SERIAL_PORT_PROFILE ],)

class PrintingThread(threading.Thread):

    def __init__(self, sendingQueue, printingQueue, isPrinting):
        self.sendingQueue = sendingQueue
        self.printingQueue = printingQueue
        super(PrintingThread, self).__init__()

    def printGPGL(self, data, speed=2):

        #Set speed and home
        silhouette.write('!' + str(speed) + '\x03H\x03')

        for i in range(0, len(data), 1024):
            silhouette.write(data[i:i+1024])
            time.sleep(.5)
            while not silhouette.ready:
                time.sleep(.5)

        #Paper out

        silhouette.write('M0,-10000\x03')

    def saveSVGToFile(self, svgString, uuid):
        svgFile = open("svg/" + uuid + ".svg", "w")
        svgFile.write(svgString)
        svgFile.close()

    def convertSVG(self, uuid):
        svgPath = "svg/" + uuid + ".svg"
        converter_path = os.path.expanduser('~/linespace/svg-simplifier/build/svg_converter')
        out = subprocess.check_output([converter_path, svgPath])
        print out
        return out

    def run(self):
        while True:
            [uuid, svgString] = self.printingQueue.get()
            self.saveSVGToFile(svgString, uuid)
            gpglData = self.convertSVG(uuid)
            isPrinting = True
            status = self.printGPGL(gpglData)
            isPrinting = False
            bytesToSend = struct.pack(">2i36c",1,0,*uuid)
            log("sending bytes: " + str(bytesToSend.encode("utf-8")))
            self.sendingQueue.put(bytesToSend)
            time.sleep(.5)
            log("alive")

class ListenThread (threading.Thread):

    def __init__(self, btObj, printingQueue):
        self.btObj = btObj
        self.printingQueue = printingQueue
        super(ListenThread, self).__init__()

    def run(self):

        try:
            while True:
                svgData = ''
                uuid = self.btObj.client_sock.recv(36)
                if(len(uuid) == 0) : break
                numBytes = struct.unpack(">I", self.btObj.client_sock.recv(4))[0]
                while(len(svgData) < numBytes):
                    svgData += self.btObj.client_sock.recv(numBytes - len(svgData))

                self.printingQueue.put([uuid, svgData])

                log("received SVG with uuid: " + uuid + " size: " + str(numBytes))
                time.sleep(0.01)

        except IOError:
            pass

        log("disconnected")

        self.btObj.client_sock.close()
        self.btObj.server_sock.close()
        return

class SendThread(threading.Thread):

    def __init__(self, btObj, sendingQueue):
        self.btObj = btObj
        self.sendingQueue = sendingQueue
        super(SendThread, self).__init__()

    def run(self):

        while True:
            toSend = self.sendingQueue.get()
            self.btObj.client_sock.send(toSend)
            log("Send: " + str(toSend))

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

    def __init__(self, btObj, sendingQueue, isPrinting):
        self.btObj=btObj
        self.sendingQueue = sendingQueue
        super(TrackingThread,self).__init__()
        self.dev=usb.core.find(idVendor=0x1536, idProduct=0x101)
        self.interface=0
        #self.endpoint=self.dev[0](0,0)[0]
        print self.dev
        if self.dev.is_kernel_driver_active(self.interface) is True:
            self.dev.detach_kernel_driver(self.interface)

            usb.util.claim_interface(self.dev,self.interface)

    def unclaimDevice(self):
        log("releasing device")
        usb.util.release_interface(self.dev, self.interface)
        self.dev.reset()
        self.dev.attach_kernel_driver(self.interface)

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

        count = 0
        while True:
            if isPrinting:
                time.sleep(1)
                continue
            if shutdown:
                self.unclaimDevice()
                return
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

                bytesToSend = struct.pack(">7i",0,x_left,y_left,x_right,y_right,eventTypes[0],eventTypes[1])

                if (eventTypes[0] == 1 or eventTypes[0] == 2) or (eventTypes[1] == 1 or eventTypes[1] == 2):
                    self.sendingQueue.put(bytesToSend)
                    log("tracking send ")
                else:
                    count +=1

                if count > 10:
                    count = 0
                    self.sendingQueue.put(bytesToSend)
                    log("tracking send ")

            except usb.core.USBError as e:
                data = None
                continue
                count+=1

try:
    printingQueue = Queue()
    sendingQueue = Queue()

    isPrinting = False
    shutdown = False

    appCommunication = BtCommunication(APP_UUID)

    listenThread = ListenThread(appCommunication, printingQueue)
    sendThread = SendThread(appCommunication, sendingQueue)
    trackingThread = TrackingThread(appCommunication, sendingQueue, isPrinting)
    printingThread = PrintingThread(sendingQueue, printingQueue, isPrinting)

    listenThread.daemon = True
    sendThread.daemon = True
    trackingThread.daemon = True
    printingThread.daemon = True

    log("starting threads")

    listenThread.start()
    sendThread.start()
    trackingThread.start()
    printingThread.start()
    while True: time.sleep(100)

except (KeyboardInterrupt, SystemExit):
    log("Will exit due to Ctrl+c")
    shutdown = True
    try:
        trackingThread.join()
    except:
        pass
    os._exit(0)