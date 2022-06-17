from xml.dom.minidom import Attr
import serial
from threading import Thread
import queue
import time
import signal
from icecream import ic
from PyQt5 import QtWidgets, QtCore
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
import sys  # We need sys so that we can pass argv to QApplication
import os
import csv
import copy


SAMPLE_HOLD = 300 #change for the needs of the graph

class AccelDataGrabber:

    def __init__(self, portName):
        time.sleep(1)
        baudrate = 2000000
        self.ser = serial.Serial(portName,baudrate,timeout=1)
        self.ser.setDTR(False)
        time.sleep(1)
        self.ser.flushInput()
        self.ser.setDTR(True)
        time.sleep(2)
        self.ser.flushInput()
        self.q = queue.Queue()
        self.exit = False
        self.data={"A": [0,0,0,0], "G":[0,0,0,0], "T": time.time()}
        serial_worker = Thread(target=self.serial_receiver)
        serial_worker.start()
        #writer_worker = Thread(target=self.csv_writer)
        #writer_worker.start()


    def handler(self, signal, frame):
        global THREADS
        print ("Ctrl-C.... Exiting")
        self.exit = True

    def decode_accel(self, value):
        x = (value.strip().split(',')[1:])
        self.data['A'] = [float(val) for val in x]
        self.data['T'] = time.time()
        self.q.put(copy.copy(self.data))

    def decode_gyro(self, value):
        x = (value.strip().split(',')[1:])
        self.data['G'] = [float(val) for val in x]
        self.data['T'] = time.time()
        self.q.put(copy.copy(self.data))

    def serial_receiver(self):
        ic("Started main thread")
        last_message = time.time()
        index = 0
        while 1:
            if self.exit:
                return
            try:
                value = self.ser.readline().decode()
            except (AttributeError, UnicodeDecodeError) as e:
                continue
            # if value[0] == 'G':
            #     index += 1
            #     try:
            #         self.decode_gyro(value)
            #     except:
            #         pass

            if value[0] == 'A':
                index += 1
                try:
                    self.decode_accel(value)
                except:
                    pass

            if index == 60:
                print("Accel Stream Rate (recvied in python) {:.2f}Hz".format( 1.0 / ((time.time() - last_message)/60.0)))
                index = 0
                last_message = time.time()    
    
    def csv_writer(self):
        with open('data.csv', 'w', newline='') as csvfile: 
            spamwriter = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
            spamwriter.writerow(['AX', 'AY', 'AZ', 'AT', 'GX', 'GY', 'GZ', 'GT', 'TS'])
            while 1:
                if self.exit:
                    break
                if self.q.empty():
                    time.sleep(0.1)
                    continue
                out = self.q.get()
                try:
                    spamwriter.writerow([
                        out['A'][0],
                        out['A'][1],
                        out['A'][2],
                        out['A'][3],
                        out['G'][0],
                        out['G'][1],
                        out['G'][2],
                        out['G'][3],
                        out['T']
                    ])
                except (IndexError):
                    pass

        print("Finsihed")

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.graphWidget = pg.PlotWidget()
        self.graphWidget.setToolTip("me")
        self.setCentralWidget(self.graphWidget)

        self.x = list(range(SAMPLE_HOLD))  # 100 time points
        self.y = [[0 for _ in range(SAMPLE_HOLD)], [0 for _ in range(SAMPLE_HOLD)],[0 for _ in range(SAMPLE_HOLD)]]  # 100 data points
        print(type(self.y))
        time.sleep(0.1)

        self.graphWidget.setBackground('black')

        self.plots = [None, None, None]
        for i in range(3):
            self.plots[i] = self.graphWidget.plot(self.x, self.y[i], pen=(i,3))

        self.timer = QtCore.QTimer()
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update_plot_data)
        self.timer.start()
        self.data_source = None


    def load_data_source(self, data_source):
        self.data_source = data_source


    def update_plot_data(self):

        self.x = self.x[1:]  # Remove the first y element.
        self.x.append(self.x[-1] + 1)  # Add a new value 1 higher than the last.

        
        for i in range(3):
            self.y[i] = self.y[i][1:]  # Remove the first 
            self.y[i].append(self.data_source.data['A'][i])  # Add a new random value.

        for i in range(3):
            self.plots[i].setData(self.x, self.y[i])


if __name__== '__main__':

    x = AccelDataGrabber('/dev/ttyUSB0')
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.load_data_source(x)
    signal.signal(signal.SIGINT, x.handler)
    w.show()
    sys.exit(app.exec_())


        
