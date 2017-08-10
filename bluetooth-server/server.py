#!/usr/bin/env python
import logging
import os
import os.path
import select
import socket
import struct
import subprocess
import sys
import time
import threading
import usb.core
import usb.util
from silhouette import *
from bluetooth import *
import Queue

APP_UUID = '00001101-0000-1000-8000-00805F9B34FB'
TEST = False

if len(sys.argv) == 2 and sys.argv[1] == '-t':
    TEST = True

class MySilhouette (Silhouette):
    def __init__(self, testing):
        super(MySilhouette, self).__init__()
        if not testing:
            self.connect()
            self.init()

    def write(self, command):
        if not TEST:
            logging.debug("Sending to Plotter: %s", repr(command))
            super(MySilhouette, self).write(command)
        else:
            logging.debug("Would send to plotter: %s", repr(command))

class BtCommunication (object):
    def __init__(self, uuid):
        self.server_sock = BluetoothSocket(RFCOMM)
        self.uuid = uuid
        self.config()
        self.establishConnection()

    def establishConnection(self):
        logging.info("Waiting for connection on RFCOMM channel %s", self.port)
        self.client_sock, self.client_info = self.server_sock.accept()
        logging.info("Accepted connection from %s", self.client_info)

    def config(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        subprocess.check_call(
                [os.path.join(script_dir, 'establishConnection.sh')])
        self.server_sock.bind(("", PORT_ANY))
        self.server_sock.listen(1)
        self.port = self.server_sock.getsockname()[1]

        advertise_service(self.server_sock, "BP_AMAZING",
                service_id = self.uuid,
                service_classes = [ self.uuid, SERIAL_PORT_CLASS ],
                profiles = [ SERIAL_PORT_PROFILE ],)

class TcpCommunication(object):
    def __init__(self, port):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.bind(('0.0.0.0', port))
        self.server_sock.listen(1)
        logging.info('Waiting for TCP connections on port %d', port)
        self.client_sock, client_addr = self.server_sock.accept()
        logging.info('Accepted connection from %s', client_addr)

class PrintingThread(threading.Thread):
    def __init__(self, sendingQueue, printingQueue, shutdown):
        super(PrintingThread, self).__init__(name='Printing thread')
        self.daemon = True
        self.sendingQueue = sendingQueue
        self.printingQueue = printingQueue
        self.shutdown = shutdown

    def printGPGL(self, data, speed=1):
        #Set speed and home
        silhouette.write('!' + str(speed) + '\x03H\x03')

        for i in range(0, len(data), 1024):
            silhouette.write(data[i:i + 1024])
            time.sleep(.5)
            while not silhouette.ready:
                time.sleep(.5)

        #Paper out
        silhouette.write('M0,-10000\x03')

    def saveSVGToFile(self, svgString, uuid):
        with open("svg/" + uuid + ".svg", "w") as svgFile:
            svgFile.write(svgString)

    def convertSVG(self, uuid):
        svgPath = "svg/" + uuid + ".svg"
        converter_path = os.path.expanduser('~/linepod/svg-converter/build/svg_converter')
        out = subprocess.check_output([converter_path, svgPath])
        return out

    def run(self):
        try:
            while not self.shutdown.is_set():
                try:
                    [uuid, svgString] = self.printingQueue.get(True, .5)
                except Queue.Empty:
                    continue
                self.saveSVGToFile(svgString, uuid)
                gpglData = self.convertSVG(uuid)
                isPrinting = True
                status = self.printGPGL(gpglData)
                isPrinting = False
                bytesToSend = struct.pack(">2i36c",1,0,*uuid)
                self.sendingQueue.put(bytesToSend)
                time.sleep(.5)
        except:
            logging.exception("Error while printing")
            self.shutdown.set()

class ListenThread (threading.Thread):
    def __init__(self, btObj, printingQueue, shutdown):
        super(ListenThread, self).__init__(name='Listen thread')
        self.daemon = True
        self.btObj = btObj
        self.printingQueue = printingQueue
        self.shutdown = shutdown

    def run(self):
        try:
            while not self.shutdown.is_set():
                lists = select.select([self.btObj.client_sock], [], [], .5)
                if not lists[0]:
                    continue
                uuid = self.btObj.client_sock.recv(36)
                if(len(uuid) == 0):
                    break
                numBytes = struct.unpack(">I", self.btObj.client_sock.recv(4))[0]
                svgData = ''
                while(len(svgData) < numBytes):
                    svgData += self.btObj.client_sock.recv(numBytes - len(svgData))

                self.printingQueue.put([uuid, svgData])

                logging.info("Received SVG with uuid: %s, size %d", uuid, numBytes)
                time.sleep(0.01)
        except:
            logging.exception("Bluetooth error")
            self.shutdown.set()
        finally:
            self.btObj.client_sock.close()
            self.btObj.server_sock.close()

class SendThread(threading.Thread):
    def __init__(self, btObj, sendingQueue, shutdown):
        super(SendThread, self).__init__(name='Send thread')
        self.daemon = True
        self.btObj = btObj
        self.sendingQueue = sendingQueue
        self.shutdown = shutdown

    def run(self):
        try:
            while not self.shutdown.is_set():
                try:
                    toSend = self.sendingQueue.get(True, .5)
                except Queue.Empty:
                    continue
                self.btObj.client_sock.send(toSend)
                logging.debug("Sending %s", toSend)
        except:
            logging.exception("Error while sending to bluetooth connection")
            self.shutdown.set()

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
        -1: ''
    }

    def __init__(self, btObj, sendingQueue, shutdown):
        super(TrackingThread, self).__init__(name='Tracking thread')
        self.daemon = True
        self.btObj = btObj
        self.sendingQueue = sendingQueue
        self.shutdown = shutdown

    def unclaimDevice(self, dev, interface):
        logging.info("Releasing airbar usb device")
        usb.util.release_interface(dev, interface)
        dev.reset()
        dev.attach_kernel_driver(interface)

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
        return [event1,event2]

    def run(self):
        try:
            dev = usb.core.find(idVendor=0x1536, idProduct=0x101)
            interface = 0
            if dev.is_kernel_driver_active(interface) is True:
                dev.detach_kernel_driver(interface)
                usb.util.claim_interface(dev, interface)

            count = 0

            while not self.shutdown.is_set():
                if isPrinting:
                    time.sleep(1)
                    continue
                data = dev.read(0x81, 0x40)
                finger_left_x1 = data[5]
                finger_left_x2 = data[6]
                finger_left_y1 = data[7]
                finger_left_y2 = data[8]
                x_left = finger_left_x2 * 256 + finger_left_x1
                y_left = finger_left_y2 * 256 + finger_left_y1

                finger_right_x1 = data[14]
                finger_right_x2 = data[15]
                finger_right_y1 = data[16]
                finger_right_y2 = data[17]
                x_right = finger_right_x2 * 256 + finger_right_x1
                y_right = finger_right_y2 * 256 + finger_right_y1

                eventTypes = self.getEventType(data[4],data[13])

                bytesToSend = struct.pack(">7i", 0, x_left, y_left, x_right, y_right, eventTypes[0], eventTypes[1])

                if (eventTypes[0] == 1 or eventTypes[0] == 2) or (eventTypes[1] == 1 or eventTypes[1] == 2):
                    self.sendingQueue.put(bytesToSend)
                    logging.debug("Sending tracking info")
                else:
                    count += 1

                if count > 10:
                    count = 0
                    self.sendingQueue.put(bytesToSend)
                    logging.debug("Sending tracking info")

        except:
            logging.exception("USB error")
            self.shutdown.set()
        finally:
            self.unclaimDevice(dev, interface)

logging.basicConfig(
        level=logging.DEBUG,
        format='[%(levelname)s] %(threadName)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')

try:
    silhouette = MySilhouette(TEST)
except:
    logging.exception('Cannot connect to plotter')
    sys.exit(1)

printingQueue = Queue.Queue()
sendingQueue = Queue.Queue()
shutdown = threading.Event()

isPrinting = False

try:
    #appCommunication = BtCommunication(APP_UUID)
    appCommunication = TcpCommunication(3000)

    threads = (ListenThread(appCommunication, printingQueue, shutdown),
               SendThread(appCommunication, sendingQueue, shutdown),
               #TrackingThread(appCommunication, sendingQueue, shutdown),
               PrintingThread(sendingQueue, printingQueue, shutdown))
    logging.info('starting threads')

    for t in threads:
        t.start()

    logging.info('threads started')

    # Give python a chance to throw a KeyboardInterrupt
    while True:
        shutdown.wait(1)
except KeyboardInterrupt:
    logging.info('Exiting due to ctrl-c')
except:
    logging.exception('Caught error in main thread')
finally:
    logging.info('Trying to exit threads gracefully...')
    shutdown.set()
    for t in threads:
        t.join(1)
    for t in threads:
        if t.is_alive():
            logging.warn(t.name + ' did not exit gracefully')
    logging.info('Exiting')
