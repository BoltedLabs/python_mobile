import time
from curses import ascii

from dataclasses import dataclass

from enum import Enum

import serial

from functools import wraps
import errno
import os
import signal

class TimeoutError(Exception):
    pass

def _handle_timeout(signum, frame):
    raise TimeoutError()

class GSMType(Enum):
    GSM: str = 'CMGF'
    GPS: str = 'CGNSPWR'

class SMSEnableError(Exception):
    pass

class SMSDisableError(Exception):
    pass

class SMSFailedToSend(Exception):
    pass

class GPSEnableError(Exception):
    pass

class GPSDisableError(Exception):
    pass

class SMSNotDeleted(Exception):
    pass

class SMSAlreadyDeleted(Exception):
    pass

@dataclass
class GPSLocation:
    status: bool
    fix: bool
    timestamp: str
    lat: str
    long: str
    altitude: str
    speed_over_ground: str
    course_over_ground: str
    fix_mode: str
    reserved: str
    hdop: str
    pdop: str
    vdop: str
    reserved2: str
    gnss_satellites_in_view: str
    gnss_satellites_used: str
    glonass_satellites_used: str
    reservered3: str
    cno_max: str
    hpa: str
    vpa: str

@dataclass
class SMSRaw:
    index: int
    status: str
    from_address: str

    serial: object 

    deleted: bool = False

    raw = []
    utf: str = None

    def get(self):
        if self.deleted:
            raise SMSAlreadyDeleted()

        self.serial.write_raw(f'AT+CMGR={self.index}')

        message = []

        while True:
            contents = self.serial._serial.readline()
            
            if b'OK' in contents:
                break

            message.append(contents.strip())

        self.raw = message
        
        lines = []
        for line in self.raw:
            if len(line) > 0:
                lines.append(line.decode('ascii', 'ignore') + '\n')

        message = ''.join(lines)

        self.utf = message

    def delete(self):
        if self.deleted:
            raise SMSAlreadyDeleted()

        response = self.serial.write(f'AT+CMGD={self.index}')

        if response == 'ERROR':
            raise SMSNotDeleted()
        self.deleted = True
        return True


class Commander:
    def __init__(self, serial_path: str):
        self._serial_path: str = serial_path
        self._serial: serial.Serial = serial.Serial(serial_path, 115200, timeout=3.0)

        self.enabled: [str] = []

    def _command_enable(self, module) -> str:
        return f'AT+{module}=1'

    def _command_disable(self, module) -> str:
        return f'AT+{module}=0'

    def _command_status(self, module) -> str:
        return f'AT+{module}?'

    def _handle_response(self, checks=['OK', 'ERROR'], timeout=5):
        response = None

        # NOTE: Rolling a custom timeout incase something went wrong with the hardware
        #       default timeout time is 5s
        signal.signal(signal.SIGALRM, _handle_timeout)
        signal.alarm(timeout)

        try:
            while True:
                contents = self._serial.readline().decode().strip()

                if any(x in contents for x in checks):
                    response = contents
                    break
        finally:
            signal.alarm(0)

        return response

    def write_raw(self, command):
        command += '\r\n'

        return self._serial.write(command.encode())

    def write(self, command, delay=None, timeout=5, checks=['OK', 'ERROR'], split_space=False):
        self.write_raw(command)

        response = None

        if delay:
            time.sleep(delay)

        response = self._handle_response(timeout=timeout, checks=checks)

        if split_space:
            response = response.split(' ')[1].strip()

        return response

    def write_order(self, commands, delay=0.5, timeout=5):
        responses = []

        for command in commands:
            self.write_raw(command)

            time.sleep(delay)

        response = self._handle_response(timeout=timeout)
        return response

    def gps_disable(self) -> bool:
        status = self.write(self._command_status(GSMType.GPS.value), checks=[
            f'+{GSMType.GPS.value}:'
        ], split_space=True)
        
        if status == '0':
            return True

        response = self.write(self._command_disable(GSMType.GPS.value))

        if response == 'ERROR':
            raise GPSDisableError()
        return True

    def gps_enable(self) -> bool:
        status = self.write(self._command_status(GSMType.GPS.value), checks=[
            f'+{GSMType.GPS.value}:'
        ], split_space=True)

        if status == '1':
            return True

        response = self.write(self._command_enable(GSMType.GPS.value))

        if response == 'ERROR':
            raise GPSEnableError()
        return True

    def gps_get(self, until_location=True):
        if until_location:
            while True:
                response = self._gps_get_location()

                if response.lat:
                    return response
        else:
            return self._gps_get_location()

    def _gps_get_location(self):
        response = self.write('AT+CGNSINF', checks=['+CGNSINF:'], split_space=True)
        split = response.split(',')
        return GPSLocation(*split)

    def sms_disable(self) -> bool:
        status = self.write(self._command_status(GSMType.GSM.value))

        if status == '0':
            return True
        
        response = self.write(self._command_disable(GSMType.GSM.value))

        if response == 'ERROR':
            raise SMSDisableError()
        return True
    
    def sms_enable(self) -> bool:
        status = self.write(self._command_status(GSMType.GSM.value))

        if status == '1':
            return True

        response = self.write(self._command_enable(GSMType.GSM.value))

        if response == 'ERROR':
            raise SMSDisableError()
        return True

    def sms_get_storage_modes(self):
        return self.write('AT+CPMS=?', checks=['+CPMS:'])

    def sms_set_storage_mode(self, mode: str) -> str:
        return self.write(f'AT+CPMS="{mode}"')

    def sms_send(self, to, message):
        response = self.write_order([f'AT+CMGS="{to}"', f'{message}', ascii.ctrl("z")])

        if response == 'ERROR':
            raise SMSFailedToSend()
        return True

    def sms_get(self, delay=0.5):
        response = self.write_raw('AT+CMGL="ALL"')

        time.sleep(delay)
        
        lines = []
        while True:
            contents = self._serial.readline()

            if b'+CMGL:' in contents:
                raw = contents.decode().split('+CMGL: ')[1].split(',')
            
                index = raw[0]
                status = raw[1][1:-1]
                from_address = raw[2]
                
                message = SMSRaw(index, status, from_address, serial=self)
                message.get()

                lines.append(message)
                continue

            if b'OK' in contents:
                break

        return lines
