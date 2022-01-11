'''
author: Nhan <anhnhancao@gmail.com>
brief: GUI for video streaming, car controller and model running
'''
import os
import cv2
import sys
import termios
import numpy as np
import tty
import time
import threading
# import multiprocessing as mp
from threading import Lock
import queue
from PyQt5 import Qt
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import  QWidget, QLabel, QApplication, QMessageBox
from PyQt5.QtCore import QThread, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWebEngineWidgets import QWebEnginePage, QWebEngineSettings, QWebEngineView
from Emojinator import emojinator_model
import cv2
import numpy as np
import serial
import json
from functools import partial


# A UI class for the main window
class CustomMainWindow(QMainWindow):

    img_changePixmap = pyqtSignal(QImage)
    contour_changePixmap = pyqtSignal(QImage)

    def __init__(self):
        super().__init__()

        self.button_exe_dic = {
        'wifi_event_exec'            : self.wifi_event_exec,    
        'scan_event_exec'            : self.scan_event_exec,    
        'video_streaming_event_exec' : self.video_streaming_event_exec,    
        'mode_control_event_exec'    : self.mode_control_event_exec,
        'enter_password_event_exec'  : self.enter_password_event_exec,    
        'car_control_event_exec'     : self.car_control_event_exec
        }

        self.button_event = {
            'wifi_event'            : 'wifi_event_exec',            
            'scan_event'            : 'scan_event_exec',            
            'video_streaming_event' : 'video_streaming_event_exec',    
            'mode_control_event'    : 'mode_control_event_exec',    
            'enter_password_event'  : 'enter_password_event_exec',
            'car_control_event'     : 'car_control_event_exec'
        }

        self.car_control_key = {
            'w':RF_CMD_CAR_CTRL_MOVE_FORWARD,
            's':RF_CMD_CAR_CTRL_MOVE_BACKWARD,
            'a':RF_CMD_CAR_CTRL_TURN_LEFT,
            'd':RF_CMD_CAR_CTRL_TURN_RIGHT,
            'r':RF_CMD_CAR_CTRL_ROTATE_LEFT,
            't':RF_CMD_CAR_CTRL_ROTATE_RIGHT,
            'f':RF_CMD_CAR_CTRL_BACK_LEFT,
            'g':RF_CMD_CAR_CTRL_BACK_RIGHT,
            'x':RF_CMD_CAR_CTRL_STOP
        }

        self.direction_key_signal = {
            'w':'direction/MOVE_FORWARD.png',
            's':'direction/MOVE_BACKWARD.png',
            'a':'direction/TURN_LEFT.png',
            'd':'direction/TURN_RIGHT.png',
            'r':'direction/ROTATE_LEFT.png',
            't':'direction/ROTATE_RIGHT.png',
            'f':'direction/BACK_LEFT.png',
            'g':'direction/BACK_RIGHT.png',
            'x':'direction/STOP.png'
        }

        self.model_mapping = {
            '5':0,
            '4':0,
            '6':0,
            '9':0,
            '11':0,
            '1':0,
            '2':0,
            '10':0,
            'stop':0
        }

        self.model_mapping_display = {
            RF_CMD_CAR_CTRL_MOVE_FORWARD :'direction/MOVE_FORWARD.png',
            RF_CMD_CAR_CTRL_MOVE_BACKWARD:'direction/MOVE_BACKWARD.png',
            RF_CMD_CAR_CTRL_TURN_LEFT    :'direction/TURN_LEFT.png',
            RF_CMD_CAR_CTRL_TURN_RIGHT   :'direction/TURN_RIGHT.png',
            RF_CMD_CAR_CTRL_ROTATE_LEFT  :'direction/ROTATE_LEFT.png',
            RF_CMD_CAR_CTRL_ROTATE_RIGHT :'direction/ROTATE_RIGHT.png',
            RF_CMD_CAR_CTRL_BACK_LEFT    :'direction/BACK_LEFT.png',
            RF_CMD_CAR_CTRL_BACK_RIGHT   :'direction/BACK_RIGHT.png',
            RF_CMD_CAR_CTRL_STOP         :'direction/STOP.png'
        }
        

        self.usb = usb_serial(USB_COM_PORT)
        self.button_connect_status = 'disconnect'
        self.video_streaming_status = 'stop'
        self.mode_control_event_status = 'Keyboard'
        self.model_obj = emojinator_model()
        self.is_button_executed_done = True

        self.wifi_select_ssid = {
            'IDX':b'',
            'SSID':b'',
            'Password':b'',
            'Local IP':''
        }

        self.wifi_get_log = {
            'SSID':'',
            'Password':'',
            'Local IP':''
        }

        self.wifi_scan_ssid = {
            'IDX':[],
            'SSID':[]
        }

        self.butto_queue = queue.PriorityQueue()
        self.butto_queue_idx = 0

        # self.car_control_queue = queue.PriorityQueue()
        # self.car_control_queue_idx = 0

        #  Load UI from UI configuration file
        loadUi('lvtnhk211.ui', self)
        self.setWindowTitle('Remote Car Control')
        # Set up central Widget for Auto layout
        self.setCentralWidget(self.horizontalLayoutWidget)

        # Connect the button to all neccessary events
        self.pushButton_2.setEnabled(True)
        self.pushButton_2.clicked.connect(self.wifi_event)

        self.pushButton.setEnabled(True)
        self.pushButton.clicked.connect(self.scan_event)

        self.pushButton_3.setEnabled(True)
        self.pushButton_3.clicked.connect(self.video_streaming_event)
        
        self.pushButton_4.setEnabled(True)
        self.pushButton_4.clicked.connect(self.mode_control_event)

        self.pushButton_5.setEnabled(True)
        self.pushButton_5.clicked.connect(self.enter_password_event)

        # Display to stop the car at the beginning
        direction_pixmap = QPixmap(self.direction_key_signal['x'])
        pixmap_show = direction_pixmap.scaled(200, 200, Qt.KeepAspectRatio)
        self.label_5.setPixmap(pixmap_show)

        self.comboBox.activated[str].connect(self.onActivated)                  
        self.comboText = None      
        self.car_control_cmd = None

        self.is_typed_pass = False    
        self.is_scanned_ssid = False       

        self.car_control_packet = b''                

        # self.webview = QWebEngineView()
        # self.webview
        self.page = QWebEnginePage()
        self.webview.setPage(self.page)
        self.webview.settings().setAttribute(
            QWebEngineSettings.FullScreenSupportEnabled, True
        )

        # Load file JSON here, at the beginning always set the url to None

        # if not os.path.exists('ip.json'):
        #     print('The log file does not exist')
        #     available_content = False
        # else:
        #     available_content = True
            
        # self.f = open("ip.json", "r+")

        # if available_content:
        #     data = json.load(self.f)
        #     self.wifi_get_log['SSID'] = data['ssid']
        #     self.wifi_get_log['Password'] = data['password']
        #     self.wifi_get_log['Local IP'] = data['ip']
        # else:
        #     # Need to load new configurations for this esp32 module
        #     pass
        
        # self.f.close()

        # Load the URL from JSON file
        self.f = open("ip.json", "r+")
        data = json.load(self.f)
        start_url = data['ip']
        if start_url == '':
            pass
            # Re-tart the system execution
            # os.execl(sys.executable, sys.executable, *sys.argv)
        self.f.close()

        self.webview.load(
            QUrl(start_url)
        )

        videoCapture = threading.Thread(name = 'VideoCapture', target = self.videoCaptureThread)
        modelRun = threading.Thread(name = 'ModelRun', target = self.modelRunThread)
        buttonHandle = threading.Thread(name = 'ButtonHandle', target = self.buttonHandleThread)
        keyboardControl = threading.Thread(name = 'KeyboardControl', target = self.keyboardControlThread)

        videoCapture.start()
        modelRun.start()
        buttonHandle.start()
        keyboardControl.start()

        # Start the QT5 core
        self.show()


    @pyqtSlot(QImage)
    def setImage(self, image):
        self.label.setPixmap(QPixmap.fromImage(image))


    @pyqtSlot(QImage)
    def setContours(self, image):
        self.label_2.setPixmap(QPixmap.fromImage(image))


    def videoCaptureThread(self):
        self.img_changePixmap.connect(self.setImage)
        self.contour_changePixmap.connect(self.setContours)

        while True:
            img, contour = self.model_obj.get_image_from_queue()
            # https://stackoverflow.com/a/55468544/6622587

            img_rgbImage = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            contour_rgbImage = cv2.cvtColor(contour, cv2.COLOR_BGR2RGB)

            img_h, img_w, img_ch = img_rgbImage.shape
            contour_h, contour_w, contour_ch = contour_rgbImage.shape

            img_bytesPerLine = img_ch * img_w
            contour_bytesPerLine = contour_ch * contour_w

            img_convertToQtFormat = QImage(img_rgbImage.data, img_w, img_h, img_bytesPerLine, QImage.Format_RGB888)
            contour_convertToQtFormat = QImage(contour_rgbImage.data, contour_w, contour_h, contour_bytesPerLine, QImage.Format_RGB888)

            img_p = img_convertToQtFormat.scaled(640, 480, Qt.KeepAspectRatio)
            contour_p = contour_convertToQtFormat.scaled(640, 480, Qt.KeepAspectRatio)

            # Update available imgae
            self.img_changePixmap.emit(img_p)
            self.contour_changePixmap.emit(contour_p)

            time.sleep(0.005)


    def modelRunThread(self):
        previous_control = None
        current_control = None

        self.model_obj.keras_predict(self.model_obj.model, np.zeros((50, 50, 1), dtype=np.uint8))
        self.model_obj.emoji_open()

        start_time = time.time()

        while True:
            # Get the prediction from ML model
            if (self.mode_control_event_status == 'Emoji') and (self.video_streaming_status == 'start'):
                run_model = True
            else:
                run_model = False

            result = self.model_obj.emoji_predict(run_model)

            if result != None:
                if result == 5:
                    self.model_mapping['5'] += 1
                elif result == 1:
                    self.model_mapping['1'] += 1
                elif result == 11:
                    self.model_mapping['11'] += 1
                elif result == 4:
                    self.model_mapping['4'] += 1
                elif result == 6:
                    self.model_mapping['6'] += 1
                else:
                    self.model_mapping['5'] += 1

            # Only Emoji control mode need the timeout mechanism
            if (self.mode_control_event_status == 'Emoji'):
                # Debouncing in 100ms if using Hand gesture model
                # to control the car
                duration = time.time() - start_time   

                # Check the timeoout condition
                if duration > 0.1:
                    # max_idx = max(self.model_mapping)
                    max_value = 0
                    max_idx = None
                    for i in self.model_mapping:
                        if self.model_mapping[i] >= max_value:
                            max_value = self.model_mapping[i]
                            max_idx = i

                    if max_value >= 5:
                        self.car_control_packet = b'\xAB\xBA\x01'

                        # Need to adjust this if/else to get the best performance
                        # emoji
                        if max_idx == '5':
                            self.car_control_packet += RF_CMD_CAR_CTRL_STOP
                        elif max_idx == '1':
                            self.car_control_packet += RF_CMD_CAR_CTRL_MOVE_FORWARD
                        elif max_idx == '11':
                            self.car_control_packet += RF_CMD_CAR_CTRL_MOVE_BACKWARD
                        elif max_idx == '4':
                            self.car_control_packet += RF_CMD_CAR_CTRL_ROTATE_LEFT
                        elif max_idx == '6':
                            self.car_control_packet += RF_CMD_CAR_CTRL_ROTATE_RIGHT
                        else:
                            self.car_control_packet += RF_CMD_CAR_CTRL_STOP

                        current_control = self.car_control_packet[3:4]

                        self.model_mapping = {
                            '5':0,
                            '4':0,
                            '6':0,
                            '9':0,
                            '11':0,
                            '1':0,
                            '2':0,
                            '10':0,
                            'stop':0
                        }

                        # Send data via USB
                        # Send data via Virtual com port
                        if current_control != previous_control:
                            # Show directon image for displaying the direction
                            direction_pixmap = QPixmap(self.model_mapping_display[current_control])
                            pixmap_show = direction_pixmap.scaled(200, 200, Qt.KeepAspectRatio)
                            self.label_5.setPixmap(pixmap_show)

                            self.car_control_send_cmd()

                        previous_control = current_control
                        start_time = time.time()

            time.sleep(0.005)


    def buttonHandleThread(self):
        # |-- Header 1 --|-- Header 2 --|-- payload length --|--- CMD ---|---- data ----|
        # |--- 1 byte ---|--- 1 byte ---|------ 1 byte ------|-- 1 byte--|-- n bytes ---|

        while True:
            while self.butto_queue.empty():
                time.sleep(0.01)

            # Bypass the Queue element ID
            button_evt = self.butto_queue.get()[1]
            # Select the button event
            print(button_evt)
            function2call = self.button_exe_dic[button_evt]
            status = function2call()

            # Reset the button executed flag
            if not self.is_button_executed_done:
                self.is_button_executed_done = True

    
    def keyboardControlThread(self):
        filedescriptors = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin)
        key = None
        previous_control = None
        current_control = None

        while True:
            # Get input from keyboard incase 
            # switching from using ML model 
            # to control the car tp using keyboard
            # key = sys.stdin.read(1)[0]

            key = self.lineEdit_2.text()
            if key != '':
                print('Receive key: ', key)
                self.lineEdit_2.setText("")

            if (key in self.car_control_key)  and (self.video_streaming_status == 'start'):
                current_control = self.car_control_key[key] 

                # To avoid changing mode when waiting for the next
                # character
                if (self.mode_control_event_status == 'Keyboard') and (current_control != previous_control):
                    self.car_control_packet = b'\xAB\xBA\x01'
                    self.car_control_packet += self.car_control_key[key]

                    # Show directon image for displaying the direction
                    direction_pixmap = QPixmap(self.direction_key_signal[key])
                    pixmap_show = direction_pixmap.scaled(200, 200, Qt.KeepAspectRatio)
                    self.label_5.setPixmap(pixmap_show)

                    self.car_control_send_cmd()

                previous_control = current_control
            
            time.sleep(0.01)

        termios.tcsetattr(sys.stdin, termios.TCSADRAIN,filedescriptors)


    def delay(self, ms):
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec_()


    ################### Button Event APIs ###################
    def wifi_event(self):
        if self.is_button_executed_done:
            self.is_button_executed_done = False
            self.butto_queue_idx += 1
            self.butto_queue.put((self.butto_queue_idx, self.button_event['wifi_event']))
        else:
            print('The button feature is not executed completely')
        return


    def scan_event(self):
        if self.is_button_executed_done:
            self.butto_queue_idx += 1
            self.butto_queue.put((self.butto_queue_idx, self.button_event['scan_event']))
        else:
            print('The button feature is not executed completely')
        return 


    def video_streaming_event(self):
        if self.is_button_executed_done:
            self.butto_queue_idx += 1
            self.butto_queue.put((self.butto_queue_idx, self.button_event['video_streaming_event']))
        else:
            print('The button feature is not executed completely')
        return


    def mode_control_event(self):
        if self.is_button_executed_done:
            self.butto_queue_idx += 1
            self.butto_queue.put((self.butto_queue_idx, self.button_event['mode_control_event']))
        else:
            print('The button feature is not executed completely')
        return


    def enter_password_event(self):
        if self.is_button_executed_done:
            self.butto_queue_idx += 1
            self.butto_queue.put((self.butto_queue_idx, self.button_event['enter_password_event']))
        else:
            print('The button feature is not executed completely')
        return


    def onActivated(self, text):
        self.comboText = text  
        self.wifi_get_log['SSID'] = self.comboText

        # Open and write the SSID to JSON file
        self.f = open("ip.json", "r+")
        data = json.load(self.f)
        data['ssid'] = self.wifi_get_log['SSID']

        data_obj = json.dumps(data)
        self.f.close()

        # Clear the file content since we load it
        # using json.load before
        self.f = open("ip.json", "w").close()

        # Reopen and overwrite the file content
        self.f = open("ip.json", "r+")
        self.f.write(data_obj)
        self.f.close()

        print(f'Select SSID: {text}')  


    def car_control_send_cmd(self):
        if self.is_button_executed_done:
            self.butto_queue_idx += 1
            self.butto_queue.put((self.butto_queue_idx, self.button_event['car_control_event']))
        else:
            print('The button feature is not executed completely')
        return


    ################### Execution APIs ###################
    def wifi_event_exec(self):
        tx_packet = b'\xAB\xBA\x01'
        rx_packet = b''
        
        if (self.button_connect_status == 'disconnect') and (self.is_scanned_ssid) and (self.is_typed_pass):       
            tx_packet += RF_CMD_CONNECT      
            self.usb.usb_send_data(tx_packet)
            # Wait for response data in 2 second
            rx_packet = self.usb.usb_receive_data(2)

            if rx_packet[(RF_CMD_HEADER_SIZE + RF_CMD_CMD_SIZE + RF_CMD_PAYLOAD_LEN_SIZE): (RF_CMD_HEADER_SIZE + RF_CMD_CMD_SIZE + RF_CMD_PAYLOAD_LEN_SIZE + 1)] == b'\x01':
                print('Received ACK from Connect ')
                self.button_connect_status = 'connect'
                # Update the label of the Connect button
                self.pushButton_2.setText('CONNECTING')

                # Reset to force enter wifi password for the next time               
                self.is_typed_pass = False

                print("Connect to wifi network")

                # Get local IP for storage purpose
                rx_packet = b''
                tx_packet = b'\xAB\xBA\x01'
                tx_packet += RF_CMD_GET_IP  
                timeout = 15
                start_get_ip = False
                start_time = time.time()

                ###########################################################
                # Send RF command to the STM32 and wait for response here #
                ###########################################################
                while True:
                    duration = time.time() - start_time
                    
                    if duration > timeout:
                        # Exceed timeout
                        print('Fail to get the entire of Local IP')
                        data = b''
                        break

                    # Send data via Virtual com port
                    self.usb.usb_send_data(tx_packet)
                    # Wait for response data in 1 second
                    rx_packet = self.usb.usb_receive_data(10)
                    print(rx_packet)

                    if (rx_packet[(RF_CMD_HEADER_SIZE + RF_CMD_CMD_SIZE + RF_CMD_PAYLOAD_LEN_SIZE): (RF_CMD_HEADER_SIZE + RF_CMD_CMD_SIZE + RF_CMD_PAYLOAD_LEN_SIZE + 1)] == b'\x01') and (rx_packet[RF_CMD_HEADER_SIZE: RF_CMD_HEADER_SIZE + RF_CMD_PAYLOAD_LEN_SIZE] == b'\x02'):
                        # There is no ready SSID yet
                        print('Temporarily no Local IP')

                        # time.sleep(0.5)
                        self.delay(500)
                    elif (rx_packet[(RF_CMD_HEADER_SIZE + RF_CMD_CMD_SIZE + RF_CMD_PAYLOAD_LEN_SIZE): (RF_CMD_HEADER_SIZE + RF_CMD_CMD_SIZE + RF_CMD_PAYLOAD_LEN_SIZE + 1)] == b'\x01') and (rx_packet[RF_CMD_HEADER_SIZE: RF_CMD_HEADER_SIZE + RF_CMD_PAYLOAD_LEN_SIZE] != b'\x02'):
                        ip_bytes = rx_packet[(RF_CMD_HEADER_SIZE + RF_CMD_CMD_SIZE + RF_CMD_PAYLOAD_LEN_SIZE + 1):]
                        ip_str = ip_bytes.decode('ascii')
                        ip_str += ':81'
                        start_get_ip = True

                        print('Local IP: ', ip_str)

                        # Open and write the Local IP to JSON file
                        self.f = open("ip.json", "r+")
                        data = json.load(self.f)
                        data['ip'] = ip_str
                        data_obj = json.dumps(data)
                        self.f.close()
                        # Clear the file content since we load it
                        # using json.load before
                        self.f = open("ip.json", "w").close()
                        # Reopen and overwrite the file content
                        self.f = open("ip.json", "r+")
                        self.f.write(data_obj)
                        self.f.close()
                        break
                        
                    # time.sleep(0.02)
                    self.delay(20)

                self.pushButton_2.setText('DISCONNECT')

            else:
                print('Wrong status of Wifi connect')
                return False

        elif self.button_connect_status == 'connect':
            tx_packet += RF_CMD_DISCONNECT      
            self.usb.usb_send_data(tx_packet)
            # Wait for response data in 1 second
            rx_packet = self.usb.usb_receive_data(1)

            if rx_packet[(RF_CMD_HEADER_SIZE + RF_CMD_CMD_SIZE + RF_CMD_PAYLOAD_LEN_SIZE): (RF_CMD_HEADER_SIZE + RF_CMD_CMD_SIZE + RF_CMD_PAYLOAD_LEN_SIZE + 1)] == b'\x01':
                print('Received ACK from Disconnect ')
                self.button_connect_status = 'disconnect'
                # Update the label of the Connect button
                self.pushButton_2.setText('CONNECT')
                print("Disconnect from current wifi network")
            else:
                print('Wrong status of Wifi disconnect')
                return False

        return True


    def scan_event_exec(self):
        if self.button_connect_status == 'disconnect':

            print("Start WIFI scanning")

            # Append scanning data to a list, the addd to the combo box later
            self.pushButton.setText('SCANNING')

            self.is_scanned_ssid = True
            rx_packet = b''
            tx_packet = b'\xAB\xBA\x01'
            tx_packet += RF_CMD_GET_AVAILABLE_SSID  
            ssid_bytes = b''
            timeout = 15
            start_time = time.time()
            start_get_ssid  = False

            ###########################################################
            # Send RF command to the STM32 and wait for response here #
            ###########################################################
            while True:
                duration = time.time() - start_time
                
                if duration > timeout:
                    # Exceed timeout
                    print('Fail to get the entire SSID')
                    data = b''
                    break

                # Send data via Virtual com port
                self.usb.usb_send_data(tx_packet)
                # Wait for response data in 2 second
                rx_packet = self.usb.usb_receive_data(3)

                if (rx_packet[(RF_CMD_HEADER_SIZE + RF_CMD_CMD_SIZE + RF_CMD_PAYLOAD_LEN_SIZE): (RF_CMD_HEADER_SIZE + RF_CMD_CMD_SIZE + RF_CMD_PAYLOAD_LEN_SIZE + 1)] == b'\x01') and (rx_packet[RF_CMD_HEADER_SIZE: RF_CMD_HEADER_SIZE + RF_CMD_PAYLOAD_LEN_SIZE] == b'\x02'):
                    # There is no ready SSID yet
                    print('Temporarily no available SSID')

                    # time.sleep(0.5)
                    self.delay(500)
                    
                elif (rx_packet[(RF_CMD_HEADER_SIZE + RF_CMD_CMD_SIZE + RF_CMD_PAYLOAD_LEN_SIZE): (RF_CMD_HEADER_SIZE + RF_CMD_CMD_SIZE + RF_CMD_PAYLOAD_LEN_SIZE + 1)] == b'\x00') and (rx_packet[RF_CMD_HEADER_SIZE: RF_CMD_HEADER_SIZE + RF_CMD_PAYLOAD_LEN_SIZE] == b'\x02'):
                    print('Run out of available SSID')
                    if start_get_ssid:
                        # QMessageBox.about("Scan status", "Complete")
                        break
                else:
                    ssid_idx = rx_packet[(RF_CMD_HEADER_SIZE + RF_CMD_CMD_SIZE + RF_CMD_PAYLOAD_LEN_SIZE + 1):(RF_CMD_HEADER_SIZE + RF_CMD_CMD_SIZE + RF_CMD_PAYLOAD_LEN_SIZE + 1 + 1)]
                    ssid_bytes = rx_packet[(RF_CMD_HEADER_SIZE + RF_CMD_CMD_SIZE + RF_CMD_PAYLOAD_LEN_SIZE + 1 + 1):]
                    ssid_str = ssid_bytes.decode('ascii')
                    print('SSID length: ', rx_packet[(RF_CMD_HEADER_SIZE + RF_CMD_PAYLOAD_LEN_SIZE + RF_CMD_CMD_SIZE + 1 + 1):])
                    print('ssid_bytes', ssid_bytes)
                    print('ssid_str: ', ssid_str)
                    print('ssid_idx: ', ssid_idx)

                    # Check if this SSID is appended to the scan list before
                    if not (ssid_str in self.wifi_scan_ssid['SSID']):
                        self.wifi_scan_ssid['IDX'].append(ssid_idx)
                        self.wifi_scan_ssid['SSID'].append(ssid_str)
                        print(f'Received SSID: {ssid_str}')
                    
                    start_get_ssid = True
                    
                # time.sleep(0.02)
                self.delay(20)
                    
            # Need to pasr SSID from bytes/interger to strng
            self.pushButton.setText('SCAN WIFI')

            # Append and Display to Combo box here
            for ssid in self.wifi_scan_ssid['SSID']:
                self.comboBox.addItem(ssid)

            return True
        else:
            return False


    def video_streaming_event_exec(self):
        if self.video_streaming_status == 'stop':
            self.video_streaming_status = 'start'
            self.pushButton_3.setText('STOP')
            # Start video streaming here            
            print("Start the session")

            # Open the web browser here link to the video streaming page
            # TODO: define the best solution to start video streaming here

        else:
            self.video_streaming_status = 'stop'
            self.pushButton_3.setText('START')
            print("Stop the session")

            # Close the web browser here link to the video streaming page
            # TODO: define the best solution to stop video streaming here
        return True


    def mode_control_event_exec(self):
        if  self.mode_control_event_status == 'Emoji':
            # Use this flag to classify the output from model
            self.mode_control_event_status = 'Keyboard'
            self.pushButton_4.setText('KEYBOARD CTRL')
            print("Switch to Keyboard control")
        else:
            self.mode_control_event_status = 'Emoji'
            self.pushButton_4.setText('EMOJI CTRL')
            print("Switch to Emoji control")
        return True

    
    def enter_password_event_exec(self):
        tx_packet = b'\xAB\xBA'
        rx_packet = b''

        if self.button_connect_status == 'disconnect':
            self.is_typed_pass = True

            textboxValue = self.lineEdit.text()
            self.wifi_select_ssid['Password'] = textboxValue.encode('ascii')
            self.wifi_select_ssid['SSID'] = self.comboText

            # Open and write the SSID to JSON file
            # Open the file for the first time
            self.f = open("ip.json", "r+")
            data = json.load(self.f)
            data['password'] = textboxValue
            data_obj = json.dumps(data)
            self.f.close()
            # Clear the file content since we load it
            # using json.load before
            self.f = open("ip.json", "w").close()
            # Reopen and overwrite the file content
            self.f = open("ip.json", "r+")
            self.f.write(data_obj)
            self.f.close()

            print('Pass word: ', textboxValue)
            
            for idx in range(len(self.wifi_scan_ssid['SSID'])):
                if self.wifi_scan_ssid['SSID'][idx] == self.wifi_select_ssid['SSID']:
                    print('Mapping to the correct password and SSID: ', self.wifi_select_ssid['IDX'])
                    self.wifi_select_ssid['IDX'] = self.wifi_scan_ssid['IDX'][idx]
            
            # # Pop up a 
            # Qt.QMessageBox.question(self, 'Wifi selection', 
            #                         "SSID: {}, <br>Password: {} "\
            #                         .format(self.comboText, textboxValue) ,        
            #                         Qt.QMessageBox.Ok, Qt.QMessageBox.Ok)

            self.lineEdit.setText("")

            # Send Set SSID password to the MCU
            tx_packet += (len(self.wifi_select_ssid['Password']) + 1 + 1).to_bytes(1, byteorder='big') 
            tx_packet += RF_CMD_SET_SSID
            tx_packet += self.wifi_select_ssid['IDX']
            tx_packet += self.wifi_select_ssid['Password']

            # Send data via Virtual com port
            self.usb.usb_send_data(tx_packet)
            # Wait for response data in 1 second
            rx_packet = self.usb.usb_receive_data(1)
            if (rx_packet[(RF_CMD_HEADER_SIZE + RF_CMD_CMD_SIZE + RF_CMD_PAYLOAD_LEN_SIZE): (RF_CMD_HEADER_SIZE + RF_CMD_CMD_SIZE + RF_CMD_PAYLOAD_LEN_SIZE + 1)] == b'\x01') and (rx_packet[RF_CMD_HEADER_SIZE: RF_CMD_HEADER_SIZE + RF_CMD_PAYLOAD_LEN_SIZE] == b'\x02'):
                # Reset this parameters for the next SSID selection
                self.wifi_select_ssid = {
                    'IDX':b'',
                    'SSID':b'',
                    'Password':b''
                }
                return True                
        else:
            return False

        return True


    def car_control_event_exec(self):
        rx_packet = b''
        # Send data via Virtual com port
        self.usb.usb_send_data(self.car_control_packet)
        # Wait for response data in 1 second
        rx_packet = self.usb.usb_receive_data(1)
        if (rx_packet[(RF_CMD_HEADER_SIZE + RF_CMD_CMD_SIZE + RF_CMD_PAYLOAD_LEN_SIZE): (RF_CMD_HEADER_SIZE + RF_CMD_CMD_SIZE + RF_CMD_PAYLOAD_LEN_SIZE + 1)] == b'\x01') and (rx_packet[RF_CMD_HEADER_SIZE: RF_CMD_HEADER_SIZE + RF_CMD_PAYLOAD_LEN_SIZE] == b'\x02'):
            print('Send Car control packet successfully')


class usb_serial(object):
    
    def __init__ (self, port):
        self.comPort = port
        self.baudrate = 115200
        self.usb_mutex = Lock()
        self.usb_port = serial.Serial(self.comPort, self.baudrate, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE)

    def usb_send_data(self, data):
        # print(data)
        self.usb_mutex.acquire()
        self.usb_port.flushInput()
        self.usb_port.write(data)
        self.usb_mutex.release()


    def usb_receive_data(self, timeout):
        self.usb_mutex.acquire()
        start_time = time.time()     
        data = b''
        data_idx = 0
        enter_header = False
        payload_len = 0

        # Wait for received data
        while True:
        # |-- Header 1 --|-- Header 2 --|-- payload length --|--- CMD ---|---- data ----|
        # |--- 1 byte ---|--- 1 byte ---|------ 1 byte ------|-- 1 byte--|-- n bytes ---|
            duration = time.time() - start_time

            if duration > timeout:
                # Exceed timeout
                print('TIME OUT')
                data = b''
                # Release the mutex here
                self.usb_mutex.release()
                return data

            if self.usb_port.inWaiting():
                data_idx += 1
                data += self.usb_port.read()

                # print(data)

                if enter_header:
                    if data_idx == (RF_CMD_HEADER_SIZE + RF_CMD_PAYLOAD_LEN_SIZE):
                        # Parse one byte of payload length
                        payload_len = int.from_bytes(data[(RF_CMD_HEADER_SIZE) : 
                                            (RF_CMD_HEADER_SIZE + RF_CMD_PAYLOAD_LEN_SIZE)], "big")
                        print('USB received payload length: ', payload_len)
                    
                    # Reach the end of payload
                    if data_idx == (RF_CMD_HEADER_SIZE + RF_CMD_PAYLOAD_LEN_SIZE + payload_len):
                        # Release the mutex here
                        self.usb_mutex.release()
                        return data

			# Check if entered data frame
            if (not enter_header) and (data_idx == RF_CMD_HEADER_SIZE):
                if data == b'\xAB\xBA':
                    enter_header = 1
                else:
					# Minus the received index to 1 for the next header
                    data_idx -= 1
                    data = data[1:RF_CMD_HEADER_SIZE]

        

RF_CMD_CAR_CTRL_MOVE_FORWARD  = b'\x00'
RF_CMD_CAR_CTRL_MOVE_BACKWARD = b'\x01'
RF_CMD_CAR_CTRL_TURN_LEFT     = b'\x02'
RF_CMD_CAR_CTRL_TURN_RIGHT    = b'\x03'
RF_CMD_CAR_CTRL_BACK_LEFT     = b'\x04'
RF_CMD_CAR_CTRL_BACK_RIGHT    = b'\x05'
RF_CMD_CAR_CTRL_ROTATE_LEFT   = b'\x06'
RF_CMD_CAR_CTRL_ROTATE_RIGHT  = b'\x07'
RF_CMD_CAR_CTRL_STOP          = b'\x08'

RF_CMD_CONNECT                = b'\xA0'
RF_CMD_DISCONNECT             = b'\xA1'
RF_CMD_GET_AVAILABLE_SSID     = b'\xA2'
RF_CMD_SET_SSID               = b'\xA3'
RF_CMD_GET_IP                 = b'\xA4'
RF_CMD_GET_RSSI               = b'\xA5'

RF_CMD_RESPONSE_ACK           = b'\xB0'
RF_CMD_HEADER1                = b'\xAB'
RF_CMD_HEADER2                = b'\xBA'

RF_CMD_HEADER_SIZE            = 2
RF_CMD_CMD_SIZE               = 1
RF_CMD_PAYLOAD_LEN_SIZE       = 1

USB_COM_PORT                  = '/dev/tty.usbmodem5D81208233341'


if __name__ == '__main__':
    app = QApplication(sys.argv)
    QApplication.setStyle(QStyleFactory.create('Plastique'))
    ui = CustomMainWindow()
    sys.exit(app.exec_())
