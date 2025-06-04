import os
import psutil
import serial, serial.tools.list_ports
import time
import threading

from logic.config_watcher import *
from logic.logger import logger

class ArduinoMouse:
    def __init__(self):
        self.cfg = Config()
        self.mouse_buttons_pressed = set()
        self.serial_read_thread = None
        self.stop_event = threading.Event()
        
        self.serial_port = serial.Serial()
        self.serial_port.baudrate = self.cfg.arduino_baudrate
        self.serial_port.timeout = 0
        self.serial_port.write_timeout = 0
        
        if self.cfg.arduino_port == 'auto':
            self.serial_port.port = self.__detect_port()
        else:
            self.serial_port.port = self.cfg.arduino_port
        
        try:
            if self.serial_port.port:
                self.serial_port.open()
                logger.info(f'[Arduino] Serial port {self.serial_port.port} opened successfully.')
                self._start_listening()
            else:
                logger.error('[Arduino] No serial port detected or configured. Cannot connect.')
        except serial.SerialException as e:
            logger.error(f'[Arduino] Failed to connect to serial port {self.serial_port.port}: {e}')
            self.checks()
        except Exception as e:
            logger.error(f'[Arduino] An unexpected error occurred during Arduino initialization: {e}')
            self.checks()

        if not self.serial_port.is_open:
            logger.warning('[Arduino] Serial port is not open. Arduino functionality will be unavailable.')
                    
    def click(self):
        self._send_command('c')

    def press(self):
        self._send_command('p')

    def release(self):
        self._send_command('r')
        
    def move(self, x, y):
        if self.cfg.arduino_16_bit_mouse:
            data_str = f'm{x},{y}'
            data = f'{data_str}\n'.encode()
            logger.info(f"[Arduino] Sending move data: {data_str}")
            self.serial_port.write(data)
        else:
            x_parts = self._split_value(x)
            y_parts = self._split_value(y)
            for x_part, y_part in zip(x_parts, y_parts):
                data_str = f'm{x_part},{y_part}'
                data = f'{data_str}\n'.encode()
                logger.info(f"[Arduino] Sending move data: {data_str}")
                self.serial_port.write(data)
        
    def _split_value(self, value):
        if value == 0:
            return [0]
        
        values = []
        sign = -1 if value < 0 else 1
        abs_value = abs(value)
        while abs_value > 127:
            values.append(sign * 127)
            abs_value -= 127
        values.append(sign * abs_value)

        return values
    
    def _start_listening(self):
        if self.serial_port.is_open and (self.serial_read_thread is None or not self.serial_read_thread.is_alive()):
            self.stop_event.clear()
            self.serial_read_thread = threading.Thread(target=self._read_serial_data, daemon=True)
            self.serial_read_thread.name = "ArduinoSerialListener"
            self.serial_read_thread.start()
            logger.info("[Arduino] Started serial listener thread.")
        elif not self.serial_port.is_open:
            logger.warning("[Arduino] Cannot start serial listener, port is not open.")

    def _read_serial_data(self):
        logger.info("[Arduino] Serial listener thread running.")
        loop_count = 0
        while not self.stop_event.is_set():
            loop_count += 1
            if loop_count % 10000 == 0:
                 if self.serial_port.is_open:
                    logger.info(f"[Arduino] Listener loop active. Port: {self.serial_port.port}, In waiting: {self.serial_port.in_waiting}")
                 else:
                    logger.info("[Arduino] Listener loop active, but port is not open.")
            
            if self.serial_port.is_open and self.serial_port.in_waiting > 0:
                try:
                    raw_bytes = self.serial_port.readline()
                    decoded_line = raw_bytes.decode('utf-8', errors='ignore')
                    stripped_line = decoded_line.strip()
                    
                    if stripped_line: # Only log "after strip" if it's not empty
                        if stripped_line.startswith("BD:"):
                            try:
                                button_id = int(stripped_line.split(":")[1])
                                self.mouse_buttons_pressed.add(button_id)
                                logger.info(f"[Arduino] Button Down detected (from Arduino mouse): {button_id}") 
                            except (IndexError, ValueError) as e:
                                logger.error(f"[Arduino] Error parsing BD line '{stripped_line}': {e}")
                        elif stripped_line.startswith("BU:"):
                            try:
                                button_id = int(stripped_line.split(":")[1])
                                self.mouse_buttons_pressed.discard(button_id)
                                logger.info(f"[Arduino] Button Up detected (from Arduino mouse): {button_id}") 
                            except (IndexError, ValueError) as e:
                                logger.error(f"[Arduino] Error parsing BU line '{stripped_line}': {e}")
                except serial.SerialException as e:
                    logger.error(f"[Arduino] Serial error during read: {e}")
                    self.close()
                    break 
                except Exception as e:
                    logger.error(f"[Arduino] Error reading/parsing serial data: {e}")
            else:
                time.sleep(0.001)
        logger.info("[Arduino] Serial listener thread stopped.")

    def is_button_pressed(self, button_id):
        return button_id in self.mouse_buttons_pressed

    def close(self):
        self.stop_event.set()
        if self.serial_read_thread and self.serial_read_thread.is_alive():
            self.serial_read_thread.join(timeout=1)
            if self.serial_read_thread.is_alive():
                logger.warning("[Arduino] Serial listener thread did not terminate in time.")
        if self.serial_port.is_open:
            self.serial_port.close()
            logger.info("[Arduino] Serial port closed.")

    def __del__(self):
        self.close()

    def __detect_port(self):
        ports = serial.tools.list_ports.comports()
        
        for port in ports:
            if "Arduino" in port.description:
                return port.device
        return None

    def _send_command(self, command):
        logger.info(f"[Arduino] Sending command: {command}")
        self.serial_port.write(f'{command}\n'.encode())
    
    def find_library_directory(self, base_path, library_name_start):
        for root, dirs, files in os.walk(base_path):
            for dir_name in dirs:
                if dir_name.startswith(library_name_start):
                    return os.path.join(root, dir_name)
        return None

    def checks(self):
        for process in psutil.process_iter(['pid', 'name']):
            if process.info['name'] == 'Arduino IDE.exe':
                logger.error('[Arduino] Arduino IDE is open, close IDE and restart app.')
                break
        
        try:
            documents_path = os.path.join(os.environ['USERPROFILE'], 'Documents')
            arduino_libraries_path = os.path.join(documents_path, 'Arduino', 'libraries')
            
            USB_Host_Shield_library_path = self.find_library_directory(arduino_libraries_path, 'USB_Host_Shield')
            if USB_Host_Shield_library_path is None:
                logger.error("[Arduino] Usb host shield library not found")
                return
            
            hid_settings = os.path.join(USB_Host_Shield_library_path, 'settings.h')
            
            if os.path.exists(hid_settings):
                with open(hid_settings, 'r') as file:
                    for line in file:
                        if line.startswith('#define ENABLE_UHS_DEBUGGING'):
                            parts = line.split()
                            if len(parts) == 3 and parts[1] == 'ENABLE_UHS_DEBUGGING':
                                value = parts[2]
                                if value == '1':
                                    logger.error(f'[Arduino] Disable `ENABLE_UHS_DEBUGGING` setting in {hid_settings} file.')
                                    break
        except Exception as e:
            logger.error(f'[Arduino] USB_Host_Shield lib not found.\n{e}')
            
arduino = ArduinoMouse()